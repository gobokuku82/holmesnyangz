"""
Contract Review Agent

계약서 및 문서 검토를 담당하는 에이전트
- 위험 요소 분석
- 법적 준수사항 확인
- 개선 권고사항 제시
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional, Annotated
from datetime import datetime
import json

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition

from core.states import ReviewAgentState
from tools.contract_review_tool import ContractReviewTool


class ReviewAgent:
    """계약서 검토 에이전트"""

    def __init__(self):
        """Initialize ReviewAgent"""
        self.logger = logging.getLogger("ReviewAgent")
        self.llm_client = None  # Will be initialized when needed
        self.review_tool = ContractReviewTool()

        # LangGraph 0.6+ 설정
        self.memory = MemorySaver()
        self.graph = None
        self.app = None

        # 에이전트 설정
        self._setup_graph()

    def _setup_graph(self):
        """LangGraph 워크플로우 설정"""
        # 상태 그래프 생성
        workflow = StateGraph(ReviewAgentState)

        # 노드 추가
        workflow.add_node("extract_document", self.extract_document_node)
        workflow.add_node("analyze_document", self.analyze_document_node)
        workflow.add_node("perform_review", self.perform_review_node)
        workflow.add_node("generate_recommendations", self.generate_recommendations_node)
        workflow.add_node("create_report", self.create_report_node)

        # 엣지 설정
        workflow.set_entry_point("extract_document")
        workflow.add_edge("extract_document", "analyze_document")
        workflow.add_conditional_edges(
            "analyze_document",
            self.check_document_validity,
            {
                "valid": "perform_review",
                "invalid": END
            }
        )
        workflow.add_edge("perform_review", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "create_report")
        workflow.add_edge("create_report", END)

        # 컴파일
        self.graph = workflow
        self.app = workflow.compile(checkpointer=self.memory)

        self.logger.info("ReviewAgent graph compiled successfully")

    async def extract_document_node(self, state: ReviewAgentState) -> ReviewAgentState:
        """문서 추출 노드"""
        try:
            query = state["original_query"]
            self.logger.info(f"Extracting document from query: {query}")

            # 문서 내용 추출 (현재는 state에서 직접 가져옴)
            document_content = state.get("document_content", "")

            # 문서가 없는 경우 쿼리에서 추출 시도
            if not document_content:
                # LLM을 사용한 문서 내용 추출 (실제로는 파일 업로드 등 필요)
                prompt = f"""
사용자의 요청에서 검토할 문서 내용을 추출하세요.

요청: {query}

문서 내용이 명시적으로 포함되어 있으면 추출하고,
없으면 문서를 요청하는 메시지를 생성하세요.
"""
                response = await self.llm_client.analyze_request(prompt)

                if "문서" not in response and "계약서" not in response:
                    return {
                        **state,
                        "status": "no_document",
                        "error_message": "검토할 문서를 제공해주세요"
                    }

                document_content = response

            return {
                **state,
                "document_content": document_content,
                "status": "document_extracted"
            }

        except Exception as e:
            self.logger.error(f"Error extracting document: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    async def analyze_document_node(self, state: ReviewAgentState) -> ReviewAgentState:
        """문서 분석 노드"""
        try:
            document_content = state.get("document_content", "")
            self.logger.info("Analyzing document type and structure")

            # 문서 유형 감지
            document_type = await self._detect_document_type(document_content)

            # 문서 구조 분석
            document_structure = await self._analyze_structure(document_content)

            # LLM을 사용한 초기 분석
            prompt = f"""
다음 문서를 분석하세요:

문서 내용:
{document_content[:2000]}  # 처음 2000자만

분석 항목:
1. 문서 유형
2. 주요 당사자
3. 핵심 조건
4. 특이사항

