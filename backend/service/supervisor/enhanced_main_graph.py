# backend/service/supervisor/enhanced_main_graph.py
"""
Enhanced Real Estate Supervisor with LLM Integration
LangGraph 0.6.7 기반 고도화된 Supervisor
OpenAI API 통합 및 구조화된 출력 지원
"""

from typing import Dict, Any, Type, Optional, Literal, List
from langgraph.graph import StateGraph, START, END
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from service.core.base_agent import BaseAgent
from service.core.states import SupervisorState, create_supervisor_initial_state
from service.core.context import AgentContext, create_agent_context
from service.core.config import Config
from service.utils.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


# ============ LLM Helper Class ============

class LLMHelper:
    """LLM 호출을 위한 헬퍼 클래스"""

    def __init__(self):
        """Initialize LLM Helper with config"""
        self.config = Config()
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize LLM client based on config"""
        provider = self.config.LLM_PROVIDER

        if provider == "openai" and self.config.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI library not installed")
                self._client = None
        elif provider == "azure_openai" and self.config.AZURE_OPENAI_KEY:
            try:
                from openai import AsyncAzureOpenAI
                self._client = AsyncAzureOpenAI(
                    api_key=self.config.AZURE_OPENAI_KEY,
                    azure_endpoint=self.config.AZURE_OPENAI_ENDPOINT,
                    api_version="2024-02-01"
                )
                logger.info("Azure OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI library not installed")
                self._client = None
        else:
            logger.warning(f"Using mock LLM (provider={provider}, has_key={bool(self.config.OPENAI_API_KEY)})")
            self._client = None

    async def complete(
        self,
        prompt: str,
        task_type: str = "general",
        system_prompt: Optional[str] = None,
        json_mode: bool = False
    ) -> str:
        """
        LLM 완성 요청

        Args:
            prompt: User prompt
            task_type: Task type for model selection (intent, planning, execution, evaluation)
            system_prompt: System prompt
            json_mode: Enable JSON response mode

        Returns:
            LLM response text
        """
        if self._client is None:
            # Fallback to mock response
            return self._mock_response(prompt, task_type)

        # Get model config for task type
        model_config = self.config.get_model_config(task_type)
        model_params = self.config.DEFAULT_MODEL_PARAMS.get(task_type, {})

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": model_config["model"],
                "messages": messages,
                "temperature": model_params.get("temperature", 0.7),
                "max_tokens": model_params.get("max_tokens", 1000),
            }

            # Enable JSON mode if requested
            if json_mode or model_params.get("json_mode", False):
                kwargs["response_format"] = {"type": "json_object"}

            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Fallback to mock
            return self._mock_response(prompt, task_type)

    def _mock_response(self, prompt: str, task_type: str) -> str:
        """Generate mock response based on task type"""
        if task_type == "intent":
            return json.dumps({
                "intent_type": "search",
                "confidence": 0.85,
                "entities": {
                    "region": "강남구",
                    "property_type": "아파트",
                    "deal_type": "매매",
                    "size_range": {"min": 30, "max": 35}
                },
                "requires_clarification": False
            })
        elif task_type == "planning":
            return json.dumps({
                "strategy": "sequential",
                "reasoning": "순차적 실행이 적합합니다",
                "agents": [
                    {
                        "name": "property_search",
                        "order": 1,
                        "parallel_group": 1,
                        "params": {"region": "강남구"},
                        "expected_output": "매물 목록"
                    }
                ]
            })
        elif task_type == "evaluation":
            return json.dumps({
                "quality_score": 0.85,
                "completeness": 0.90,
                "needs_retry": False,
                "summary": "분석 완료",
                "final_answer": "강남구 30평대 아파트 매물을 찾았습니다.",
                "confidence_level": "high"
            })
        else:
            return "Mock response"


# Singleton LLM Helper
_llm_helper = None

def get_llm_helper() -> LLMHelper:
    """Get singleton LLM helper instance"""
    global _llm_helper
    if _llm_helper is None:
        _llm_helper = LLMHelper()
    return _llm_helper


# ============ Enhanced Node Functions ============

async def analyze_intent_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Enhanced Step 1: LLM을 사용한 의도 분석
    """
    try:
        query = state.get("query", "")
        logger.info(f"[Step 1] Enhanced intent analysis starting: {query[:50]}...")

        # Get LLM helper
        llm = get_llm_helper()

        # Create prompt
        system_prompt = """당신은 부동산 챗봇의 의도 분석 전문가입니다.
사용자의 질문을 정확히 분석하여 의도와 핵심 정보를 추출해주세요.
응답은 반드시 유효한 JSON 형식이어야 합니다."""

        user_prompt = f"""사용자 질문: {query}

다음 JSON 형식으로 응답하세요:
{{
    "intent_type": "search|analysis|comparison|recommendation|general 중 하나",
    "confidence": 0.0-1.0 사이의 신뢰도,
    "entities": {{
        "region": "지역명 (없으면 null)",
        "property_type": "아파트|오피스텔|빌라|상가 (없으면 null)",
        "deal_type": "매매|전세|월세 (없으면 null)",
        "price_range": {{"min": 숫자, "max": 숫자}} (없으면 null),
        "size_range": {{"min": 숫자, "max": 숫자}} (평수, 없으면 null),
        "keywords": ["추출된", "키워드들"]
    }},
    "requires_clarification": true 또는 false,
    "clarification_questions": ["필요한 경우 명확화 질문들"]
}}"""

        # Call LLM
        response = await llm.complete(
            prompt=user_prompt,
            task_type="intent",
            system_prompt=system_prompt,
            json_mode=True
        )

        # Parse response
        try:
            intent = json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response[:100]}...")
            # Fallback to basic parsing
            intent = {
                "intent_type": "search",
                "confidence": 0.5,
                "entities": {
                    "region": None,
                    "property_type": "아파트",
                    "deal_type": "매매"
                },
                "requires_clarification": True
            }

        logger.info(f"[Step 1] Intent analyzed: type={intent.get('intent_type')}, confidence={intent.get('confidence', 0):.2f}")

        return {
            "intent": intent,
            "intent_confidence": intent.get("confidence", 0.5),
            "status": "processing",
            "execution_step": "planning"
        }

    except Exception as e:
        logger.error(f"[Step 1] Intent analysis failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Intent analysis failed: {str(e)}"]
        }


