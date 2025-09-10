"""
Finance Agent
자본 관리 및 금융 상담 전문 에이전트
"""

from typing import Dict, Any, Optional
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState
from backend.tools.finance_tools import FINANCE_TOOLS
from backend.config import settings

logger = logging.getLogger(__name__)


class FinanceAgent(BaseAgent):
    """
    자본 관리 전문 에이전트
    - 대출 한도 계산
    - 월 상환액 시뮬레이션
    - 예산별 매물 추천
    - 금리 비교
    - 세금 계산
    - 투자 수익률 분석
    """
    
    def __init__(self):
        super().__init__(agent_id="finance_agent", name="자본 관리 전문가")
        
        # LLM 초기화
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model=settings.default_model,
                temperature=0.3,  # 금융 계산은 정확성이 중요
                api_key=settings.openai_api_key
            )
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.3,
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
        system_prompt = """당신은 부동산 금융 전문가입니다.
        
주요 역할:
1. 대출 한도 계산 (DTI, LTV, DSR 기준)
2. 월 상환액 시뮬레이션
3. 예산에 맞는 매물 추천
4. 은행별 금리 비교
5. 세금 계산 (취득세, 재산세 등)
6. 투자 수익률 분석

사용 가능한 도구:
- calculate_loan_limit: 대출 한도 계산
- simulate_monthly_payment: 월 상환액 시뮬레이션
- find_properties_by_budget: 예산별 매물 추천
- compare_interest_rates: 금리 비교
- calculate_taxes: 세금 계산
- calculate_investment_return: 투자 수익률 계산

응답 시 주의사항:
- 정확한 숫자와 계산 제공
- 금액은 "X억 X천만원" 형식으로 표현
- DTI, LTV, DSR 등 금융 규제 설명
- 리스크 요소 명시
- 실질적인 조언 제공"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 도구 사용 에이전트 생성
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=FINANCE_TOOLS,
            prompt=prompt
        )
        
        # 에이전트 실행기 생성
        return AgentExecutor(
            agent=agent,
            tools=FINANCE_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        금융 관련 질의 처리
        
        Args:
            state: Current state
            
        Returns:
            Updated state with finance information
        """
        query = state.get("query", "")
        entities = state.get("entities", {})
        parameters = state.get("agent_parameters", {}).get("finance_params", {})
        
        logger.info(f"Processing finance query: {query}")
        
        # 금융 정보 추출
        financial_info = self._extract_financial_info(query, entities, parameters)
        
        # 도구를 직접 사용하거나 LLM 에이전트 사용
        if self.agent_executor and query:
            result = self._process_with_llm(query, financial_info)
        else:
            result = self._process_with_tools(financial_info)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(result)
        
        return {
            "finance_result": result,
            "confidence": confidence,
            "current_step": "finance_analysis_complete"
        }
    
    def _extract_financial_info(self, query: str, entities: Dict, parameters: Dict) -> Dict[str, Any]:
        """
        질의에서 금융 정보 추출
        """
        import re
        
        financial_info = {
            "monthly_income": None,
            "loan_amount": None,
            "property_price": None,
            "down_payment": None,
            "interest_rate": 4.0,  # 기본값
            "loan_years": 30  # 기본값
        }
        
        # 월 소득 추출
        income_patterns = [
            r'월\s*(?:소득|수입|급여)?\s*(\d+)\s*만\s*원?',
            r'(\d+)\s*만\s*원?\s*월\s*(?:소득|수입|급여)',
            r'월급\s*(\d+)\s*만'
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, query)
            if match:
                financial_info["monthly_income"] = int(match.group(1)) * 10000
                break
        
        # 대출 금액 추출
        loan_patterns = [
            r'대출\s*(\d+)\s*억',
            r'(\d+)\s*억\s*대출',
            r'대출\s*(\d+)\s*천만'
        ]
        
        for pattern in loan_patterns:
            match = re.search(pattern, query)
            if match:
                if '억' in pattern:
                    financial_info["loan_amount"] = int(match.group(1)) * 100000000
                else:
                    financial_info["loan_amount"] = int(match.group(1)) * 10000000
                break
        
        # 부동산 가격 추출
        if entities.get("price"):
            price_info = entities["price"][0] if isinstance(entities["price"], list) else entities["price"]
            if isinstance(price_info, dict):
                value = int(price_info.get("value", 0))
                unit = price_info.get("unit", "")
                if unit == "billion":
                    financial_info["property_price"] = value * 100000000
                elif unit == "ten_million":
                    financial_info["property_price"] = value * 10000000
        
        # 파라미터에서 추가 정보
        if parameters:
            financial_info.update({
                k: v for k, v in parameters.items() 
                if v is not None
            })
        
        return financial_info
    
    def _process_with_llm(self, query: str, financial_info: Dict) -> Dict[str, Any]:
        """
        LLM 에이전트를 사용한 처리
        """
        try:
            # 컨텍스트 포함 쿼리 생성
            context_parts = []
            if financial_info["monthly_income"]:
                context_parts.append(f"월 소득: {financial_info['monthly_income'] // 10000}만원")
            if financial_info["property_price"]:
                context_parts.append(f"부동산 가격: {financial_info['property_price'] // 100000000}억원")
            if financial_info["loan_amount"]:
                context_parts.append(f"대출 금액: {financial_info['loan_amount'] // 100000000}억원")
            
            enhanced_query = f"""
사용자 질의: {query}

금융 정보:
{chr(10).join(context_parts) if context_parts else '제공된 금융 정보 없음'}

위 정보를 바탕으로 상세한 금융 분석과 조언을 제공해주세요.
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
                    "financial_context": financial_info
                }
            else:
                return {
                    "status": "success",
                    "response": str(response),
                    "financial_context": financial_info
                }
                
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            # 폴백: 도구 직접 사용
            return self._process_with_tools(financial_info)
    
    def _process_with_tools(self, financial_info: Dict) -> Dict[str, Any]:
        """
        도구를 직접 사용한 처리
        """
        from backend.tools.finance_tools import (
            calculate_loan_limit,
            simulate_monthly_payment,
            calculate_taxes
        )
        
        results = {}
        response_parts = []
        
        try:
            # 1. 대출 한도 계산
            if financial_info.get("monthly_income"):
                loan_limit = calculate_loan_limit.invoke({
                    "monthly_income": financial_info["monthly_income"],
                    "existing_loans": 0,
                    "property_price": financial_info.get("property_price")
                })
                results["loan_limit"] = loan_limit
                
                if loan_limit.get("status") == "success":
                    limit = loan_limit["loan_limits"]["final_limit"]
                    response_parts.append(
                        f"### 대출 한도 분석\n"
                        f"- 최대 대출 가능액: {loan_limit['formatted']['final_limit']}\n"
                        f"- 월 상환 가능액: {loan_limit['formatted']['monthly_payment']}\n"
                        f"- DTI: {loan_limit['ratios']['dti']}%\n"
                    )
            
            # 2. 월 상환액 시뮬레이션
            if financial_info.get("loan_amount"):
                payment_sim = simulate_monthly_payment.invoke({
                    "loan_amount": financial_info["loan_amount"],
                    "interest_rate": financial_info.get("interest_rate", 4.0),
                    "loan_years": financial_info.get("loan_years", 30)
                })
                results["payment_simulation"] = payment_sim
                
                if payment_sim.get("status") == "success":
                    response_parts.append(
                        f"\n### 월 상환액 시뮬레이션\n"
                        f"- 대출금액: {financial_info['loan_amount'] // 100000000}억원\n"
                        f"- 월 상환액: {payment_sim['formatted']['monthly']}\n"
                        f"- 총 이자: {payment_sim['formatted']['total_interest']}\n"
                        f"- 총 상환액: {payment_sim['formatted']['total_payment']}\n"
                    )
            
            # 3. 세금 계산
            if financial_info.get("property_price"):
                taxes = calculate_taxes.invoke({
                    "property_price": financial_info["property_price"],
                    "transaction_type": "매매",
                    "is_first_home": True
                })
                results["taxes"] = taxes
                
                if taxes.get("status") == "success":
                    response_parts.append(
                        f"\n### 세금 정보\n"
                        f"- 취득세: {taxes['formatted']['acquisition_total']}\n"
                        f"- 재산세: {taxes['formatted']['property_annual']}\n"
                    )
                    
                    # 팁 추가
                    for tip in taxes.get("tips", [])[:2]:
                        response_parts.append(f"- 💡 {tip}")
            
            # 응답이 비어있는 경우
            if not response_parts:
                response_parts.append(
                    "금융 분석을 위한 정보가 부족합니다.\n"
                    "월 소득, 대출 금액, 부동산 가격 등을 알려주시면 상세한 분석을 제공할 수 있습니다."
                )
            
            return {
                "status": "success",
                "response": "\n".join(response_parts),
                "detailed_results": results,
                "financial_context": financial_info
            }
            
        except Exception as e:
            logger.error(f"Tool processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": "금융 정보를 분석하는 중 오류가 발생했습니다."
            }
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        결과의 신뢰도 계산
        """
        if result.get("status") != "success":
            return 0.0
        
        confidence = 0.5  # 기본 신뢰도
        
        # 상세 결과가 있으면 신뢰도 증가
        if result.get("detailed_results"):
            confidence += 0.1 * len(result["detailed_results"])
        
        # 도구 사용 결과가 있으면 신뢰도 증가
        if result.get("tool_results"):
            confidence += 0.1 * min(len(result["tool_results"]), 3)
        
        # 금융 컨텍스트가 완전하면 신뢰도 증가
        context = result.get("financial_context", {})
        if context.get("monthly_income") and context.get("property_price"):
            confidence += 0.2
        
        return min(confidence, 0.95)