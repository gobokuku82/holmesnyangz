"""
Legal Agent
법률 및 규정 자문 전문 에이전트
"""

from typing import Dict, Any, Optional, List
import logging
import re
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState
from backend.tools.legal_tools import LEGAL_TOOLS
from backend.config import settings

logger = logging.getLogger(__name__)


class LegalAgent(BaseAgent):
    """
    법률 자문 전문 에이전트
    - 계약서 조항 설명
    - 세금 계산 (취득세, 양도세)
    - 법적 요건 확인
    - 법률 가이드라인 제공
    - 계약 위험 분석
    """
    
    def __init__(self):
        super().__init__(agent_id="legal_agent", name="법률 자문 전문가")
        
        # LLM 초기화
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model=settings.default_model,
                temperature=0.2,  # 법률 정보는 정확성이 중요
                api_key=settings.openai_api_key
            )
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.2,
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
        system_prompt = """당신은 부동산 법률 전문가입니다.
        
주요 역할:
1. 부동산 계약서 조항 설명 및 검토
2. 취득세, 양도세 등 세금 계산
3. 법적 요건 및 절차 안내
4. 임대차보호법 등 관련 법률 설명
5. 계약 위험 분석 및 조언

사용 가능한 도구:
- explain_contract_terms: 계약서 조항 설명
- calculate_acquisition_tax: 취득세 계산
- check_legal_requirements: 법적 요건 확인
- provide_legal_guidelines: 법률 가이드라인
- analyze_contract_risks: 계약 위험 분석

응답 시 주의사항:
- 정확한 법률 정보 제공
- 세금은 정확한 계산식과 함께 설명
- 관련 법조문 인용 (가능한 경우)
- 위험 요소 명확히 지적
- 실무적 조언 포함
- 전문가 상담 필요성 안내

중요: 법률 조언은 참고용이며, 실제 거래 시 전문가 상담을 권장한다고 명시하세요."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 도구 사용 에이전트 생성
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=LEGAL_TOOLS,
            prompt=prompt
        )
        
        # 에이전트 실행기 생성
        return AgentExecutor(
            agent=agent,
            tools=LEGAL_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        법률 관련 질의 처리
        
        Args:
            state: Current state
            
        Returns:
            Updated state with legal information
        """
        query = state.get("query", "")
        entities = state.get("entities", {})
        parameters = state.get("agent_parameters", {}).get("legal_params", {})
        
        logger.info(f"Processing legal query: {query}")
        
        # 법률 정보 추출
        legal_context = self._extract_legal_context(query, entities, parameters)
        
        # 도구를 직접 사용하거나 LLM 에이전트 사용
        if self.agent_executor and query:
            result = self._process_with_llm(query, legal_context)
        else:
            result = self._process_with_tools(legal_context)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(result)
        
        return {
            "legal_result": result,
            "confidence": confidence,
            "current_step": "legal_analysis_complete"
        }
    
    def _extract_legal_context(self, query: str, entities: Dict, parameters: Dict) -> Dict[str, Any]:
        """
        법률 관련 컨텍스트 추출
        """
        context = {
            "transaction_type": None,
            "property_price": None,
            "is_first_home": True,
            "topic": None,
            "contract_type": None
        }
        
        query_lower = query.lower()
        
        # 거래 유형 추출
        if "매매" in query or "구매" in query or "구입" in query:
            context["transaction_type"] = "매매"
            context["contract_type"] = "매매"
        elif "전세" in query:
            context["transaction_type"] = "전세"
            context["contract_type"] = "전세"
        elif "월세" in query or "임대" in query:
            context["transaction_type"] = "월세"
            context["contract_type"] = "월세"
        
        # 가격 정보 추출
        if entities.get("price"):
            price_info = entities["price"][0] if isinstance(entities["price"], list) else entities["price"]
            if isinstance(price_info, dict):
                value = int(price_info.get("value", 0))
                unit = price_info.get("unit", "")
                if unit == "billion":
                    context["property_price"] = value * 100000000
                elif unit == "ten_million":
                    context["property_price"] = value * 10000000
        
        # 주제 추출
        topics = {
            "계약": ["계약", "계약서", "특약"],
            "세금": ["세금", "취득세", "양도세", "재산세"],
            "임대차": ["임대차", "전세", "월세", "보증금"],
            "재개발": ["재개발", "재건축", "정비사업"],
            "상속": ["상속", "증여", "상속세"]
        }
        
        for topic_name, keywords in topics.items():
            if any(keyword in query_lower for keyword in keywords):
                context["topic"] = topic_name
                break
        
        # 첫 주택 여부
        if "첫" in query or "생애" in query or "처음" in query:
            context["is_first_home"] = True
        elif "두번째" in query or "추가" in query or "다주택" in query:
            context["is_first_home"] = False
        
        # 파라미터에서 추가 정보
        if parameters:
            context.update({
                k: v for k, v in parameters.items() 
                if v is not None
            })
        
        return context
    
    def _process_with_llm(self, query: str, legal_context: Dict) -> Dict[str, Any]:
        """
        LLM 에이전트를 사용한 처리
        """
        try:
            # 컨텍스트 포함 쿼리 생성
            context_parts = []
            if legal_context["transaction_type"]:
                context_parts.append(f"거래 유형: {legal_context['transaction_type']}")
            if legal_context["property_price"]:
                context_parts.append(f"부동산 가격: {legal_context['property_price'] // 100000000}억원")
            if legal_context["topic"]:
                context_parts.append(f"주요 주제: {legal_context['topic']}")
            
            enhanced_query = f"""
사용자 질의: {query}

법률 컨텍스트:
{chr(10).join(context_parts) if context_parts else '특정 컨텍스트 없음'}

위 정보를 바탕으로 정확한 법률 정보와 실무적 조언을 제공해주세요.
법률 조언은 참고용이며, 실제 거래 시 전문가 상담이 필요함을 안내해주세요.
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
                    "legal_context": legal_context,
                    "disclaimer": "본 정보는 일반적인 법률 정보 제공을 목적으로 하며, 개별 사안에 대한 법률 자문이 아닙니다. 실제 거래 시 반드시 전문가와 상담하시기 바랍니다."
                }
            else:
                return {
                    "status": "success",
                    "response": str(response),
                    "legal_context": legal_context,
                    "disclaimer": "본 정보는 참고용입니다. 실제 거래 시 전문가 상담을 받으세요."
                }
                
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            # 폴백: 도구 직접 사용
            return self._process_with_tools(legal_context)
    
    def _process_with_tools(self, legal_context: Dict) -> Dict[str, Any]:
        """
        도구를 직접 사용한 처리
        """
        from backend.tools.legal_tools import (
            explain_contract_terms,
            calculate_acquisition_tax,
            check_legal_requirements,
            provide_legal_guidelines
        )
        
        results = {}
        response_parts = []
        
        try:
            # 1. 계약서 조항 설명 (계약 관련 질의)
            if legal_context.get("contract_type"):
                contract_info = explain_contract_terms.invoke({
                    "contract_type": legal_context["contract_type"],
                    "is_first_time": legal_context.get("is_first_home", True)
                })
                results["contract_terms"] = contract_info
                
                if contract_info.get("status") == "success":
                    response_parts.append(f"### {legal_context['contract_type']} 계약 주요 조항\n")
                    
                    # 중요 조항
                    important = contract_info.get("important_clauses", [])
                    if important:
                        response_parts.append("**꼭 확인해야 할 사항:**\n")
                        for clause in important[:4]:
                            response_parts.append(f"• {clause}\n")
                    
                    # 주의사항
                    red_flags = contract_info.get("red_flags", [])
                    if red_flags:
                        response_parts.append("\n**계약 시 주의사항:**\n")
                        for flag in red_flags[:3]:
                            response_parts.append(f"⚠️ {flag}\n")
            
            # 2. 취득세 계산 (매매 + 가격 정보)
            if legal_context.get("property_price") and legal_context.get("transaction_type") == "매매":
                tax_info = calculate_acquisition_tax.invoke({
                    "property_price": legal_context["property_price"],
                    "is_first_home": legal_context.get("is_first_home", True),
                    "area_sqm": 85.0  # 기본값
                })
                results["acquisition_tax"] = tax_info
                
                if tax_info.get("status") == "success":
                    response_parts.append("\n### 취득세 계산\n")
                    calc = tax_info.get("tax_calculation", {})
                    response_parts.append(
                        f"- 세율: {calc.get('base_rate', 0)}%\n"
                        f"- 취득세: {calc.get('acquisition_tax', 0) // 10000}만원\n"
                        f"- 지방교육세: {calc.get('education_tax', 0) // 10000}만원\n"
                        f"- **총 납부세액: {tax_info['formatted']['final_tax']}**\n"
                    )
                    
                    # 감면 정보
                    reduction = tax_info.get("reduction_info", {})
                    if reduction.get("reasons"):
                        response_parts.append(f"- 감면 사유: {', '.join(reduction['reasons'])}\n")
            
            # 3. 법적 요건 확인
            if legal_context.get("transaction_type"):
                requirements = check_legal_requirements.invoke({
                    "transaction_type": legal_context["transaction_type"],
                    "property_type": "아파트"
                })
                results["legal_requirements"] = requirements
                
                if requirements.get("status") == "success":
                    response_parts.append("\n### 필요 서류 및 절차\n")
                    
                    # 필수 서류
                    docs = requirements.get("required_documents", {})
                    if docs.get("verification"):
                        response_parts.append("**확인 필수 서류:**\n")
                        for doc in docs["verification"][:5]:
                            response_parts.append(f"□ {doc}\n")
                    
                    # 법적 요건
                    special = requirements.get("legal_requirements", {}).get("special", [])
                    if special:
                        response_parts.append("\n**법적 의무사항:**\n")
                        for req in special[:3]:
                            response_parts.append(f"• {req}\n")
            
            # 4. 법률 가이드라인 (주제별)
            if legal_context.get("topic"):
                guidelines = provide_legal_guidelines.invoke({
                    "topic": legal_context["topic"],
                    "user_type": "buyer"
                })
                results["guidelines"] = guidelines
                
                if guidelines.get("status") == "success" and guidelines.get("guidelines"):
                    response_parts.append(f"\n### {legal_context['topic']} 관련 법률 정보\n")
                    
                    # 첫 번째 가이드라인 요약
                    for guide_name, guide_content in list(guidelines["guidelines"].items())[:1]:
                        if isinstance(guide_content, dict) and "주요내용" in guide_content:
                            for item in guide_content["주요내용"][:3]:
                                response_parts.append(f"• {item}\n")
            
            # 면책 조항 추가
            response_parts.append(
                "\n---\n"
                "📌 **법적 고지**: 본 정보는 일반적인 법률 정보 제공을 목적으로 하며, "
                "개별 사안에 대한 법률 자문이 아닙니다. 실제 거래 시에는 반드시 "
                "법무사, 변호사 등 전문가와 상담하시기 바랍니다.\n"
            )
            
            # 응답이 비어있는 경우
            if not response_parts or len(response_parts) == 1:
                response_parts = [
                    "부동산 거래와 관련된 법률 정보를 제공해드립니다.\n",
                    "구체적인 질문을 해주시면 더 정확한 답변을 드릴 수 있습니다.\n",
                    "예시: 취득세 계산, 계약서 검토, 임대차보호법 등\n"
                ]
            
            return {
                "status": "success",
                "response": "\n".join(response_parts),
                "detailed_results": results,
                "legal_context": legal_context,
                "disclaimer": "본 정보는 참고용입니다. 실제 거래 시 전문가 상담을 받으세요."
            }
            
        except Exception as e:
            logger.error(f"Tool processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": "법률 정보를 처리하는 중 오류가 발생했습니다."
            }
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        결과의 신뢰도 계산
        """
        if result.get("status") != "success":
            return 0.0
        
        confidence = 0.6  # 법률 정보는 기본 신뢰도를 높게 설정
        
        # 상세 결과가 있으면 신뢰도 증가
        if result.get("detailed_results"):
            results = result["detailed_results"]
            if results.get("contract_terms"):
                confidence += 0.1
            if results.get("acquisition_tax"):
                confidence += 0.1
            if results.get("legal_requirements"):
                confidence += 0.1
            if results.get("guidelines"):
                confidence += 0.05
        
        # 도구 사용 결과가 있으면 신뢰도 증가
        if result.get("tool_results"):
            confidence += 0.05 * min(len(result["tool_results"]), 2)
        
        # 법률 컨텍스트가 명확하면 신뢰도 증가
        context = result.get("legal_context", {})
        if context.get("transaction_type") and context.get("property_price"):
            confidence += 0.05
        
        return min(confidence, 0.95)