async def build_plan_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Enhanced Step 2: LLM을 사용한 계획 수립
    """
    try:
        intent = state.get("intent", {})
        intent_type = intent.get("intent_type", "search")
        confidence = state.get("intent_confidence", 0.5)

        logger.info(f"[Step 2] Building plan: intent_type={intent_type}, confidence={confidence:.2f}")

        # Get LLM helper
        llm = get_llm_helper()

        # Create prompt
        system_prompt = """당신은 부동산 분석 워크플로우 설계 전문가입니다.
의도 분석 결과를 바탕으로 최적의 agent 실행 계획을 수립해주세요.
병렬 실행이 가능한 경우 parallel_group을 동일하게 설정하세요."""

        user_prompt = f"""의도 분석 결과:
{json.dumps(intent, ensure_ascii=False, indent=2)}

사용 가능한 agents:
- property_search: 매물 검색 및 조회
- market_analysis: 시장 분석 및 트렌드
- region_comparison: 지역 간 비교
- investment_advisor: 투자 조언 및 추천

JSON 형식으로 실행 계획을 작성하세요:
{{
    "strategy": "sequential|parallel|hybrid 중 하나",
    "reasoning": "계획 수립 이유",
    "agents": [
        {{
            "name": "agent 이름",
            "order": 실행 순서,
            "parallel_group": 병렬 그룹 번호,
            "params": {{agent에 전달할 파라미터}},
            "depends_on": ["의존 agent들"],
            "expected_output": "예상 출력"
        }}
    ],
    "estimated_time": 예상 소요 시간(초),
    "fallback_plan": {{
        "trigger": "실패 조건",
        "agents": ["대체 agent들"]
    }}
}}"""

        # Call LLM
        response = await llm.complete(
            prompt=user_prompt,
            task_type="planning",
            system_prompt=system_prompt,
            json_mode=True
        )

        # Parse response
        try:
            plan = json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse plan: {response[:100]}...")
            # Fallback to simple plan
            plan = {
                "strategy": "sequential",
                "reasoning": "기본 순차 실행",
                "agents": [
                    {
                        "name": "property_search",
                        "order": 1,
                        "parallel_group": 1,
                        "params": intent.get("entities", {})
                    }
                ]
            }

        # Validate agents exist
        available_agents = AgentRegistry.list_agents()
        plan["agents"] = [
            agent for agent in plan.get("agents", [])
            if agent["name"] in available_agents or Config.LLM_SETTINGS.get("fallback_to_mock", True)
        ]

        logger.info(f"[Step 2] Plan created: strategy={plan.get('strategy')}, agents={len(plan.get('agents', []))}")

        return {
            "execution_plan": plan,
            "agent_selection": [a["name"] for a in plan.get("agents", [])],
            "status": "processing",
            "execution_step": "executing"
        }

    except Exception as e:
        logger.error(f"[Step 2] Planning failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Planning failed: {str(e)}"]
        }


async def execute_plan_parallel_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Enhanced Step 3: 병렬 실행을 지원하는 계획 실행
    """
    try:
        execution_plan = state.get("execution_plan", {})
        agents = execution_plan.get("agents", [])
        strategy = execution_plan.get("strategy", "sequential")

        logger.info(f"[Step 3] Executing plan: strategy={strategy}, agents={len(agents)}")

        # Prepare context
        context = {
            "chat_user_ref": state.get("chat_user_ref", "system"),
            "chat_session_id": state.get("chat_session_id", "default"),
            "chat_thread_id": state.get("chat_thread_id"),
            "original_query": state.get("query", ""),
            "llm_provider": Config.LLM_PROVIDER,
            "language": "ko"
        }

        agent_results = {}
        failed_agents = []

        if strategy == "parallel" or strategy == "hybrid":
            # Group agents by parallel_group
            groups = {}
            for agent_config in agents:
                group = agent_config.get("parallel_group", agent_config["order"])
                if group not in groups:
                    groups[group] = []
                groups[group].append(agent_config)

            # Execute groups in order
            for group_num in sorted(groups.keys()):
                group_agents = groups[group_num]
                logger.info(f"[Step 3] Executing parallel group {group_num}: {[a['name'] for a in group_agents]}")

                # Execute agents in parallel
                tasks = []
                for agent_config in group_agents:
                    task = execute_single_agent(agent_config, context, agent_results)
                    tasks.append(task)

                # Wait for all tasks in group
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for agent_config, result in zip(group_agents, results):
                    agent_name = agent_config["name"]
                    if isinstance(result, Exception):
                        logger.error(f"Agent {agent_name} failed: {result}")
                        agent_results[agent_name] = {"status": "error", "error": str(result)}
                        failed_agents.append(agent_name)
                    else:
                        agent_results[agent_name] = result
                        if result.get("status") == "error":
                            failed_agents.append(agent_name)
        else:
            # Sequential execution
            for agent_config in agents:
                agent_name = agent_config["name"]
                result = await execute_single_agent(agent_config, context, agent_results)
                agent_results[agent_name] = result
                if result.get("status") == "error":
                    failed_agents.append(agent_name)

        logger.info(f"[Step 3] Execution complete: success={len(agent_results)-len(failed_agents)}, failed={len(failed_agents)}")

        # Update retry count if needed
        retry_count = state.get("retry_count", 0)
        if failed_agents and retry_count > 0:
            retry_count += 1

        return {
            "agent_results": agent_results,
            "failed_agents": failed_agents,
            "agent_metrics": {
                name: {"execution_time": 0.5, "success": name not in failed_agents}
                for name in agent_results
            },
            "retry_count": retry_count,
            "status": "processing",
            "execution_step": "evaluating"
        }

    except Exception as e:
        logger.error(f"[Step 3] Execution failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Execution failed: {str(e)}"]
        }


