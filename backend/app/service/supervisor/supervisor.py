"""
Real Estate Supervisor - OpenAI Version
LLM = OpenAI
"""

import json
import logging
from typing import Dict, Any, Optional, List
from langgraph.graph import StateGraph, START, END
import sys
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
service_dir = current_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

# Add paths in correct order - most specific first
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Also add app.service to path for direct imports
sys.path.insert(0, str(backend_dir / "app" / "service"))

from core.states import RealEstateMainState
from core.context import LLMContext, create_default_llm_context
from core.config import Config
from core.todo_types import (
    create_todo_dict, update_todo_status, find_todo, get_todo_summary
)

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Centralized LLM Manager for all LLM operations
    Uses LLMContext for configuration (LangGraph 0.6+)
    OpenAI version
    """

    def __init__(self, context: LLMContext = None):
        self.context = context or create_default_llm_context()
        self.client = None
        self._connection_error = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        # Get API key from context first, only fallback to config if context.api_key is None
        # Empty string means explicitly no API key
        if self.context.api_key == "":
            api_key = ""  # Explicitly empty
        else:
            api_key = self.context.api_key or Config.LLM_DEFAULTS.get("api_key")

        if self.context.provider == "openai" and api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=api_key,
                    organization=self.context.organization
                )
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.error("OpenAI library not installed. Install with: pip install openai")
                self._connection_error = "OpenAI 라이브러리가 설치되지 않았습니다."
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self._connection_error = f"OpenAI 연결 실패: {str(e)}"
        elif self.context.provider == "azure":
            # Azure OpenAI support can be added here
            logger.info("Azure OpenAI not yet implemented")
            self._connection_error = "Azure OpenAI는 아직 지원되지 않습니다."
        else:
            if self.context.provider == "openai" and not api_key:
                logger.warning("OPENAI_API_KEY not found")
                self._connection_error = "API 키가 설정되지 않았습니다."
            else:
                self._connection_error = "LLM 공급자가 설정되지 않았습니다."

    def get_model(self, purpose: str) -> str:
        """Get model name for specific purpose"""
        # Check context overrides first
        if self.context.model_overrides and purpose in self.context.model_overrides:
            return self.context.model_overrides[purpose]
        # Use defaults from config
        return Config.LLM_DEFAULTS["models"].get(purpose, "gpt-4o-mini")

    def get_params(self) -> Dict[str, Any]:
        """Get LLM parameters with context overrides"""
        params = Config.LLM_DEFAULTS["default_params"].copy()

        # Apply context overrides if present
        if self.context.temperature is not None:
            params["temperature"] = self.context.temperature
        if self.context.max_tokens is not None:
            params["max_tokens"] = self.context.max_tokens
        if self.context.response_format is not None:
            params["response_format"] = self.context.response_format

        return params

    async def classify_service_relevance(self, query: str) -> Dict[str, Any]:
        """
        Stage 1: Classify if query is relevant to our service
        Uses description-based classification

        Args:
            query: User query

        Returns:
            Classification result with reasoning
        """
        if not self.client:
            return {"is_relevant": False, "reasoning": "시스템 오류"}

        try:
            system_prompt = """당신은 부동산 전문 챗봇 서비스의 관련성 분류기입니다.

이 챗봇의 서비스 범위:
1. 부동산 매매/전세/월세 정보 제공
2. 부동산 시세 및 시장 분석
3. 부동산 관련 법률 및 계약 안내
4. 부동산 대출 및 금융 정보
5. 부동산 투자 및 개발 정보
6. 건축 규제 및 인허가 정보
7. 부동산 세금 및 공과금 안내

서비스 범위에 포함되지 않는 것:
- 일반적인 인사, 감정 표현, 욕설
- 부동산과 무관한 일반 지식 질문
- 다른 산업이나 주제에 대한 질의
- 의미없는 텍스트나 무작위 단어
- 개인 정보나 자기소개 (예: "내 이름은 ~야", "나는 ~다")

중요: 문맥을 우선적으로 판단하세요!
- 부동산 관련 키워드가 있어도 전체 문맥이 부동산과 무관하면 false로 분류
- 예시: "내 이름은 양도세야" → false (개인 소개, 부동산과 무관)
- 예시: "양도세가 뭐야?" → true (부동산 세금 관련 질문)
- 예시: "집값이라는 친구가 있어" → false (개인 이야기, 부동산과 무관)
- 예시: "요즘 집값이 어때?" → true (부동산 시세 관련 질문)

질의가 부동산 서비스와 관련이 있는지 판단하세요.
경계선에 있는 경우(예: 일반 금융이지만 부동산 대출일 수도 있는 경우) true로 분류하세요.