JSON 형식으로 응답하세요:
{{
    "document_type": "문서 유형",
    "parties": ["당사자1", "당사자2"],
    "key_terms": ["조건1", "조건2"],
    "special_notes": ["특이사항"]
}}
"""
            analysis = await self.llm_client.analyze_request(prompt)

            # 응답 파싱
            if isinstance(analysis, str):
                try:
                    analysis_data = json.loads(analysis)
                except json.JSONDecodeError:
                    analysis_data = {
                        "document_type": document_type,
                        "parties": [],
                        "key_terms": [],
                        "special_notes": []
                    }
            else:
                analysis_data = analysis

            return {
                **state,
                "document_type": document_type,
                "document_metadata": analysis_data,
                "document_structure": document_structure,
                "status": "analyzed"
            }

        except Exception as e:
            self.logger.error(f"Error analyzing document: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    def check_document_validity(self, state: ReviewAgentState) -> str:
        """문서 유효성 확인"""
        status = state.get("status", "")
        document_content = state.get("document_content", "")

        if status == "analyzed" and document_content:
            return "valid"
        else:
            return "invalid"

    async def perform_review_node(self, state: ReviewAgentState) -> ReviewAgentState:
        """문서 검토 실행 노드"""
        try:
            document_content = state["document_content"]
            document_type = state.get("document_type", "일반문서")

            self.logger.info(f"Performing review for {document_type}")

            # Contract Review Tool 호출
            result = await self.review_tool.search(
                query=state["original_query"],
                params={
                    "document_content": document_content,
                    "document_type": document_type,
                    "review_focus": ["risk", "compliance", "completeness"]
                }
            )

            if result["status"] == "success" and result["data"]:
                review_data = result["data"][0]

                # 위험 레벨 매핑
                risk_level = review_data.get("overall_risk_level", "low")

                return {
                    **state,
                    "review_results": review_data,
                    "risk_factors": review_data.get("risk_factors", []),
                    "compliance_check": review_data.get("compliance_check", {}),
                    "risk_level": risk_level,
                    "status": "reviewed"
                }
            else:
                return {
                    **state,
                    "status": "review_failed",
                    "error_message": "문서 검토 실패"
                }

        except Exception as e:
            self.logger.error(f"Review error: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    async def generate_recommendations_node(self, state: ReviewAgentState) -> ReviewAgentState:
        """권고사항 생성 노드"""
        try:
            review_results = state.get("review_results", {})
            risk_factors = state.get("risk_factors", [])
            risk_level = state.get("risk_level", "low")

            self.logger.info("Generating recommendations")

            # 기본 권고사항 (Tool에서 제공)
            recommendations = review_results.get("recommendations", [])

            # LLM을 사용한 추가 권고사항 생성
            if risk_factors:
                prompt = f"""
다음 위험 요소들에 대한 구체적인 개선 방안을 제시하세요:

위험 요소:
{json.dumps(risk_factors, ensure_ascii=False, indent=2)}

전체 위험도: {risk_level}

각 위험 요소에 대해 실행 가능한 구체적인 개선 방안을 제시하세요.
"""
                additional_recommendations = await self.llm_client.generate_response(prompt)

                if additional_recommendations:
                    recommendations.append(f"추가 권고: {additional_recommendations}")

            # 위험도별 일반 권고사항
            if risk_level in ["high", "critical"]:
                recommendations.append("⚠️ 법률 전문가의 검토를 강력히 권고합니다")
            elif risk_level == "medium":
                recommendations.append("📋 주요 조항에 대한 재검토를 권고합니다")

            return {
                **state,
                "recommendations": recommendations,
                "status": "recommendations_generated"
            }

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    async def create_report_node(self, state: ReviewAgentState) -> ReviewAgentState:
        """검토 보고서 생성 노드"""
        try:
            self.logger.info("Creating review report")

            review_results = state.get("review_results", {})
            recommendations = state.get("recommendations", [])
            risk_level = state.get("risk_level", "low")
            document_type = state.get("document_type", "일반문서")

            # 보고서 생성
            report = f"""
==================================================
📋 계약서 검토 보고서
==================================================