async def execute_single_agent(
    agent_config: Dict[str, Any],
    context: Dict[str, Any],
    previous_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a single agent"""
    agent_name = agent_config["name"]
    params = agent_config.get("params", {})

    try:
        logger.info(f"Executing agent: {agent_name}")

        # Get agent from registry
        agent = AgentRegistry.get_agent(agent_name)

        # Add context and previous results to params
        execution_params = {
            **params,
            "context": context,
            "previous_results": previous_results
        }

        # Execute agent
        result = await agent.execute(execution_params)

        logger.info(f"Agent {agent_name} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_name} execution failed: {e}")
        return {
            "status": "error",
            "agent": agent_name,
            "error": str(e)
        }


async def evaluate_results_node(state: Dict[str, Any], runtime: Optional[Any] = None) -> Dict[str, Any]:
    """
    Enhanced Step 4: LLM을 사용한 결과 평가
    """
    try:
        agent_results = state.get("agent_results", {})
        failed_agents = state.get("failed_agents", [])
        query = state.get("query", "")
        intent = state.get("intent", {})

        logger.info(f"[Step 4] Evaluating results: {len(agent_results)} results")

        # Get LLM helper
        llm = get_llm_helper()

        # Prepare results summary
        results_summary = {
            agent_name: {
                "status": result.get("status"),
                "data_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else 0,
                "has_insights": bool(result.get("insights")),
                "has_recommendations": bool(result.get("recommendations"))
            }
            for agent_name, result in agent_results.items()
        }

        # Create evaluation prompt
        system_prompt = """당신은 부동산 분석 결과 평가 전문가입니다.
실행 결과를 종합하여 품질을 평가하고 사용자 친화적인 답변을 생성해주세요."""

        user_prompt = f"""원래 질문: {query}
의도: {json.dumps(intent, ensure_ascii=False)}
실행 결과 요약: {json.dumps(results_summary, ensure_ascii=False)}
실패한 agents: {failed_agents}

JSON 형식으로 평가 결과를 작성하세요:
{{
    "quality_score": 0.0-1.0,
    "completeness": 0.0-1.0,
    "needs_retry": true 또는 false,
    "retry_agents": ["재시도 필요 agent들"],
    "missing_information": ["누락된 정보"],
    "summary": "결과 요약",
    "final_answer": "사용자에게 전달할 답변 (자연스러운 한국어)",
    "confidence_level": "high|medium|low",
    "recommendations": ["추가 추천사항"]
}}"""

        # Call LLM
        response = await llm.complete(
            prompt=user_prompt,
            task_type="evaluation",
            system_prompt=system_prompt,
            json_mode=True
        )

        # Parse response
        try:
            evaluation = json.loads(response)
        except json.JSONDecodeError:
            # Fallback evaluation
            evaluation = {
                "quality_score": 0.7,
                "completeness": 0.8,
                "needs_retry": len(failed_agents) > 0,
                "retry_agents": failed_agents,
                "summary": "분석 완료",
                "final_answer": _generate_basic_answer(query, agent_results),
                "confidence_level": "medium"
            }

        # Check retry logic
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)
        needs_retry = evaluation.get("needs_retry", False) and retry_count < max_retries

        logger.info(f"[Step 4] Evaluation complete: quality={evaluation.get('quality_score', 0):.2f}, retry={needs_retry}")

        # Create final output
        final_output = {
            "answer": evaluation.get("final_answer", ""),
            "data": agent_results,
            "metadata": {
                "quality_score": evaluation.get("quality_score", 0),
                "completeness": evaluation.get("completeness", 0),
                "confidence_level": evaluation.get("confidence_level", "low"),
                "agents_used": list(agent_results.keys()),
                "execution_time": datetime.now().isoformat(),
                "retry_count": retry_count
            },
            "recommendations": evaluation.get("recommendations", [])
        }

        return {
            "evaluation": evaluation,
            "quality_score": evaluation.get("quality_score", 0),
            "final_output": final_output,
            "retry_needed": needs_retry,
            "retry_agents": evaluation.get("retry_agents", []) if needs_retry else [],
            "status": "completed" if not needs_retry else "processing",
            "execution_step": "finished" if not needs_retry else "retrying"
        }

    except Exception as e:
        logger.error(f"[Step 4] Evaluation failed: {e}")
        return {
            "status": "failed",
            "errors": [f"Evaluation failed: {str(e)}"]
        }


def _generate_basic_answer(query: str, agent_results: Dict[str, Any]) -> str:
    """Generate basic answer without LLM"""
    parts = [f"'{query}'에 대한 분석 결과입니다.\n"]

    for agent_name, result in agent_results.items():
        if result.get("status") == "success":
            if "data" in result and result["data"]:
                parts.append(f"• {agent_name}: {len(result['data'])}개 결과")
            if "insights" in result:
                parts.append(f"• 분석: {result['insights'][0] if result['insights'] else '완료'}")

    if not parts[1:]:
        return "죄송합니다. 요청하신 정보를 찾을 수 없습니다."

    return "\n".join(parts)


# ============ Enhanced Supervisor Class ============

class EnhancedRealEstateSupervisor(BaseAgent):
    """
    고도화된 부동산 챗봇 Supervisor
    - LLM 통합 (OpenAI/Azure/Mock)
    - 병렬 실행 지원
    - 구조화된 출력
    """

    def __init__(
        self,
        agent_name: str = "enhanced_supervisor",
        checkpoint_dir: Optional[str] = None,
        max_retries: int = 2
    ):
        """Initialize enhanced supervisor"""
        self.max_retries = max_retries
        super().__init__(agent_name, checkpoint_dir)

        # Initialize LLM helper
        self.llm_helper = get_llm_helper()

        logger.info(f"EnhancedRealEstateSupervisor initialized (provider={Config.LLM_PROVIDER})")

    def _get_state_schema(self) -> Type:
        """State schema"""
        return SupervisorState

    def _build_graph(self) -> None:
        """
        Build enhanced workflow graph
        """
        self.workflow = StateGraph(
            state_schema=SupervisorState,
            context_schema=AgentContext
        )

        # Add nodes
        self.workflow.add_node("analyze_intent", analyze_intent_node)
        self.workflow.add_node("build_plan", build_plan_node)
        self.workflow.add_node("execute_plan", execute_plan_parallel_node)
        self.workflow.add_node("evaluate_results", evaluate_results_node)

        # Add edges
        self.workflow.add_edge(START, "analyze_intent")
        self.workflow.add_edge("analyze_intent", "build_plan")
        self.workflow.add_edge("build_plan", "execute_plan")
        self.workflow.add_edge("execute_plan", "evaluate_results")

        # Conditional edges
        self.workflow.add_conditional_edges(
            "evaluate_results",
            self._should_retry,
            {
                "retry": "execute_plan",
                "end": END
            }
        )

        logger.info("Enhanced workflow graph built")

    def _should_retry(self, state: Dict[str, Any]) -> Literal["retry", "end"]:
        """Determine if retry is needed"""
        needs_retry = state.get("retry_needed", False)
        retry_count = state.get("retry_count", 0)

        if needs_retry and retry_count < self.max_retries:
            logger.info(f"Retrying (attempt {retry_count + 1}/{self.max_retries})")
            return "retry"
        return "end"

    async def _validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input"""
        if "query" not in input_data:
            logger.error("Missing 'query' field")
            return False

        query = input_data["query"]
        if not isinstance(query, str) or len(query.strip()) == 0:
            logger.error("Invalid query")
            return False

        return True

    def _create_initial_state(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial state with LLM config"""
        state = create_supervisor_initial_state(
            chat_session_id=input_data.get("chat_session_id", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            query=input_data.get("query", ""),
            max_retries=self.max_retries
        )

        # Add LLM configuration to state
        state["llm_provider"] = Config.LLM_PROVIDER
        state["llm_model"] = Config.DEFAULT_MODELS.get("general")

        return state

    async def ask(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """
        Simple interface for asking questions

        Args:
            query: User question
            session_id: Optional session ID

        Returns:
            Final response with answer and metadata
        """
        input_data = {
            "query": query,
            "chat_session_id": session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }

        result = await self.execute(input_data)

        if result["status"] == "success":
            return result["data"].get("final_output", {})
        else:
            return {
                "error": result.get("error", "Unknown error"),
                "status": "failed"
            }


# ============ Testing ============

async def test_enhanced_supervisor():
    """Test enhanced supervisor"""

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    supervisor = EnhancedRealEstateSupervisor()

    test_queries = [
        "강남역 근처 30평대 아파트 매매 시세 알려줘",
        "서초구와 강남구 아파트 가격 비교 분석해줘",
        "투자하기 좋은 지역 추천해줘",
        "송파구 잠실동 40평 아파트 전세 시세는?"
    ]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"📝 질문: {query}")
        print(f"{'='*70}")

        result = await supervisor.ask(query)

        if "error" in result:
            print(f"❌ 오류: {result['error']}")
        else:
            print(f"\n✅ 답변:")
            print(result.get('answer', 'No answer'))

            if "metadata" in result:
                meta = result["metadata"]
                print(f"\n📊 메타데이터:")
                print(f"  • 품질 점수: {meta.get('quality_score', 0):.2f}")
                print(f"  • 완성도: {meta.get('completeness', 0):.2f}")
                print(f"  • 신뢰도: {meta.get('confidence_level', 'unknown')}")
                print(f"  • 사용된 agents: {', '.join(meta.get('agents_used', []))}")
                print(f"  • 재시도 횟수: {meta.get('retry_count', 0)}")

            if "recommendations" in result and result["recommendations"]:
                print(f"\n💡 추천사항:")
                for rec in result["recommendations"]:
                    print(f"  • {rec}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_supervisor())