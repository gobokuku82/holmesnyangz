"""
Price Search Agent
부동산 시세 검색 및 분석 전문 에이전트
"""

from typing import Dict, Any, List, Optional
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState
from backend.tools.price_tools import PRICE_TOOLS
from backend.config import settings

logger = logging.getLogger(__name__)


class PriceSearchAgent(BaseAgent):
    """
    시세 검색 전문 에이전트
    - 실거래가 조회
    - 시세 동향 분석
    - 지역별 가격 비교
    - 평당가 계산
    """
    
    def __init__(self):
        super().__init__(agent_id="price_search_agent", name="시세 검색 전문가")
        
        # LLM 초기화
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model=settings.default_model,
                temperature=0.5,
                api_key=settings.openai_api_key
            )
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.5,
                api_key=settings.anthropic_api_key
            )
        else:
            logger.warning("No LLM API key found")
            self.llm = None
        
        # 에이전트 초기화
        self.agent_executor = self._create_agent_executor() if self.llm else None
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        도구를 사용하는 에이전트 실행기 생성
        """
        # 프롬프트 템플릿
        system_prompt = """당신은 부동산 시세 검색 전문가입니다.
        
주요 역할:
1. 실거래가 정보 검색 및 제공
2. 시세 동향 분석
3. 지역별 가격 비교
4. 평당가/㎡당가 계산
5. 시장 통계 정보 제공

사용 가능한 도구:
- search_real_estate_price: 실거래가 검색
- analyze_price_trend: 가격 동향 분석
- compare_prices: 지역별 가격 비교
- calculate_price_per_area: 평당가 계산
- get_market_statistics: 시장 통계 조회