문서 유형: {document_type}
검토 일시: {datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")}

--------------------------------------------------
1. 종합 평가
--------------------------------------------------
• 전체 위험도: {self._translate_risk_level(risk_level)}
• 위험 요소: {len(state.get('risk_factors', []))}개 발견
• 문서 완성도: {review_results.get('completeness_check', {}).get('completeness_score', 0):.0%}

--------------------------------------------------
2. 주요 발견사항
--------------------------------------------------
"""
            # 위험 요소 추가
            for i, risk in enumerate(state.get('risk_factors', [])[:5], 1):
                report += f"• [{risk['risk_level']}] {risk['description']}\n"

            report += """
--------------------------------------------------
3. 개선 권고사항
--------------------------------------------------
"""
            for recommendation in recommendations[:10]:
                report += f"• {recommendation}\n"

            report += """
--------------------------------------------------
4. 다음 단계
--------------------------------------------------
"""
            if risk_level in ["high", "critical"]:
                report += "• 즉시 법률 전문가 상담 필요\n"
                report += "• 위험 조항 수정 후 재검토 필요\n"
            elif risk_level == "medium":
                report += "• 표시된 위험 요소 검토 및 수정\n"
                report += "• 필요시 상대방과 조건 재협상\n"
            else:
                report += "• 최종 검토 후 서명 진행 가능\n"
                report += "• 계약서 사본 보관 확인\n"

            report += "\n=================================================="

            return {
                **state,
                "review_report": report,
                "status": "completed"
            }

        except Exception as e:
            self.logger.error(f"Error creating report: {e}")
            return {
                **state,
                "status": "error",
                "error_message": str(e)
            }

    def _translate_risk_level(self, risk_level: str) -> str:
        """위험 레벨 한글 변환"""
        translations = {
            "low": "낮음 ✅",
            "medium": "보통 ⚠️",
            "high": "높음 ⚠️⚠️",
            "critical": "매우 높음 🚨"
        }
        return translations.get(risk_level, risk_level)

    async def _detect_document_type(self, content: str) -> str:
        """문서 유형 감지"""
        content_lower = content.lower()

        if "임대차" in content_lower or "임차인" in content_lower:
            return "임대차계약서"
        elif "매매" in content_lower or "매수인" in content_lower:
            return "매매계약서"
        elif "전세" in content_lower:
            return "전세계약서"
        elif "근저당" in content_lower:
            return "근저당권설정계약서"
        elif "내용증명" in content_lower:
            return "내용증명"
        else:
            return "일반문서"

    async def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """문서 구조 분석"""
        lines = content.split('\n')

        structure = {
            "total_lines": len(lines),
            "sections": [],
            "has_signatures": False,
            "has_special_terms": False
        }

        # 섹션 찾기
        for line in lines:
            if line.strip().startswith("제") and "조" in line:
                structure["sections"].append(line.strip())
            if "서명" in line or "(인)" in line:
                structure["has_signatures"] = True
            if "특약" in line:
                structure["has_special_terms"] = True

        structure["section_count"] = len(structure["sections"])

        return structure

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        에이전트 실행

        Args:
            input_data: {
                "original_query": str,
                "document_content": str,
                "document_type": Optional[str],
                "chat_session_id": str,
                "shared_context": Dict
            }

        Returns:
            실행 결과
        """
        try:
            self.logger.info(f"ReviewAgent executing")

            # 초기 상태 설정
            initial_state = ReviewAgentState(
                chat_session_id=input_data.get("chat_session_id", ""),
                original_query=input_data.get("original_query", ""),
                document_content=input_data.get("document_content", ""),
                document_type=input_data.get("document_type", ""),
                status="initialized",
                shared_context=input_data.get("shared_context", {}),
                todos=input_data.get("todos", []),
                todo_counter=input_data.get("todo_counter", 0),
                parent_todo_id=input_data.get("parent_todo_id"),
                review_results={},
                risk_factors=[],
                compliance_check={},
                risk_level="low",
                recommendations=[],
                document_metadata={},
                document_structure={},
                review_report="",
                error_message=""
            )

            # LangGraph 실행
            config = {"configurable": {"thread_id": input_data.get("chat_session_id", "default")}}
            result = await self.app.ainvoke(initial_state, config)

            # 결과 반환
            return {
                "status": result.get("status", "unknown"),
                "review_report": result.get("review_report", ""),
                "review_results": result.get("review_results", {}),
                "risk_level": result.get("risk_level", "unknown"),
                "risk_factors": result.get("risk_factors", []),
                "recommendations": result.get("recommendations", []),
                "error_message": result.get("error_message", ""),
                "todos": result.get("todos", [])
            }

        except Exception as e:
            self.logger.error(f"ReviewAgent execution error: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "todos": []
            }


# 테스트 코드
if __name__ == "__main__":
    import asyncio

    async def test():
        agent = ReviewAgent()

        # 테스트 1: 임대차계약서 검토
        print("\n=== Test 1: 임대차계약서 검토 ===")
        sample_contract = """
부동산 임대차 계약서

임대인 김철수와 임차인 이영희는 다음과 같이 계약한다.

제1조 (목적물)
서울시 강남구 테헤란로 123, 면적 85㎡

제2조 (임대차 기간)
2024년 1월 1일부터 2025년 12월 31일까지

제3조 (보증금과 월세)
보증금: 5천만원, 월세: 100만원

제4조 (특약사항)
- 중도 해지 불가
- 원상복구 비용 전액 임차인 부담
- 임차인의 모든 권리 포기

임대인: 김철수 (인)
임차인: 이영희 (인)
"""
        result = await agent.execute({
            "original_query": "이 임대차계약서 검토해줘",
            "document_content": sample_contract,
            "chat_session_id": "test_session_1"
        })
        print(f"Status: {result['status']}")
        print(f"Risk Level: {result.get('risk_level')}")
        if result.get('review_report'):
            print("=== Report Preview ===")
            print(result['review_report'][:500] + "...")

        # 테스트 2: 문서 없이 요청
        print("\n=== Test 2: 문서 없이 요청 ===")
        result = await agent.execute({
            "original_query": "계약서 검토해줘",
            "chat_session_id": "test_session_2"
        })
        print(f"Status: {result['status']}")
        if result.get('error_message'):
            print(f"Error: {result['error_message']}")

    asyncio.run(test())