JSON 형식으로 응답:
{
    "is_relevant": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "판단 근거"
}"""

            user_prompt = f"사용자 질의: {query}"

            model = self.get_model("intent")
            params = self.get_params()
            params["temperature"] = 0.1  # Lower temperature for consistent classification

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Service relevance classification failed: {e}")
            return {"is_relevant": True, "reasoning": "분류 실패, 기본 처리"}  # Default to true on error

    async def extract_keywords_for_validation(self, query: str) -> Dict[str, Any]:
        """
        Stage 2: Extract and score keywords for validation

        Args:
            query: User query

        Returns:
            Keywords and relevance score
        """
        if not self.client:
            return {"keywords": [], "score": 0.5}

        try:
            system_prompt = """부동산 관련 키워드를 추출하고 문맥 내 역할을 평가하세요.

부동산 관련 키워드 예시:
- 거래: 매매, 전세, 월세, 임대, 분양
- 부동산 유형: 아파트, 빌라, 오피스텔, 주택, 상가, 토지
- 지역: 강남구, 서초구 등 구체적 지역명
- 금융: 대출, 담보, 금리, LTV, DTI
- 법률: 계약, 등기, 세금, 양도세, 취득세
- 시장: 시세, 가격, 평형, 평수, 매물

중요: 키워드의 문맥상 역할 평가
1. 키워드가 질문의 주제인가? (높은 점수)
2. 키워드가 단순히 언급만 되었는가? (낮은 점수)
3. 부정 패턴이 있는가? (매우 낮은 점수)
   - "내 이름은 [키워드]" → 개인 소개
   - "[키워드]라는 친구/사람" → 인물 언급
   - "나는 [키워드]야/다" → 자기 소개

예시 평가:
- "양도세 계산 방법" → score: 0.9 (주제)
- "내 이름은 양도세야" → score: 0.1 (단순 언급, 부정 패턴)
- "집값 어때?" → score: 0.9 (주제)
- "집값이라는 애가 있어" → score: 0.1 (인물 언급)

