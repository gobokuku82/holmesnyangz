"""
Search Team Supervisor - 검색 관련 Agent들을 관리하는 서브그래프
법률, 부동산, 대출 검색을 병렬/순차적으로 수행
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service.core.separated_states import SearchTeamState, SearchKeywords, SharedState
from app.service.core.agent_registry import AgentRegistry
from app.service.core.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class SearchTeamSupervisor:
    """
    검색 팀 Supervisor
    법률, 부동산, 대출 검색 Agent들을 관리하고 조정
    """

    def __init__(self, llm_context=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
        """
        self.llm_context = llm_context
        self.team_name = "search"

        # Agent 초기화 (Registry에서 가져오기)
        self.available_agents = self._initialize_agents()

        # 법률 검색 도구 초기화
        self.legal_search_tool = None
        try:
            from app.service.tools.legal_search_tool import LegalSearchTool
            self.legal_search_tool = LegalSearchTool()
            logger.info("LegalSearchTool initialized successfully")
        except Exception as e:
            logger.warning(f"LegalSearchTool initialization failed: {e}")

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _initialize_agents(self) -> Dict[str, bool]:
        """사용 가능한 Agent 확인"""
        agent_types = ["search_agent"]  # 현재는 통합 SearchAgent 사용
        available = {}

        for agent_name in agent_types:
            available[agent_name] = agent_name in AgentRegistry.list_agents(enabled_only=True)

        logger.info(f"SearchTeam available agents: {available}")
        return available

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(SearchTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_search_node)
        workflow.add_node("route", self.route_search_node)
        workflow.add_node("search", self.execute_search_node)
        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START,"prepare")
        workflow.add_edge("prepare", "route")

        # 라우팅 후 검색 또는 종료
        workflow.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "search": "search",
                "skip": "finalize"
            }
        )

        workflow.add_edge("search", "aggregate")
        workflow.add_edge("aggregate", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("SearchTeam subgraph built successfully")

    def _route_decision(self, state: SearchTeamState) -> str:
        """검색 실행 여부 결정"""
        if not state.get("search_scope"):
            return "skip"
        return "search"

    async def prepare_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 준비 노드
        키워드 추출 및 검색 범위 설정
        """
        logger.info("[SearchTeam] Preparing search")

        # 초기화
        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()
        state["search_progress"] = {}

        # 키워드가 없으면 쿼리에서 추출
        if not state.get("keywords"):
            query = state.get("shared_context", {}).get("query", "")
            state["keywords"] = self._extract_keywords(query)

        # 검색 범위가 없으면 키워드 기반으로 결정
        if not state.get("search_scope"):
            state["search_scope"] = self._determine_search_scope(state["keywords"])

        logger.info(f"[SearchTeam] Search scope: {state['search_scope']}")
        return state

    def _extract_keywords(self, query: str) -> SearchKeywords:
        """쿼리에서 키워드 추출 - LLM 사용 시 더 정확함"""
        # LLM이 있으면 LLM 기반 추출, 없으면 패턴 매칭
        if self.llm_context and self.llm_context.api_key:
            try:
                return self._extract_keywords_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM keyword extraction failed, using fallback: {e}")

        # Fallback: 패턴 매칭 기반 키워드 추출
        return self._extract_keywords_with_patterns(query)

    def _extract_keywords_with_llm(self, query: str) -> SearchKeywords:
        """LLM을 사용한 키워드 추출"""
        from openai import OpenAI

        system_prompt = """당신은 부동산 검색 쿼리에서 키워드를 추출하는 전문가입니다.
사용자 질문을 분석하여 검색에 필요한 핵심 키워드를 카테고리별로 추출하세요.

## 카테고리별 키워드 설명:

1. **legal (법률 관련)**
   - 법률 용어, 권리, 의무, 계약 조항 관련
   - 예: 법, 전세, 임대, 보증금, 계약, 권리, 의무, 갱신, 임차인, 임대인, 법률, 조항, 규정
   - 예시: "전세금 5% 인상" → ["전세금", "인상", "임대차", "갱신"]

2. **real_estate (부동산 시세)**
   - 부동산 종류, 지역, 가격, 시세 관련
   - 예: 아파트, 빌라, 오피스텔, 시세, 매매, 가격, 평수, 지역명, 동네명
   - 예시: "강남구 아파트 시세" → ["강남구", "아파트", "시세", "전세가"]

3. **loan (대출 관련)**
   - 대출 상품, 금리, 조건 관련
   - 예: 대출, 금리, 한도, LTV, DTI, DSR, 담보, 신용, 상환, 금융
   - 예시: "주택담보대출 금리" → ["주택담보대출", "금리", "한도"]

4. **general (일반 정보)**
   - 숫자, 단위, 날짜 등 보조 정보
   - 예: 5억, 10%, 2024년, 3개월, 평당
   - 예시: "5억 전세" → ["5억", "전세"]

## 응답 형식 (JSON 형식으로 응답):
{
    "legal": ["법률", "관련", "키워드"],
    "real_estate": ["부동산", "관련", "키워드"],
    "loan": ["대출", "관련", "키워드"],
    "general": ["숫자", "단위", "날짜"]
}

## 추출 가이드:
- 검색에 실제로 도움이 되는 키워드만 추출
- 불용어(은, 는, 이, 가 등)는 제외
- 동의어나 유사어는 대표 키워드 하나만 포함
- 빈 배열로 반환 가능 (해당 카테고리에 키워드가 없으면)
- 동일한 키워드가 여러 카테고리에 속할 수 있음 (예: "전세"는 legal과 real_estate 모두)"""

        try:
            client = OpenAI(api_key=self.llm_context.api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"키워드 추출할 질문: {query}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"LLM Keyword Extraction: {result}")

            return SearchKeywords(
                legal=result.get("legal", []),
                real_estate=result.get("real_estate", []),
                loan=result.get("loan", []),
                general=result.get("general", [])
            )
        except Exception as e:
            logger.error(f"LLM keyword extraction failed: {e}")
            raise

    def _extract_keywords_with_patterns(self, query: str) -> SearchKeywords:
        """패턴 매칭 기반 키워드 추출 (Fallback)"""
        legal_keywords = []
        real_estate_keywords = []
        loan_keywords = []
        general_keywords = []

        # 법률 관련 키워드
        legal_terms = ["법", "전세", "임대", "계약", "보증금", "권리", "의무", "갱신", "임차인", "임대인"]
        for term in legal_terms:
            if term in query:
                legal_keywords.append(term)

        # 부동산 관련 키워드
        estate_terms = ["아파트", "빌라", "오피스텔", "시세", "매매", "가격", "평수", "지역", "강남", "강북", "서초", "송파"]
        for term in estate_terms:
            if term in query:
                real_estate_keywords.append(term)

        # 대출 관련 키워드
        loan_terms = ["대출", "금리", "한도", "LTV", "DTI", "DSR", "담보", "신용"]
        for term in loan_terms:
            if term in query:
                loan_keywords.append(term)

        # 일반 키워드 (숫자, 퍼센트 등)
        import re
        numbers = re.findall(r'\d+[%억만원평]?', query)
        general_keywords.extend(numbers)

        return SearchKeywords(
            legal=legal_keywords,
            real_estate=real_estate_keywords,
            loan=loan_keywords,
            general=general_keywords
        )

    def _determine_search_scope(self, keywords: SearchKeywords) -> List[str]:
        """키워드 기반 검색 범위 결정"""
        scope = []

        if keywords.get("legal"):
            scope.append("legal")
        if keywords.get("real_estate"):
            scope.append("real_estate")
        if keywords.get("loan"):
            scope.append("loan")

        # 아무것도 없으면 법률 검색을 기본으로
        if not scope:
            scope = ["legal"]

        return scope

    async def route_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 라우팅 노드
        병렬/순차 실행 결정
        """
        logger.info("[SearchTeam] Routing search")

        # 검색할 Agent 확인
        search_scope = state.get("search_scope", [])

        if len(search_scope) > 1:
            state["execution_strategy"] = "parallel"
        else:
            state["execution_strategy"] = "sequential"

        return state

    async def execute_search_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        검색 실행 노드
        실제 검색 Agent 호출 + 하이브리드 법률 검색
        """
        logger.info("[SearchTeam] Executing searches")

        search_scope = state.get("search_scope", [])
        keywords = state.get("keywords", {})
        shared_context = state.get("shared_context", {})
        query = shared_context.get("query", "")

        # === 1. 법률 검색 (우선 실행) ===
        if "legal" in search_scope and self.legal_search_tool:
            try:
                logger.info("[SearchTeam] Executing legal search")

                # 검색 파라미터 구성
                search_params = {
                    "limit": 10
                }

                # 임차인 보호 조항 필터
                if any(term in query for term in ["임차인", "전세", "임대", "보증금"]):
                    search_params["is_tenant_protection"] = True

                # 법률 검색 실행
                result = await self.legal_search_tool.search(query, search_params)

                # 결과 파싱
                if result.get("status") == "success":
                    legal_data = result.get("data", [])

                    # 결과 포맷 변환
                    state["legal_results"] = [
                        {
                            "law_title": item.get("law_title", ""),
                            "article_number": item.get("article_number", ""),
                            "article_title": item.get("article_title", ""),
                            "content": item.get("content", ""),
                            "relevance_score": 1.0 - item.get("distance", 0.0),
                            "chapter": item.get("chapter"),
                            "section": item.get("section"),
                            "source": "legal_db"
                        }
                        for item in legal_data
                    ]

                    state["search_progress"]["legal_search"] = "completed"
                    logger.info(f"[SearchTeam] Legal search completed: {len(legal_data)} results")
                else:
                    state["search_progress"]["legal_search"] = "failed"
                    logger.warning(f"Legal search returned status: {result.get('status')}")

            except Exception as e:
                logger.error(f"Legal search failed: {e}")
                state["search_progress"]["legal_search"] = "failed"
                # 실패해도 계속 진행

        # === 2. SearchAgent 실행 (부동산, 대출 검색) ===
        # 법률 검색이 이미 완료되었으므로 scope에서 제외
        remaining_scope = [s for s in search_scope if s != "legal"]

        if remaining_scope and self.available_agents.get("search_agent"):
            try:
                # SearchAgent 입력 준비
                search_input = {
                    "query": query,
                    "original_query": shared_context.get("original_query", query),
                    "chat_session_id": shared_context.get("session_id", ""),
                    "collection_keywords": self._flatten_keywords(keywords),
                    "search_scope": remaining_scope,
                    "shared_context": {},
                    "todos": [],
                    "todo_counter": 0
                }

                result = await AgentAdapter.execute_agent_dynamic(
                    "search_agent",
                    search_input,
                    self.llm_context
                )

                # 결과 파싱
                if result.get("status") in ["completed", "success"]:
                    collected_data = result.get("collected_data", {})

                    # 부동산 검색 결과
                    if "real_estate_search" in collected_data:
                        state["real_estate_results"] = collected_data["real_estate_search"]
                        state["search_progress"]["real_estate_search"] = "completed"

                    # 대출 검색 결과
                    if "loan_search" in collected_data:
                        state["loan_results"] = collected_data["loan_search"]
                        state["search_progress"]["loan_search"] = "completed"

                    state["search_progress"]["search_agent"] = "completed"
                else:
                    state["search_progress"]["search_agent"] = "failed"
                    state["error"] = result.get("error", "Search failed")

            except Exception as e:
                logger.error(f"Search execution failed: {e}")
                state["search_progress"]["search_agent"] = "failed"
                state["error"] = str(e)

        return state

    def _flatten_keywords(self, keywords: SearchKeywords) -> List[str]:
        """키워드 평탄화"""
        all_keywords = []
        if isinstance(keywords, dict):
            all_keywords.extend(keywords.get("legal", []))
            all_keywords.extend(keywords.get("real_estate", []))
            all_keywords.extend(keywords.get("loan", []))
            all_keywords.extend(keywords.get("general", []))
        return list(set(all_keywords))

    async def aggregate_results_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        결과 집계 노드
        여러 검색 결과를 통합
        """
        logger.info("[SearchTeam] Aggregating results")

        # 결과 집계
        total_results = 0
        sources = []

        if state.get("legal_results"):
            total_results += len(state["legal_results"])
            sources.append("legal_db")

        if state.get("real_estate_results"):
            total_results += len(state["real_estate_results"])
            sources.append("real_estate_api")

        if state.get("loan_results"):
            total_results += len(state["loan_results"])
            sources.append("loan_service")

        state["total_results"] = total_results
        state["sources_used"] = sources

        # 통합 결과 생성
        state["aggregated_results"] = {
            "total_count": total_results,
            "by_type": {
                "legal": len(state.get("legal_results", [])),
                "real_estate": len(state.get("real_estate_results", [])),
                "loan": len(state.get("loan_results", []))
            },
            "sources": sources,
            "keywords_used": state.get("keywords", {})
        }

        logger.info(f"[SearchTeam] Aggregated {total_results} results from {len(sources)} sources")
        return state

    async def finalize_node(self, state: SearchTeamState) -> SearchTeamState:
        """
        최종화 노드
        상태 정리 및 완료 처리
        """
        logger.info("[SearchTeam] Finalizing")

        state["end_time"] = datetime.now()

        if state.get("start_time"):
            elapsed = (state["end_time"] - state["start_time"]).total_seconds()
            state["search_time"] = elapsed

        # 상태 결정
        if state.get("error"):
            state["status"] = "failed"
        elif state.get("total_results", 0) > 0:
            state["status"] = "completed"
        else:
            state["status"] = "completed"  # 결과가 없어도 완료로 처리

        logger.info(f"[SearchTeam] Completed with status: {state['status']}")
        return state

    async def execute(
        self,
        shared_state: SharedState,
        search_scope: Optional[List[str]] = None,
        keywords: Optional[Dict] = None
    ) -> SearchTeamState:
        """
        SearchTeam 실행

        Args:
            shared_state: 공유 상태
            search_scope: 검색 범위
            keywords: 검색 키워드

        Returns:
            검색 팀 상태
        """
        # 초기 상태 생성
        initial_state = SearchTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            keywords=keywords or SearchKeywords(legal=[], real_estate=[], loan=[], general=[]),
            search_scope=search_scope or [],
            filters={},
            legal_results=[],
            real_estate_results=[],
            loan_results=[],
            aggregated_results={},
            total_results=0,
            search_time=0.0,
            sources_used=[],
            search_progress={},
            start_time=None,
            end_time=None,
            error=None,
            current_search=None
        )

        # 서브그래프 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"SearchTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state


# 테스트 코드
if __name__ == "__main__":
    async def test_search_team():
        from app.service.core.separated_states import StateManager

        # SearchTeam 초기화
        search_team = SearchTeamSupervisor()

        # 테스트 쿼리
        queries = [
            "전세금 5% 인상 가능한가요?",
            "강남구 아파트 시세",
            "주택담보대출 한도"
        ]

        for query in queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print("-"*60)

            # 공유 상태 생성
            shared_state = StateManager.create_shared_state(
                query=query,
                session_id="test_search_team"
            )

            # SearchTeam 실행
            result = await search_team.execute(shared_state)

            print(f"Status: {result['status']}")
            print(f"Total results: {result.get('total_results', 0)}")
            print(f"Sources used: {result.get('sources_used', [])}")
            print(f"Search time: {result.get('search_time', 0):.2f}s")

            if result.get("aggregated_results"):
                print(f"Results by type: {result['aggregated_results']['by_type']}")

    import asyncio
    asyncio.run(test_search_team())