응답 시 주의사항:
- 정확한 수치와 단위 표기
- 가격은 "X억 X천만원" 형식으로 표현
- 비교 분석 시 구체적인 수치 제공
- 시장 인사이트 포함"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 도구 사용 에이전트 생성
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=PRICE_TOOLS,
            prompt=prompt
        )
        
        # 에이전트 실행기 생성
        return AgentExecutor(
            agent=agent,
            tools=PRICE_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        시세 관련 질의 처리
        
        Args:
            state: Current state
            
        Returns:
            Updated state with price information
        """
        query = state.get("query", "")
        entities = state.get("entities", {})
        parameters = state.get("agent_parameters", {}).get("search_params", {})
        
        logger.info(f"Processing price search query: {query}")
        
        # 검색 파라미터 추출
        location = self._extract_location(entities, parameters)
        property_type = entities.get("property_type", "아파트")
        transaction_type = entities.get("transaction_type", "매매")
        
        # 도구를 직접 사용하거나 LLM 에이전트 사용
        if self.agent_executor and query:
            result = self._process_with_llm(query, location, property_type, transaction_type)
        else:
            result = self._process_with_tools(location, property_type, transaction_type, entities)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(result)
        
        return {
            "price_search_result": result,
            "confidence": confidence,
            "current_step": "price_search_complete"
        }
    
    def _process_with_llm(self, 
                         query: str,
                         location: str,
                         property_type: str,
                         transaction_type: str) -> Dict[str, Any]:
        """
        LLM 에이전트를 사용한 처리
        """
        try:
            # 컨텍스트 포함 쿼리 생성
            enhanced_query = f"""
사용자 질의: {query}

추출된 정보:
- 지역: {location if location else '미지정'}
- 부동산 타입: {property_type}
- 거래 유형: {transaction_type}

위 정보를 바탕으로 사용자 질의에 답변해주세요.
"""
            
            # 에이전트 실행
            response = self.agent_executor.invoke({
                "input": enhanced_query
            })
            
            # 결과 파싱
            if isinstance(response, dict):
                output = response.get("output", "")
                intermediate_steps = response.get("intermediate_steps", [])
                
                # 도구 사용 결과 수집
                tool_results = []
                for step in intermediate_steps:
                    if len(step) >= 2:
                        action = step[0]
                        observation = step[1]
                        tool_results.append({
                            "tool": action.tool if hasattr(action, 'tool') else "unknown",
                            "input": action.tool_input if hasattr(action, 'tool_input') else {},
                            "output": observation
                        })
                
                return {
                    "status": "success",
                    "response": output,
                    "tool_results": tool_results,
                    "search_context": {
                        "location": location,
                        "property_type": property_type,
                        "transaction_type": transaction_type
                    }
                }
            else:
                return {
                    "status": "success",
                    "response": str(response),
                    "search_context": {
                        "location": location,
                        "property_type": property_type,
                        "transaction_type": transaction_type
                    }
                }
                
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            # 폴백: 도구 직접 사용
            return self._process_with_tools(location, property_type, transaction_type, {})
    
    def _process_with_tools(self,
                           location: str,
                           property_type: str,
                           transaction_type: str,
                           entities: Dict) -> Dict[str, Any]:
        """
        도구를 직접 사용한 처리
        """
        from backend.tools.price_tools import (
            search_real_estate_price,
            analyze_price_trend,
            get_market_statistics
        )
        
        results = {}
        
        try:
            # 1. 실거래가 검색
            if location:
                price_search = search_real_estate_price.invoke({
                    "location": location,
                    "property_type": property_type,
                    "transaction_type": transaction_type
                })
                results["price_search"] = price_search
                
                # 2. 가격 동향 분석
                trend_analysis = analyze_price_trend.invoke({
                    "location": location,
                    "property_type": property_type,
                    "period_months": 6
                })
                results["trend_analysis"] = trend_analysis
                
                # 3. 시장 통계
                market_stats = get_market_statistics.invoke({
                    "location": location
                })
                results["market_statistics"] = market_stats
            
            # 응답 생성
            response = self._generate_response(results, location, property_type, transaction_type)
            
            return {
                "status": "success",
                "response": response,
                "detailed_results": results,
                "search_context": {
                    "location": location,
                    "property_type": property_type,
                    "transaction_type": transaction_type
                }
            }
            
        except Exception as e:
            logger.error(f"Tool processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": "시세 정보를 검색하는 중 오류가 발생했습니다."
            }
    
    def _extract_location(self, entities: Dict, parameters: Dict) -> Optional[str]:
        """
        위치 정보 추출
        """
        # 엔티티에서 위치 추출
        if entities.get("location"):
            locations = entities["location"]
            if isinstance(locations, list) and locations:
                return locations[0]
            elif isinstance(locations, str):
                return locations
        
        # 파라미터에서 위치 추출
        if parameters.get("location"):
            locations = parameters["location"]
            if isinstance(locations, list) and locations:
                return locations[0]
            elif isinstance(locations, str):
                return locations
        
        return None
    
    def _generate_response(self,
                          results: Dict,
                          location: str,
                          property_type: str,
                          transaction_type: str) -> str:
        """
        검색 결과를 바탕으로 응답 생성
        """
        response_parts = []
        
        # 헤더
        if location:
            response_parts.append(f"### {location} {property_type} {transaction_type} 시세 정보\n")
        
        # 실거래가 정보
        if "price_search" in results:
            search_data = results["price_search"]
            if search_data.get("status") == "success":
                response_parts.append(f"**검색 결과: {search_data.get('total_results', 0)}건**\n")
                
                # 상위 3개 매물 표시
                for idx, item in enumerate(search_data.get("results", [])[:3], 1):
                    response_parts.append(
                        f"{idx}. {item['name']}\n"
                        f"   - 가격: {item['price']}\n"
                        f"   - 면적: {item['area_pyeong']}평 ({item['area_sqm']:.1f}㎡)\n"
                        f"   - 층수: {item['floor']}\n"
                        f"   - 건축년도: {item['year_built']}년\n"
                    )
        
        # 가격 동향
        if "trend_analysis" in results:
            trend_data = results["trend_analysis"]
            if trend_data.get("status") == "success":
                summary = trend_data.get("trend_summary", {})
                response_parts.append(
                    f"\n**가격 동향 분석**\n"
                    f"- 추세: {summary.get('direction', 'N/A')}\n"
                    f"- 변동률: {summary.get('change_percent', 0):.1f}%\n"
                    f"- 현재 평균가: {summary.get('current_avg_price', 0) // 100000000}억원\n"
                )
        
        # 시장 통계
        if "market_statistics" in results:
            stats = results["market_statistics"]
            if stats.get("status") == "success":
                statistics = stats.get("statistics", {})
                response_parts.append(
                    f"\n**시장 현황**\n"
                    f"- 평균 거래 기간: {statistics.get('avg_days_on_market', 'N/A')}일\n"
                    f"- 재고 수준: {statistics.get('inventory_level', 'N/A')}\n"
                    f"- 인기 평형: {statistics.get('popular_size', 'N/A')}\n"
                    f"- 시장 심리: {statistics.get('market_sentiment', 'N/A')}\n"
                )
                
                # 인사이트 추가
                insights = stats.get("insights", [])
                if insights:
                    response_parts.append("\n**시장 인사이트**\n")
                    for insight in insights[:2]:
                        response_parts.append(f"- {insight}\n")
        
        # 응답이 비어있는 경우
        if not response_parts:
            return "시세 정보를 찾을 수 없습니다. 지역명이나 검색 조건을 확인해주세요."
        
        return "\n".join(response_parts)
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        결과의 신뢰도 계산
        """
        if result.get("status") != "success":
            return 0.0
        
        confidence = 0.5  # 기본 신뢰도
        
        # 검색 결과가 있으면 신뢰도 증가
        if result.get("detailed_results"):
            if result["detailed_results"].get("price_search"):
                confidence += 0.2
            if result["detailed_results"].get("trend_analysis"):
                confidence += 0.15
            if result["detailed_results"].get("market_statistics"):
                confidence += 0.15
        
        # LLM 응답이 있으면 신뢰도 증가
        if result.get("tool_results"):
            confidence = min(confidence + 0.1 * len(result["tool_results"]), 0.95)
        
        return min(confidence, 1.0)