JSON 형식으로 응답:
{
    "keywords": ["추출된 키워드"],
    "real_estate_keywords": ["부동산 관련 키워드만"],
    "context_role": "main_topic|mentioned|negative_pattern",
    "negative_patterns": ["발견된 부정 패턴"],
    "score": 0.0-1.0 (문맥 고려한 부동산 관련도)
}"""

            user_prompt = f"질의: {query}"

            model = self.get_model("intent")
            params = self.get_params()
            params["temperature"] = 0.1

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return {"keywords": [], "score": 0.5}

    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user intent from query with two-stage validation

        Args:
            query: User query string

        Returns:
            Intent analysis with entities and confidence
        """
        # Early negative pattern detection
        negative_patterns = [
            r"내\s*이름은.*[야다]",  # "내 이름은 ~야/다"
            r"나는.*[야다]$",  # "나는 ~야/다" at end
            r".*라는\s*(친구|사람|애|놈|녀석)",  # "~라는 친구/사람"
            r"^(안녕|하이|헬로|ㅎㅇ)",  # Simple greetings
            r"^(ㅋ+|ㅎ+|ㅠ+|ㅜ+)$",  # Korean emoticons only
        ]

        import re
        for pattern in negative_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.info(f"Early negative pattern detected: {query}")
                return {
                    "intent_type": "irrelevant",
                    "is_real_estate_related": False,
                    "confidence": 0.95,
                    "message": "죄송합니다. 부동산 관련 질문만 답변 가능합니다.",
                    "reasoning": "개인 소개나 일반 대화로 판단됨"
                }

        # Check for connection errors
        if self._connection_error:
            return {
                "error": True,
                "intent": "error",
                "message": "시스템 연결 오류가 발생했습니다.",
                "details": self._connection_error,
                "suggestion": "잠시 후 다시 시도해주세요."
            }

        if not self.client:
            return {
                "error": True,
                "intent": "error",
                "message": "LLM 클라이언트가 초기화되지 않았습니다.",
                "details": "OpenAI 연결에 실패했습니다.",
                "suggestion": "시스템 관리자에게 문의하세요."
            }

        try:
            # Stage 1: Service relevance classification
            logger.debug(f"Stage 1: Classifying service relevance for: {query}")
            relevance = await self.classify_service_relevance(query)

            # Stage 2: Keyword validation (if needed)
            if relevance.get("confidence", 0) < 0.6:  # Lower threshold for additional validation
                logger.debug(f"Stage 2: Low confidence ({relevance.get('confidence')}), extracting keywords")
                keywords = await self.extract_keywords_for_validation(query)

                # Stage 1 has priority - only use Stage 2 to confirm, not override
                if not relevance.get("is_relevant"):
                    # Stage 1 says irrelevant - only continue if Stage 2 strongly disagrees
                    if keywords.get("score", 0) < 0.7:  # Need very high score to override Stage 1
                        logger.info(f"Query classified as irrelevant (Stage1: {relevance.get('is_relevant')}, Stage2 score: {keywords.get('score')})")
                        return {
                            "intent_type": "irrelevant",
                            "is_real_estate_related": False,
                            "confidence": max(relevance.get("confidence", 0), 1 - keywords.get("score", 0.5)),
                            "message": "죄송합니다. 부동산 관련 질문만 답변 가능합니다.",
                            "reasoning": f"서비스 관련성: {relevance.get('reasoning', 'N/A')}, 키워드 점수: {keywords.get('score', 0):.2f}"
                        }
                    else:
                        # Stage 2 strongly disagrees - continue but log warning
                        logger.warning(f"Stage conflict - Stage1: false, Stage2: {keywords.get('score')} - continuing")
                elif relevance.get("is_relevant") and keywords.get("score", 0) < 0.5:
                    # Stage 1 says relevant but Stage 2 disagrees - trust Stage 1
                    logger.debug(f"Stage1 overrides Stage2 - Stage1: true, Stage2: {keywords.get('score')}")
                    pass
            else:
                # High confidence from Stage 1
                if not relevance.get("is_relevant"):
                    logger.info(f"Query classified as irrelevant with high confidence: {relevance.get('confidence')}")
                    return {
                        "intent_type": "irrelevant",
                        "is_real_estate_related": False,
                        "confidence": relevance.get("confidence", 0.9),
                        "message": "죄송합니다. 부동산 관련 질문만 답변 가능합니다.",
                        "reasoning": relevance.get("reasoning", "서비스 범위 외")
                    }

            # Stage 3: Detailed intent analysis (for relevant queries)
            system_prompt = """당신은 부동산 전문 챗봇의 의도 분석기입니다.
사용자 질의를 분석하여 구체적인 의도와 핵심 정보를 추출하세요.

의도 타입:
- search: 매물/시세 검색
- analysis: 시장 분석
- recommendation: 추천 요청
- legal: 법률/규정 관련
- loan: 대출 관련
- general: 일반 문의
- unclear: 의도가 불명확

JSON 형식으로 응답하세요:
{
    "intent_type": "의도 타입",
    "entities": {
        "region": "지역명",
        "property_type": "부동산 유형",
        "transaction_type": "거래 유형"
    },
    "keywords": ["핵심 키워드"],
    "confidence": 0.0-1.0
}"""

            user_prompt = f"사용자 질의: {query}"

            model = self.get_model("intent")
            params = self.get_params()

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            result = json.loads(response.choices[0].message.content)
            result["is_real_estate_related"] = True  # Already validated in stages 1-2

            return result

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            # Return unclear intent instead of error
            return {
                "intent_type": "unclear",
                "is_real_estate_related": True,  # Give benefit of doubt on error
                "message": "질문을 이해하지 못했습니다. 다음과 같은 형식으로 질문해주세요:",
                "examples": [
                    "강남구 아파트 시세 알려줘",
                    "서초구 30평대 전세 매물 찾아줘",
                    "부동산 계약시 주의사항은?",
                    "주택담보대출 금리 비교해줘"
                ],
                "original_query": query
            }

    async def create_execution_plan(
        self,
        query: str,
        intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            query: User query
            intent: Analyzed intent

        Returns:
            Execution plan with agents and keywords
        """
        # Check for connection errors
        if self._connection_error:
            return {
                "error": True,
                "message": "시스템 연결 오류로 실행 계획을 생성할 수 없습니다.",
                "details": self._connection_error,
                "agents": []
            }

        if not self.client:
            return {
                "error": True,
                "message": "LLM 클라이언트가 초기화되지 않았습니다.",
                "details": "OpenAI 연결에 실패했습니다.",
                "agents": []
            }

        try:
            system_prompt = """당신은 부동산 챗봇의 실행 계획 수립 전문가입니다.
사용자 의도에 따라 가장 적합한 에이전트를 선택하고 실행 계획을 수립하세요.

## 에이전트 상세 명세

### 1. search_agent (검색 에이전트) - [구현 완료]
- **목적**: 부동산 관련 데이터를 검색하고 수집하는 전문 Agent
- **기능(Capabilities)**:
  • 부동산 매물 정보 검색
  • 시세 정보 조회
  • 법률 및 규정 검색
  • 대출 상품 정보 수집
  • 여러 데이터 소스 병렬 검색
  • 검색 결과 구조화 및 요약
- **한계(Limitations)**:
  • 데이터 분석이나 인사이트 도출 불가
  • 추천 로직 수행 불가
  • 복잡한 계산이나 예측 불가
- **사용 가능한 도구**:
  • legal_search: 부동산 법률 정보 검색
  • regulation_search: 부동산 규정 및 정책 검색
  • loan_search: 부동산 대출 상품 검색
  • real_estate_search: 부동산 매물 및 시세 검색
- **적합한 사용 케이스**:
  • 부동산 매물 정보가 필요한 경우
  • 시세 조회가 필요한 경우
  • 법률/규정 정보 검색이 필요한 경우
  • 대출 정보 수집이 필요한 경우
  • 여러 종류의 정보를 동시에 수집해야 하는 경우
- **부적합한 케이스**:
  • 복잡한 데이터 분석이 필요한 경우
  • 투자 추천이 필요한 경우
  • 미래 가격 예측이 필요한 경우

### 2. analysis_agent (분석 에이전트) - [구현 완료]
- **목적**: 수집된 부동산 데이터를 분석하여 인사이트를 도출하는 전문 Agent
- **기능(Capabilities)**:
  • 시장 현황 분석 (가격, 거래량, 수급)
  • 가격 트렌드 및 패턴 분석
  • 지역별/단지별 비교 분석
  • 투자 가치 평가 (ROI, 수익률)
  • 리스크 요인 식별 및 평가
  • 데이터 기반 추천사항 제공
  • 분석 결과 시각화 데이터 준비
- **한계(Limitations)**:
  • 직접적인 데이터 수집 불가 (search_agent 필요)
  • 미래 가격 정확한 예측 불가
  • 법적 구속력 있는 조언 제공 불가
  • 개인 맞춤 투자 전략 수립 불가
- **사용 가능한 도구**:
  • market_analyzer: 시장 현황 분석
  • trend_analyzer: 가격 트렌드 분석
  • comparative_analyzer: 지역별 비교
  • investment_evaluator: 투자 가치 평가
  • risk_assessor: 리스크 평가
- **적합한 사용 케이스**:
  • 시장 트렌드 분석이 필요한 경우
  • 투자 가치 평가가 필요한 경우
  • 지역간 비교 분석이 필요한 경우
  • 리스크 평가가 필요한 경우
  • SearchAgent 수집 데이터의 심층 분석이 필요한 경우
- **부적합한 케이스**:
  • 단순 정보 조회만 필요한 경우
  • 실시간 데이터가 필요한 경우
  • 법률 자문이 필요한 경우

### 3. recommendation_agent (추천 에이전트) - [개발 예정]
- **목적**: 사용자 요구사항에 맞는 부동산 추천을 제공하는 전문 Agent
- **기능(Capabilities)**:
  • 사용자 선호도 분석
  • 맞춤형 매물 추천
  • 투자 포트폴리오 제안
  • 대안 제시
- **한계(Limitations)**:
  • 직접적인 데이터 수집 불가
  • 법적 구속력 있는 조언 불가
- **적합한 사용 케이스**:
  • 맞춤 매물 추천이 필요한 경우
  • 투자 조언이 필요한 경우
- **부적합한 케이스**:
  • 단순 정보 조회만 필요한 경우

## 에이전트 선택 기준

1. **검색/수집이 필요한 경우** → search_agent 선택
   - 키워드: 검색, 조회, 찾기, 알려줘, 정보, 시세, 매물, 법률, 대출

2. **분석이 필요한 경우** → analysis_agent 선택
   - 키워드: 분석, 비교, 평가, 트렌드, 동향, 전망, 시장, 투자, 리스크

3. **추천이 필요한 경우** → recommendation_agent 선택 (미구현 시 search_agent 사용)
   - 키워드: 추천, 제안, 어떤게 좋을까, 적합한, 맞춤

## 실행 계획 수립 지침

1. 사용자 의도를 정확히 파악
2. 필요한 작업을 단계별로 분해
3. 각 단계에 적합한 에이전트 선택
4. 에이전트 간 데이터 흐름 고려
5. 현재 구현된 에이전트만 선택 (search_agent, analysis_agent 사용 가능)

JSON 형식으로 응답하세요:
{
    "agents": ["선택된 에이전트 목록"],
    "collection_keywords": ["수집할 키워드"],
    "execution_order": "sequential 또는 parallel",
    "reasoning": "계획 수립 근거",
    "agent_capabilities_used": ["사용할 에이전트 기능 목록"]
}"""

            user_prompt = f"""사용자 질의: {query}
분석된 의도: {json.dumps(intent, ensure_ascii=False)}"""

            model = self.get_model("planning")
            params = self.get_params()

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **params
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            # Return error instead of falling back
            return {
                "error": True,
                "message": "실행 계획 생성 중 오류가 발생했습니다.",
                "details": str(e),
                "agents": []
            }


class RealEstateSupervisor:
    """
    Main Supervisor for Real Estate Chatbot
    OpenAI version
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_manager = LLMManager(self.llm_context)
        self.workflow = None
        self._build_graph()

    def _route_after_intent(self, state: Dict[str, Any]) -> str:
        """
        Route based on intent classification

        Args:
            state: Current workflow state

        Returns:
            Next node name based on intent type
        """
        intent_type = state.get("intent_type", "")

        if intent_type == "irrelevant":
            logger.debug(f"[ROUTING] Intent type '{intent_type}' -> guidance_message")
            return "guidance_message"
        elif intent_type == "unclear":
            logger.debug(f"[ROUTING] Intent type '{intent_type}' -> recheck_intent")
            return "recheck_intent"
        elif intent_type == "error":
            logger.debug(f"[ROUTING] Intent type '{intent_type}' -> error_handler")
            return "error_handler"
        else:
            logger.debug(f"[ROUTING] Intent type '{intent_type}' -> create_plan")
            return "create_plan"

    def _build_graph(self):
        """Build the workflow graph"""
        self.workflow = StateGraph(state_schema=RealEstateMainState)

        # Add nodes
        self.workflow.add_node("analyze_intent", self.analyze_intent_node)
        self.workflow.add_node("recheck_intent", self.recheck_intent_node)
        self.workflow.add_node("error_handler", self.error_handler_node)
        self.workflow.add_node("guidance_message", self.guidance_message_node)
        self.workflow.add_node("create_plan", self.create_plan_node)
        self.workflow.add_node("execute_agents", self.execute_agents_node)
        self.workflow.add_node("generate_response", self.generate_response_node)

        # Add edges
        self.workflow.add_edge(START, "analyze_intent")

        # Conditional routing after intent analysis
        self.workflow.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {
                "create_plan": "create_plan",
                "recheck_intent": "recheck_intent",
                "error_handler": "error_handler",
                "guidance_message": "guidance_message"
            }
        )

        # Conditional routing after recheck
        self.workflow.add_conditional_edges(
            "recheck_intent",
            lambda state: "guidance_message" if state.get("still_unclear") else "create_plan",
            {
                "create_plan": "create_plan",
                "guidance_message": "guidance_message"
            }
        )

        # Normal flow edges
        self.workflow.add_edge("create_plan", "execute_agents")
        self.workflow.add_edge("execute_agents", "generate_response")

        # Terminal edges to END
        self.workflow.add_edge("error_handler", END)
        self.workflow.add_edge("guidance_message", END)
        self.workflow.add_edge("generate_response", END)

        logger.info("Supervisor workflow graph built successfully")

    async def analyze_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user intent using LLM

        Args:
            state: Current state

        Returns:
            Updated state with intent analysis
        """
        query = state["query"]
        logger.info(f"Analyzing intent for query: {query}")
        logger.debug(f"[NODE] analyze_intent_node - Input state keys: {list(state.keys())}")

        intent = await self.llm_manager.analyze_intent(query)
        logger.debug(f"[LLM] analyze_intent result: intent_type={intent.get('intent_type')}, confidence={intent.get('confidence')}")

        # Check if query is not related to real estate
        if not intent.get("is_real_estate_related", True) or intent.get("intent_type") == "irrelevant":
            logger.info(f"Query is irrelevant to real estate: {query}")
            return {
                "intent": intent,
                "intent_type": "irrelevant"
            }

        # Check for low confidence
        if intent.get("confidence", 0) < 0.3:
            logger.info(f"Low confidence query: {query} (confidence={intent.get('confidence')})")
            return {
                "intent": intent,
                "intent_type": "unclear",
                "confidence": intent.get("confidence", 0)
            }

        # Check for errors
        if intent.get("error"):
            logger.info(f"Error in intent analysis: {intent.get('message')}")
            return {
                "intent": intent,
                "intent_type": "error"
            }

        # Check for unclear intent from LLM
        if intent.get("intent_type") == "unclear":
            logger.info(f"Unclear intent from LLM: {query}")
            return {
                "intent": intent,
                "intent_type": "unclear"
            }

        result = {
            "intent": intent,
            "intent_type": intent.get("intent_type", "general"),
            "intent_confidence": intent.get("confidence", 0.0)
        }
        logger.debug(f"[NODE] analyze_intent_node - Output state changes: {list(result.keys())}")
        return result

    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            state: Current state

        Returns:
            Updated state with execution plan
        """
        query = state["query"]
        intent = state["intent"]

        logger.info(f"Creating execution plan for intent: {intent.get('intent_type')}")

        plan = await self.llm_manager.create_execution_plan(query, intent)

        # Check for plan creation errors
        if plan.get("error"):
            logger.error(f"Plan creation failed: {plan.get('message')}")
            return {
                "execution_plan": plan,
                "planning_error": True,
                "error_message": plan.get("message"),
                "error_details": plan.get("details"),
                "selected_agents": []
            }

        # Create TODOs for selected agents
        todos = state.get("todos", [])
        todo_counter = state.get("todo_counter", 0)
        selected_agents = plan.get("agents", [])

        # Create main TODO for each selected agent
        for agent_name in selected_agents:
            todo_id = f"main_{todo_counter}"
            todo = create_todo_dict(
                todo_id=todo_id,
                level="supervisor",
                task=f"Execute {agent_name}",
                agent=agent_name,
                purpose=plan.get("reasoning", ""),
                subtodos=[]  # Agent will fill this
            )
            todos.append(todo)
            todo_counter += 1
            logger.debug(f"[TODO] Created main TODO: {todo_id} for {agent_name}")

        result = {
            "execution_plan": plan,
            "collection_keywords": plan.get("collection_keywords", []),
            "selected_agents": selected_agents,
            "todos": todos,
            "todo_counter": todo_counter,
            "current_phase": "executing"
        }
        logger.debug(f"[NODE] create_plan_node - Created {len(selected_agents)} TODOs")
        return result

    async def execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute selected agents

        Args:
            state: Current state

        Returns:
            Updated state with agent results
        """
        # Skip if there was a planning error
        if state.get("planning_error"):
            logger.debug("[NODE] execute_agents_node - Skipping due to planning error")
            return state

        selected_agents = state.get("selected_agents", [])
        todos = state.get("todos", [])
        logger.info(f"Executing agents: {selected_agents}")
        logger.debug(f"[NODE] execute_agents_node - Starting with {len(selected_agents)} agents")

        agent_results = {}

        for agent_name in selected_agents:
            # Find and update TODO status
            agent_todo = find_todo(todos, agent=agent_name)
            if agent_todo:
                todos = update_todo_status(todos, agent_todo["id"], "in_progress")
                logger.debug(f"[TODO] Updated {agent_todo['id']} to in_progress")

            logger.debug(f"[AGENT] Executing agent: {agent_name}")
            if agent_name == "search_agent":
                # Import and execute search agent
                from agents.search_agent import SearchAgent

                agent = SearchAgent(llm_context=self.llm_context)
                input_data = {
                    "original_query": state["query"],
                    "collection_keywords": state.get("collection_keywords", []),
                    "shared_context": state.get("shared_context", {}),
                    "chat_session_id": state.get("chat_session_id", ""),
                    "parent_todo_id": agent_todo["id"] if agent_todo else None,
                    "todos": todos,  # Pass todos to agent
                    "todo_counter": state.get("todo_counter", 0)
                }

                # SearchAgent uses app.ainvoke instead of run
                result = await agent.app.ainvoke(input_data)

                # Update TODO status based on result
                if agent_todo:
                    if result.get("status") == "completed":
                        todos = update_todo_status(todos, agent_todo["id"], "completed")
                        logger.debug(f"[TODO] Updated {agent_todo['id']} to completed")
                    elif result.get("status") == "error":
                        todos = update_todo_status(todos, agent_todo["id"], "failed", result.get("error"))
                        logger.debug(f"[TODO] Updated {agent_todo['id']} to failed")

                    # Merge any TODO updates from agent
                    if "todos" in result:
                        from core.todo_types import merge_todos
                        todos = merge_todos(todos, result["todos"])

                logger.debug(f"[AGENT] {agent_name} result: status={result.get('status')}, collected_data_keys={list(result.get('collected_data', {}).keys())}")
                agent_results[agent_name] = result

            elif agent_name == "analysis_agent":
                # Import and execute analysis agent
                from agents.analysis_agent import AnalysisAgent

                agent = AnalysisAgent(llm_context=self.llm_context)

                # Prepare input data for analysis
                # Check if we have data from SearchAgent
                search_data = agent_results.get("search_agent", {}).get("collected_data", {})
                if not search_data:
                    # If no search data, check if there's data in state
                    search_data = state.get("collected_data", {})

                input_data = {
                    "original_query": state["query"],
                    "analysis_type": state.get("analysis_type", "comprehensive"),
                    "input_data": search_data,
                    "shared_context": state.get("shared_context", {}),
                    "chat_session_id": state.get("chat_session_id", ""),
                    "parent_todo_id": agent_todo["id"] if agent_todo else None,
                    "todos": todos,
                    "todo_counter": state.get("todo_counter", 0)
                }

                # Execute AnalysisAgent
                result = await agent.app.ainvoke(input_data)

                # Update TODO status based on result
                if agent_todo:
                    if result.get("status") == "completed":
                        todos = update_todo_status(todos, agent_todo["id"], "completed")
                        logger.debug(f"[TODO] Updated {agent_todo['id']} to completed")
                    elif result.get("status") == "error":
                        todos = update_todo_status(todos, agent_todo["id"], "failed", result.get("error"))
                        logger.debug(f"[TODO] Updated {agent_todo['id']} to failed")

                    # Merge any TODO updates from agent
                    if "todos" in result:
                        from core.todo_types import merge_todos
                        todos = merge_todos(todos, result["todos"])

                logger.debug(f"[AGENT] {agent_name} result: status={result.get('status')}, report_generated={result.get('final_report') is not None}")
                agent_results[agent_name] = result

            else:
                logger.warning(f"Unknown agent: {agent_name}")

        # Get TODO summary
        summary = get_todo_summary(todos)
        logger.info(f"[TODO] Progress: {summary['summary']}")

        result = {
            "agent_results": agent_results,
            "status": "agents_executed",
            "todos": todos,  # Return updated todos
            "current_phase": "evaluating"
        }
        logger.debug(f"[NODE] execute_agents_node - Completed. Agents executed: {list(agent_results.keys())}")
        return result

    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final response based on agent results

        Args:
            state: Current state

        Returns:
            Updated state with final response
        """
        logger.info("Generating final response")

        # Handle planning error
        if state.get("planning_error"):
            logger.info("Handling planning error in response generation")
            return {
                "final_response": {
                    "type": "error",
                    "error_type": "planning_failed",
                    "message": state.get("error_message", "실행 계획 생성 중 오류가 발생했습니다."),
                    "details": state.get("error_details", ""),
                    "suggestion": "다시 시도하거나 다른 방식으로 질문해주세요."
                }
            }

        agent_results = state.get("agent_results", {})

        # Check if search_agent returned direct output
        search_result = agent_results.get("search_agent", {})
        if search_result.get("direct_output"):
            return {
                "final_response": search_result["direct_output"],
                "response_type": "direct"
            }

        # Process all agent results
        all_data = {}
        for agent_name, result in agent_results.items():
            if result.get("status") == "success":
                all_data[agent_name] = result.get("data", {})

        # Create summary
        summary = "데이터 수집 완료"
        if all_data:
            summary = f"{len(all_data)}개의 에이전트에서 데이터 수집 완료"

        final_response = {
            "type": "processed",
            "data": all_data,
            "summary": summary
        }

        result = {
            "final_response": final_response,
            "response_type": "processed"
        }
        logger.debug(f"[NODE] generate_response_node - Completed with response type: {final_response.get('type')}")
        return result

    async def error_handler_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle different types of errors with specific responses

        Args:
            state: Current state

        Returns:
            Updated state with error-specific response
        """
        logger.info("Handling error response")
        intent = state.get("intent", {})
        error_details = intent.get("details", "")

        # Categorize error types and provide specific responses
        if "API 키가 설정되지 않았습니다" in error_details:
            error_type = "api_key_missing"
            message = "API 키가 설정되지 않았습니다."
            suggestion = "환경 변수에 OPENAI_API_KEY를 설정해주세요."
        elif "OpenAI 라이브러리가 설치되지 않았습니다" in error_details:
            error_type = "library_missing"
            message = "필요한 라이브러리가 설치되지 않았습니다."
            suggestion = "pip install openai 명령으로 설치해주세요."
        elif "OpenAI 연결 실패" in error_details:
            error_type = "connection_failed"
            message = "OpenAI 서버 연결에 실패했습니다."
            suggestion = "네트워크 연결을 확인하고 잠시 후 다시 시도해주세요."
        elif "Azure OpenAI는 아직 지원되지 않습니다" in error_details:
            error_type = "not_supported"
            message = "Azure OpenAI는 아직 지원되지 않습니다."
            suggestion = "OpenAI API를 사용해주세요."
        elif "LLM 공급자가 설정되지 않았습니다" in error_details:
            error_type = "provider_missing"
            message = "LLM 공급자가 설정되지 않았습니다."
            suggestion = "설정 파일에서 LLM provider를 확인해주세요."
        elif "LLM 클라이언트가 초기화되지 않았습니다" in error_details:
            error_type = "client_init_failed"
            message = "LLM 클라이언트 초기화에 실패했습니다."
            suggestion = "시스템 관리자에게 문의하세요."
        else:
            error_type = "unknown_error"
            message = intent.get("message", "알 수 없는 시스템 오류가 발생했습니다.")
            suggestion = intent.get("suggestion", "시스템 관리자에게 문의하세요.")

        logger.debug(f"[ERROR_HANDLER] Error type: {error_type}, Details: {error_details}")

        from datetime import datetime
        return {
            "final_response": {
                "type": "error",
                "error_type": error_type,
                "message": message,
                "details": error_details,
                "suggestion": suggestion,
                "timestamp": datetime.now().isoformat()
            }
        }

    async def recheck_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recheck unclear intents with more context and keyword extraction

        Args:
            state: Current state

        Returns:
            Updated state with recheck results
        """
        query = state["query"]
        logger.info(f"Rechecking unclear intent for query: {query}")

        try:
            # Try keyword extraction for additional validation
            keywords = await self.llm_manager.extract_keywords_for_validation(query)
            logger.debug(f"[RECHECK] Extracted keywords: {keywords.get('keywords', [])}, Score: {keywords.get('score', 0)}")

            if keywords.get("score", 0) < 0.3:
                # Still unclear after keyword extraction
                logger.info(f"Query still unclear after recheck (score: {keywords.get('score', 0)})")
                return {
                    "still_unclear": True,
                    "recheck_result": "failed",
                    "keywords": keywords.get("keywords", []),
                    "real_estate_keywords": keywords.get("real_estate_keywords", [])
                }
            else:
                # Found relevant keywords, can proceed
                logger.info(f"Query clarified through keywords (score: {keywords.get('score', 0)})")
                return {
                    "still_unclear": False,
                    "recheck_result": "success",
                    "intent_type": "general",  # Default to general processing
                    "keywords": keywords.get("keywords", []),
                    "real_estate_keywords": keywords.get("real_estate_keywords", []),
                    "collection_keywords": keywords.get("real_estate_keywords", [])
                }
        except Exception as e:
            logger.error(f"Recheck failed: {e}")
            # On error, treat as still unclear
            return {
                "still_unclear": True,
                "recheck_result": "error",
                "error_message": str(e)
            }

    async def guidance_message_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide guidance message for unclassified or unclear queries

        Args:
            state: Current state

        Returns:
            Updated state with guidance response
        """
        logger.info("Generating guidance message")
        intent_type = state.get("intent_type", "")
        intent = state.get("intent", {})
        query = state["query"]

        if intent_type == "irrelevant":
            message = f"사용자 메시지는 '{query}'입니다.\n죄송합니다. 부동산 관련 질문만 답변 가능합니다."
            suggestion = "부동산 매매, 전세, 시세, 대출 등에 대해 다시 질문해주세요."
            examples = [
                "강남구 아파트 시세 알려줘",
                "주택담보대출 금리는?",
                "전세 계약시 주의사항은?",
                "부동산 양도세 계산 방법은?"
            ]
            response_type = "irrelevant"
        elif state.get("still_unclear"):
            message = f"사용자 메시지는 '{query}'입니다.\n질문을 명확히 이해하지 못했습니다."
            suggestion = "더 구체적으로 다시 질문해주세요."
            examples = intent.get("examples", [
                "특정 지역의 부동산 시세를 알고 싶으시면: '강남구 아파트 시세'",
                "대출 정보를 원하시면: '주택담보대출 조건'",
                "법률 정보가 필요하시면: '전세 계약서 작성 방법'"
            ])
            response_type = "unclear"
        else:
            # Generic guidance
            base_message = intent.get("message", "요청을 처리할 수 없습니다.")
            message = f"사용자 메시지는 '{query}'입니다.\n{base_message}"
            suggestion = intent.get("suggestion", "다른 방식으로 다시 질문해주세요.")
            examples = intent.get("examples", [])
            response_type = "guidance"

        logger.debug(f"[GUIDANCE] Type: {response_type}, Message: {message}")

        return {
            "final_response": {
                "type": response_type,
                "message": message,
                "suggestion": suggestion,
                "examples": examples,
                "original_query": state["query"],
                "extracted_keywords": state.get("keywords", [])
            }
        }

    async def process_query(
        self,
        query: str,
        session_id: str = None,
        llm_context: LLMContext = None
    ) -> Dict[str, Any]:
        """
        Process user query through the workflow

        Args:
            query: User query
            session_id: Session ID
            llm_context: Optional LLM context override

        Returns:
            Complete state with final response
        """
        logger.info(f"Processing query: {query}")

        # Use override context if provided
        if llm_context:
            self.llm_context = llm_context
            self.llm_manager = LLMManager(llm_context)

        # Initialize state
        initial_state = {
            "query": query,
            "chat_session_id": session_id or "default_session",
            "shared_context": {},
            "messages": []
        }

        # Compile and run workflow
        app = self.workflow.compile()
        final_state = await app.ainvoke(initial_state)

        logger.info("Query processing completed")
        return final_state


# For backwards compatibility
def create_supervisor(llm_context: LLMContext = None) -> RealEstateSupervisor:
    """
    Factory function to create supervisor

    Args:
        llm_context: Optional LLM context

    Returns:
        Configured RealEstateSupervisor instance
    """
    return RealEstateSupervisor(llm_context=llm_context)


if __name__ == "__main__":
    import asyncio

    async def test_supervisor():
        # Example usage
        supervisor = RealEstateSupervisor()
        result = await supervisor.process_query(
            query="강남구 아파트 시세 알려줘",
            session_id="test_session"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(test_supervisor())