"""
Analyzer Agent
사용자 질의를 분석하여 의도, 엔티티, 복잡도를 파악하는 에이전트
LangGraph의 첫 번째 노드로 작동
"""

import re
from typing import Dict, Any, List, Optional, Tuple
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState
from backend.config import get_config_manager, settings

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    """
    질의 분석 에이전트
    - 사용자 의도 파악
    - 엔티티 추출
    - 질의 복잡도 평가
    - 적합한 에이전트 추천
    """
    
    def __init__(self):
        super().__init__(agent_id="analyzer_agent", name="질의 분석 전문가")
        self.config = get_config_manager()
        
        # LLM 초기화
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model=settings.default_model,
                temperature=0.3,  # 분석은 일관성이 중요
                api_key=settings.openai_api_key
            )
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.3,
                api_key=settings.anthropic_api_key
            )
        else:
            logger.warning("No LLM API key found, using pattern matching only")
            self.llm = None
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        질의 분석 처리
        
        Args:
            state: Current state with user query
            
        Returns:
            Updated state with analysis results
        """
        query = state.get("query", "")
        
        if not query:
            return {
                "intent": "unknown",
                "entities": {},
                "confidence": 0.0,
                "query_complexity": "simple",
                "selected_agents": []
            }
        
        # 1. 의도 분석
        intent, intent_confidence = self._analyze_intent(query)
        
        # 2. 엔티티 추출
        entities = self._extract_entities(query)
        
        # 3. 복잡도 평가
        complexity = self._evaluate_complexity(query, entities)
        
        # 4. 적합한 에이전트 선택
        recommended_agents = self._recommend_agents(query, intent, entities)
        
        # 5. LLM을 사용한 심화 분석 (가능한 경우)
        if self.llm:
            enhanced_analysis = self._llm_analysis(query, intent, entities)
            if enhanced_analysis:
                intent = enhanced_analysis.get("intent", intent)
                entities.update(enhanced_analysis.get("entities", {}))
                intent_confidence = enhanced_analysis.get("confidence", intent_confidence)
        
        # 6. 분석 결과 로깅
        logger.info(f"Query Analysis Complete:")
        logger.info(f"  - Intent: {intent} (confidence: {intent_confidence:.2f})")
        logger.info(f"  - Entities: {entities}")
        logger.info(f"  - Complexity: {complexity}")
        logger.info(f"  - Recommended agents: {recommended_agents}")
        
        return {
            "intent": intent,
            "entities": entities,
            "confidence": intent_confidence,
            "query_complexity": complexity,
            "selected_agents": recommended_agents,
            "current_step": "analysis_complete"
        }
    
    def _analyze_intent(self, query: str) -> Tuple[str, float]:
        """
        의도 분석
        
        Returns:
            (intent, confidence)
        """
        query_lower = query.lower()
        best_intent = "unknown"
        best_confidence = 0.0
        
        # YAML 설정에서 의도 패턴 확인
        for intent_config in self.config.config.query_analyzer.intent_detection:
            intent_name = intent_config.intent
            keywords = intent_config.keywords
            
            # 키워드 매칭 점수 계산
            matching_keywords = sum(1 for kw in keywords if kw in query_lower)
            
            if matching_keywords > 0:
                # 신뢰도 계산: 매칭된 키워드 비율
                confidence = matching_keywords / len(keywords)
                
                # 임계값 적용
                if confidence >= intent_config.confidence_threshold:
                    if confidence > best_confidence:
                        best_intent = intent_name
                        best_confidence = confidence
        
        # 의도를 찾지 못한 경우 기본값
        if best_intent == "unknown":
            # 질문 패턴으로 추가 판단
            if any(q in query_lower for q in ["뭐", "무엇", "어떤", "어떻게"]):
                best_intent = "information_search"
                best_confidence = 0.5
            elif any(q in query_lower for q in ["계산", "얼마", "비용"]):
                best_intent = "calculation"
                best_confidence = 0.5
            elif any(q in query_lower for q in ["추천", "좋은", "베스트"]):
                best_intent = "recommendation"
                best_confidence = 0.5
        
        return best_intent, best_confidence
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        엔티티 추출
        
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # 위치 엔티티
        location_patterns = [
            r'\b(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\b',
            r'\b\w+[시구동]\b',
            r'\b\w+역\b'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, query)
            if matches:
                entities["location"] = matches
                break
        
        # 가격 엔티티
        price_patterns = [
            (r'(\d+)억', 'billion'),
            (r'(\d+)천만?\s*원?', 'ten_million'),
            (r'(\d+)만\s*원', 'ten_thousand'),
            (r'월세\s*(\d+)', 'monthly_rent')
        ]
        
        for pattern, unit in price_patterns:
            matches = re.findall(pattern, query)
            if matches:
                if "price" not in entities:
                    entities["price"] = []
                for match in matches:
                    entities["price"].append({
                        "value": match,
                        "unit": unit
                    })
        
        # 부동산 타입
        property_types = ["아파트", "빌라", "오피스텔", "단독주택", "다세대", "원룸", "투룸", "쓰리룸"]
        for prop_type in property_types:
            if prop_type in query:
                entities["property_type"] = prop_type
                break
        
        # 거래 타입
        transaction_types = ["매매", "전세", "월세", "반전세"]
        for trans_type in transaction_types:
            if trans_type in query:
                entities["transaction_type"] = trans_type
                break
        
        # 면적
        area_patterns = [
            (r'(\d+)평', 'pyeong'),
            (r'(\d+)㎡', 'sqm'),
            (r'(\d+)평형', 'pyeong_type')
        ]
        
        for pattern, unit in area_patterns:
            matches = re.findall(pattern, query)
            if matches:
                entities["area"] = {
                    "value": matches[0],
                    "unit": unit
                }
                break
        
        # 금융 관련
        if any(word in query for word in ["대출", "DTI", "LTV", "DSR", "금리"]):
            entities["finance_related"] = True
        
        # 법률 관련
        if any(word in query for word in ["계약", "세금", "취득세", "양도세", "등기"]):
            entities["legal_related"] = True
        
        return entities
    
    def _evaluate_complexity(self, query: str, entities: Dict) -> str:
        """
        질의 복잡도 평가
        
        Returns:
            "simple", "moderate", or "complex"
        """
        # 복잡도 점수 계산
        complexity_score = 0
        
        # 질의 길이
        if len(query) > 100:
            complexity_score += 2
        elif len(query) > 50:
            complexity_score += 1
        
        # 엔티티 개수
        entity_count = len(entities)
        if entity_count > 3:
            complexity_score += 2
        elif entity_count > 1:
            complexity_score += 1
        
        # 복합 조건 키워드
        complex_keywords = ["그리고", "또한", "동시에", "비교", "분석", "평가"]
        if any(kw in query for kw in complex_keywords):
            complexity_score += 2
        
        # 숫자나 계산이 포함된 경우
        if re.search(r'\d+', query):
            complexity_score += 1
        
        # 복잡도 판정
        if complexity_score >= 4:
            return "complex"
        elif complexity_score >= 2:
            return "moderate"
        else:
            return "simple"
    
    def _recommend_agents(self, query: str, intent: str, entities: Dict) -> List[str]:
        """
        적합한 에이전트 추천
        
        Returns:
            List of recommended agent IDs
        """
        recommended = []
        
        # 의도 기반 추천
        intent_based = self.config.get_agents_by_intent(intent)
        recommended.extend([agent.id for agent in intent_based])
        
        # 키워드 기반 추천
        keyword_based = self.config.get_agents_by_keywords(query)
        for agent in keyword_based:
            if agent.id not in recommended:
                recommended.append(agent.id)
        
        # 엔티티 기반 추천
        if entities.get("price") or entities.get("property_type"):
            if "price_search_agent" not in recommended:
                recommended.append("price_search_agent")
        
        if entities.get("finance_related"):
            if "finance_agent" not in recommended:
                recommended.append("finance_agent")
        
        if entities.get("location"):
            if "location_agent" not in recommended:
                recommended.append("location_agent")
        
        if entities.get("legal_related"):
            if "legal_agent" not in recommended:
                recommended.append("legal_agent")
        
        # 추천이 없는 경우 기본 에이전트
        if not recommended:
            recommended = ["price_search_agent"]  # 기본값
        
        return recommended[:3]  # 최대 3개 에이전트만 추천
    
    def _llm_analysis(self, query: str, initial_intent: str, initial_entities: Dict) -> Optional[Dict]:
        """
        LLM을 사용한 심화 분석
        
        Returns:
            Enhanced analysis results or None
        """
        if not self.llm:
            return None
        
        try:
            system_prompt = """당신은 부동산 질의 분석 전문가입니다.
사용자의 질의를 분석하여 다음을 파악해주세요:
1. 의도 (information_search, calculation, recommendation, consultation 중 선택)
2. 핵심 엔티티 (위치, 가격, 부동산 타입 등)
3. 신뢰도 (0~1 사이의 값)

JSON 형식으로만 응답하세요."""
            
            user_prompt = f"""질의: {query}

초기 분석:
- 의도: {initial_intent}
- 엔티티: {initial_entities}

더 정확한 분석을 제공해주세요."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # JSON 파싱 시도
            import json
            content = response.content
            
            # JSON 블록 추출
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            
            return {
                "intent": result.get("intent", initial_intent),
                "entities": result.get("entities", {}),
                "confidence": float(result.get("confidence", 0.7))
            }
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return None


# 노드로 사용할 함수 (LangGraph 호환)
def analyzer_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph 노드 함수
    
    Args:
        state: Agent state
        
    Returns:
        Updated state
    """
    agent = AnalyzerAgent()
    return agent(state)