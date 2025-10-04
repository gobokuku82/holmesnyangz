"""
Planning Agent - 의도 분석 및 실행 계획 수립 전담
Supervisor의 계획 관련 로직을 분리하여 독립적으로 관리
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Path setup
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.agent_registry import AgentRegistry
from app.service_agent.foundation.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """의도 타입 정의"""
    LEGAL_CONSULT = "법률상담"
    MARKET_INQUIRY = "시세조회"
    LOAN_CONSULT = "대출상담"
    CONTRACT_CREATION = "계약서작성"
    CONTRACT_REVIEW = "계약서검토"
    COMPREHENSIVE = "종합분석"
    RISK_ANALYSIS = "리스크분석"
    UNCLEAR = "unclear"
    IRRELEVANT = "irrelevant"
    ERROR = "error"


class ExecutionStrategy(Enum):
    """실행 전략"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


@dataclass
class IntentResult:
    """의도 분석 결과"""
    intent_type: IntentType
    confidence: float
    keywords: List[str] = field(default_factory=list)
    reasoning: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    suggested_agents: List[str] = field(default_factory=list)
    fallback: bool = False


@dataclass
class ExecutionStep:
    """실행 단계"""
    agent_name: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 1
    optional: bool = False


@dataclass
class ExecutionPlan:
    """실행 계획"""
    steps: List[ExecutionStep]
    strategy: ExecutionStrategy
    intent: IntentResult
    estimated_time: float = 0.0
    parallel_groups: List[List[str]] = field(default_factory=list)
    error_handling: str = "continue"  # continue, stop, rollback
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlanningAgent:
    """
    의도 분석 및 실행 계획 수립을 전담하는 Agent
    """

    def __init__(self, llm_client=None):
        """
        초기화

        Args:
            llm_client: LLM 클라이언트 (Optional)
        """
        self.llm_client = llm_client
        self.intent_patterns = self._initialize_intent_patterns()
        self.agent_capabilities = self._load_agent_capabilities()

    def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """의도 패턴 초기화"""
        return {
            IntentType.LEGAL_CONSULT: ["법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신"],
            IntentType.MARKET_INQUIRY: ["시세", "가격", "매매가", "전세가", "시장", "동향", "평균"],
            IntentType.LOAN_CONSULT: ["대출", "금리", "한도", "조건", "상환", "LTV", "DTI"],
            IntentType.CONTRACT_CREATION: ["작성", "만들", "생성", "초안"],
            IntentType.CONTRACT_REVIEW: ["검토", "확인", "점검", "리뷰", "분석해"],
            IntentType.COMPREHENSIVE: ["종합", "전체", "모든", "분석", "평가"],
            IntentType.RISK_ANALYSIS: ["위험", "리스크", "주의", "문제점"]
        }

    def _load_agent_capabilities(self) -> Dict[str, Any]:
        """Agent 능력 정보 로드"""
        capabilities = {}
        for agent_name in AgentRegistry.list_agents():
            agent_caps = AgentRegistry.get_capabilities(agent_name)
            if agent_caps:
                capabilities[agent_name] = agent_caps
        return capabilities

    async def analyze_intent(self, query: str, context: Optional[Dict] = None) -> IntentResult:
        """
        사용자 의도 분석

        Args:
            query: 사용자 쿼리
            context: 추가 컨텍스트

        Returns:
            의도 분석 결과
        """
        logger.info(f"Analyzing intent for query: {query[:100]}...")

        # LLM을 사용한 분석 (가능한 경우)
        if self.llm_client:
            try:
                return await self._analyze_with_llm(query, context)
            except Exception as e:
                logger.warning(f"LLM analysis failed, falling back to pattern matching: {e}")

        # 패턴 매칭 기반 분석 (fallback)
        return self._analyze_with_patterns(query, context)

    async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
        """LLM을 사용한 의도 분석"""
        system_prompt = """당신은 부동산 AI 시스템의 의도 분석 전문가입니다.
사용자의 질문을 정확히 이해하고, 어떤 종류의 도움이 필요한지 분류해야 합니다.

## 분류 카테고리 설명:

1. **LEGAL_CONSULT (법률상담)**
   - 설명: 부동산 관련 법률, 권리, 의무에 대한 질문
   - 예시: "전세금 5% 인상이 가능한가요?", "임대차계약 갱신 거부할 수 있나요?", "보증금 반환 안 받으면 어떻게 하나요?"
   - 키워드: 법, 전세, 임대, 보증금, 계약, 권리, 의무, 갱신, 임차인, 임대인, 법률
   - 필요한 처리: 법률 데이터베이스 검색, 관련 법조항 찾기

2. **MARKET_INQUIRY (시세조회)**
   - 설명: 부동산 시장 가격, 시세, 거래 동향에 대한 질문
   - 예시: "강남구 아파트 전세 시세 알려주세요", "서초동 매매가 얼마나 올랐나요?", "평당 가격이 궁금해요"
   - 키워드: 시세, 가격, 매매가, 전세가, 월세, 시장, 동향, 평균, 지역명
   - 필요한 처리: 부동산 시세 데이터 조회, 지역별 가격 분석

3. **LOAN_CONSULT (대출상담)**
   - 설명: 주택담보대출, 전세자금대출 등 금융 관련 질문
   - 예시: "전세자금대출 한도가 얼마인가요?", "LTV가 뭔가요?", "대출 금리 비교해주세요"
   - 키워드: 대출, 금리, 한도, 조건, 상환, LTV, DTI, DSR, 담보, 금융
   - 필요한 처리: 대출 상품 조회, 금리 정보 검색, 한도 계산

4. **CONTRACT_CREATION (계약서작성)**
   - 설명: 새로운 계약서나 문서를 작성해달라는 요청
   - 예시: "임대차계약서 작성해주세요", "전세계약서 초안 만들어주세요", "특약사항 추가해서 계약서 만들어줘"
   - 키워드: 작성, 만들, 생성, 초안, 계약서, 문서
   - 필요한 처리: 문서 생성 에이전트 호출, 템플릿 기반 작성

5. **CONTRACT_REVIEW (계약서검토)**
   - 설명: 기존 계약서나 문서를 검토해달라는 요청
   - 예시: "이 계약서 검토해주세요", "특약사항 문제없나요?", "계약 조건 확인해주세요"
   - 키워드: 검토, 확인, 점검, 리뷰, 분석해, 살펴봐
   - 필요한 처리: 문서 분석, 위험 요소 식별, 개선사항 제안

6. **COMPREHENSIVE (종합분석)**
   - 설명: 여러 측면을 종합적으로 분석해달라는 요청
   - 예시: "이 물건 전체적으로 분석해주세요", "모든 조건 고려해서 평가해줘", "종합적인 의견 부탁해요"
   - 키워드: 종합, 전체, 모든, 전반적, 종합적, 평가
   - 필요한 처리: 다중 데이터 소스 통합 분석

7. **RISK_ANALYSIS (리스크분석)**
   - 설명: 위험 요소나 주의사항에 대한 질문
   - 예시: "이 계약 위험한가요?", "주의할 점 알려주세요", "문제점이 뭐가 있나요?"
   - 키워드: 위험, 리스크, 주의, 문제점, 조심, 걱정
   - 필요한 처리: 위험 요소 분석, 주의사항 추출

8. **UNCLEAR (불분명)**
   - 설명: 의도를 명확히 파악하기 어려운 질문
   - 예시: "이거 좀 봐주세요", "어떻게 해야 할까요?", "도와주세요"
   - 처리: 추가 질문으로 의도 명확화 필요

9. **IRRELEVANT (무관)**
   - 설명: 부동산과 전혀 관련 없는 질문
   - 예시: "날씨 어때?", "저녁 뭐 먹지?", "주식 추천해줘"
   - 처리: 부동산 관련 질문을 유도

## 응답 형식 (JSON 형식으로 응답):

{
    "intent": "카테고리명 (위 9개 중 하나, 대문자와 언더스코어 그대로 사용)",
    "confidence": 0.0~1.0 (판단 확신도, 0.8 이상이면 매우 확실, 0.5 미만이면 불확실),
    "keywords": ["추출된", "주요", "키워드", "목록"],
    "entities": {
        "location": "지역명 (예: 강남구, 서초동)",
        "price": "가격정보 (예: 5억, 10억원)",
        "contract_type": "계약유형 (예: 전세, 월세, 매매)",
        "date": "날짜정보",
        "area": "면적정보",
        "기타_추출된_엔티티": "값"
    },
    "reasoning": "이 카테고리로 분류한 구체적인 이유와 근거 (상세하게)"
}

## 판단 가이드:
- 여러 의도가 섞여있다면, 가장 주된 의도 하나를 선택
- 법률 관련 키워드가 있으면 LEGAL_CONSULT 우선
- 가격/시세 언급이 명확하면 MARKET_INQUIRY
- 계약서라는 단어와 함께 "작성/만들기"가 있으면 CONTRACT_CREATION
- 계약서라는 단어와 함께 "검토/확인"이 있으면 CONTRACT_REVIEW
- 불확실하면 confidence를 낮게 설정하고 UNCLEAR 선택"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"분석할 질문: {query}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"LLM Intent Analysis Result: {result}")

            # Intent 타입 파싱
            intent_str = result.get("intent", "UNCLEAR").upper()
            try:
                intent_type = IntentType[intent_str]
            except KeyError:
                logger.warning(f"Unknown intent type from LLM: {intent_str}, using UNCLEAR")
                intent_type = IntentType.UNCLEAR

            return IntentResult(
                intent_type=intent_type,
                confidence=result.get("confidence", 0.5),
                keywords=result.get("keywords", []),
                reasoning=result.get("reasoning", ""),
                entities=result.get("entities", {}),
                suggested_agents=self._suggest_agents(intent_type),
                fallback=False
            )

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            raise

    def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
        """패턴 매칭 기반 의도 분석"""
        detected_intents = {}
        found_keywords = []

        # 각 의도 타입별 점수 계산
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in query.lower():
                    score += 1
                    found_keywords.append(pattern)
            if score > 0:
                detected_intents[intent_type] = score

        # 가장 높은 점수의 의도 선택
        if detected_intents:
            best_intent = max(detected_intents.items(), key=lambda x: x[1])
            intent_type = best_intent[0]
            confidence = min(best_intent[1] * 0.3, 1.0)
        else:
            intent_type = IntentType.UNCLEAR
            confidence = 0.0

        return IntentResult(
            intent_type=intent_type,
            confidence=confidence,
            keywords=found_keywords,
            reasoning="Pattern-based analysis",
            suggested_agents=self._suggest_agents(intent_type),
            fallback=True
        )

    def _suggest_agents(self, intent_type: IntentType) -> List[str]:
        """의도에 따른 Agent 추천 (Team 기반 아키텍처용)"""
        # Team 이름으로 매핑 (agent -> team)
        agent_mapping = {
            IntentType.LEGAL_CONSULT: ["search_team"],  # 법률 DB 검색
            IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],  # 시세 조회 + 분석
            IntentType.LOAN_CONSULT: ["search_team", "analysis_team"],  # 대출 상품 검색 + 분석
            IntentType.CONTRACT_CREATION: ["document_team"],  # 문서 생성
            IntentType.CONTRACT_REVIEW: ["analysis_team"],  # 계약서 분석 (review -> analysis)
            IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],  # 종합 상담
            IntentType.RISK_ANALYSIS: ["search_team", "analysis_team"],  # 리스크 분석
            IntentType.UNCLEAR: ["search_team"],  # 불명확한 경우 기본 검색
            IntentType.IRRELEVANT: [],
            IntentType.ERROR: []
        }
        result = agent_mapping.get(intent_type, ["search_team"])
        logger.debug(f"Suggested teams for {intent_type.value}: {result}")
        return result

    async def create_execution_plan(
        self,
        intent: IntentResult,
        available_agents: Optional[List[str]] = None
    ) -> ExecutionPlan:
        """
        실행 계획 생성

        Args:
            intent: 의도 분석 결과
            available_agents: 사용 가능한 Agent 목록

        Returns:
            실행 계획
        """
        logger.info(f"Creating execution plan for intent: {intent.intent_type.value}")

        # 사용 가능한 Agent 확인
        if available_agents is None:
            available_agents = AgentRegistry.list_agents(enabled_only=True)

        # 추천 Agent 중 사용 가능한 것만 필터링
        logger.debug(f"Suggested agents: {intent.suggested_agents}")
        logger.debug(f"Available agents: {available_agents}")

        selected_agents = [
            agent for agent in intent.suggested_agents
            if agent in available_agents
        ]

        # Team 기반 아키텍처를 위한 폴백
        if not selected_agents:
            # Team 이름으로 시도
            if "search_team" in available_agents:
                selected_agents = ["search_team"]
            # 기존 agent 이름으로 폴백
            elif "search_agent" in available_agents:
                selected_agents = ["search_agent"]

        logger.info(f"Selected agents/teams for execution: {selected_agents}")

        # 실행 단계 생성
        steps = self._create_execution_steps(selected_agents, intent)

        # 전략 결정
        strategy = self._determine_strategy(intent, steps)

        # 병렬 그룹 생성
        parallel_groups = self._create_parallel_groups(steps) if strategy == ExecutionStrategy.PARALLEL else []

        return ExecutionPlan(
            steps=steps,
            strategy=strategy,
            intent=intent,
            estimated_time=self._estimate_execution_time(steps),
            parallel_groups=parallel_groups,
            metadata={"created_by": "PlanningAgent"}
        )

    def _create_execution_steps(
        self,
        selected_agents: List[str],
        intent: IntentResult
    ) -> List[ExecutionStep]:
        """실행 단계 생성"""
        steps = []

        for i, agent_name in enumerate(selected_agents):
            dependencies = []

            # Agent별 의존성 설정
            if agent_name == "analysis_agent" and "search_agent" in selected_agents:
                dependencies = ["search_agent"]
            elif agent_name == "review_agent" and "document_agent" in selected_agents:
                dependencies = ["document_agent"]

            step = ExecutionStep(
                agent_name=agent_name,
                priority=i,
                dependencies=dependencies,
                input_mapping=self._create_input_mapping(agent_name, intent),
                timeout=30 if agent_name != "analysis_agent" else 45,
                retry_count=2 if agent_name == "search_agent" else 1,
                optional=False
            )
            steps.append(step)

        return steps

    def _create_input_mapping(self, agent_name: str, intent: IntentResult) -> Dict[str, str]:
        """Agent별 입력 매핑 생성"""
        base_mapping = {
            "keywords": "intent.keywords",
            "entities": "intent.entities"
        }

        agent_specific = {
            "analysis_agent": {
                "input_data": "search_agent.collected_data",
                "analysis_type": "comprehensive"
            },
            "document_agent": {
                "document_type": intent.entities.get("document_type", "lease_contract"),
                "params": "intent.entities"
            },
            "review_agent": {
                "document": "document_agent.generated_document",
                "review_type": "comprehensive"
            }
        }

        mapping = base_mapping.copy()
        if agent_name in agent_specific:
            mapping.update(agent_specific[agent_name])

        return mapping

    def _determine_strategy(self, intent: IntentResult, steps: List[ExecutionStep]) -> ExecutionStrategy:
        """실행 전략 결정"""
        # 의존성이 있는 경우
        has_dependencies = any(step.dependencies for step in steps)
        if has_dependencies:
            return ExecutionStrategy.SEQUENTIAL

        # 복합 분석이나 리스크 분석은 병렬 처리
        if intent.intent_type in [IntentType.COMPREHENSIVE, IntentType.RISK_ANALYSIS]:
            if len(steps) > 1:
                return ExecutionStrategy.PARALLEL

        # 문서 생성-검토는 파이프라인
        agent_names = [step.agent_name for step in steps]
        if "document_agent" in agent_names and "review_agent" in agent_names:
            return ExecutionStrategy.PIPELINE

        return ExecutionStrategy.SEQUENTIAL

    def _create_parallel_groups(self, steps: List[ExecutionStep]) -> List[List[str]]:
        """병렬 실행 그룹 생성"""
        groups = []
        processed = set()

        for step in steps:
            if step.agent_name in processed:
                continue

            # 의존성이 없는 Agent들을 그룹화
            if not step.dependencies:
                group = [step.agent_name]
                for other in steps:
                    if (other.agent_name not in processed and
                        not other.dependencies and
                        other.agent_name != step.agent_name):
                        group.append(other.agent_name)
                        processed.add(other.agent_name)

                groups.append(group)
                processed.add(step.agent_name)

        # 의존성이 있는 Agent들은 별도 그룹
        for step in steps:
            if step.agent_name not in processed:
                groups.append([step.agent_name])

        return groups

    def _estimate_execution_time(self, steps: List[ExecutionStep]) -> float:
        """예상 실행 시간 계산"""
        if not steps:
            return 0.0

        total_time = 0.0
        for step in steps:
            # 병렬 실행 가능한 경우 최대 시간만 계산
            if not step.dependencies:
                total_time = max(total_time, step.timeout)
            else:
                total_time += step.timeout

        return total_time

    async def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        실행 계획 최적화

        Args:
            plan: 원본 실행 계획

        Returns:
            최적화된 실행 계획
        """
        logger.info("Optimizing execution plan")

        # 1. 불필요한 Agent 제거
        optimized_steps = self._remove_redundant_agents(plan.steps)

        # 2. 병렬화 가능성 재검토
        if len(optimized_steps) > 1:
            plan.strategy = self._determine_strategy(plan.intent, optimized_steps)
            if plan.strategy == ExecutionStrategy.PARALLEL:
                plan.parallel_groups = self._create_parallel_groups(optimized_steps)

        # 3. 타임아웃 조정
        for step in optimized_steps:
            if plan.intent.confidence < 0.5:
                step.timeout = int(step.timeout * 1.2)  # 불확실한 경우 시간 증가

        plan.steps = optimized_steps
        plan.estimated_time = self._estimate_execution_time(optimized_steps)

        return plan

    def _remove_redundant_agents(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        """중복/불필요한 Agent 제거"""
        # 현재는 단순 구현 - 추후 고도화 가능
        return steps

    async def validate_dependencies(self, plan: ExecutionPlan) -> Tuple[bool, List[str]]:
        """
        의존성 검증

        Args:
            plan: 실행 계획

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        for step in plan.steps:
            # 의존성이 있는 Agent 확인
            for dep in step.dependencies:
                dep_exists = any(s.agent_name == dep for s in plan.steps)
                if not dep_exists:
                    errors.append(f"Agent '{step.agent_name}' depends on missing '{dep}'")

            # Agent가 Registry에 있는지 확인
            if not AgentRegistry.get_agent(step.agent_name):
                errors.append(f"Agent '{step.agent_name}' not found in registry")

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_plan_summary(self, plan: ExecutionPlan) -> str:
        """실행 계획 요약"""
        summary_parts = [
            f"Intent: {plan.intent.intent_type.value} (confidence: {plan.intent.confidence:.2f})",
            f"Strategy: {plan.strategy.value}",
            f"Agents: {', '.join(step.agent_name for step in plan.steps)}",
            f"Estimated time: {plan.estimated_time:.1f}s"
        ]

        if plan.parallel_groups:
            summary_parts.append(f"Parallel groups: {plan.parallel_groups}")

        return " | ".join(summary_parts)


# 사용 예시
if __name__ == "__main__":
    import asyncio

    async def test_planning_agent():
        planner = PlanningAgent()

        # 의도 분석 테스트
        queries = [
            "전세금 5% 인상이 가능한가요?",
            "강남구 아파트 시세 알려주세요",
            "임대차계약서 작성해주세요",
            "이 계약서 검토해주세요"
        ]

        for query in queries:
            print(f"\n질문: {query}")
            intent = await planner.analyze_intent(query)
            print(f"의도: {intent.intent_type.value} (신뢰도: {intent.confidence:.2f})")
            print(f"추천 Agent: {intent.suggested_agents}")

            # 실행 계획 생성
            plan = await planner.create_execution_plan(intent)
            print(f"계획 요약: {planner.get_plan_summary(plan)}")

    asyncio.run(test_planning_agent())