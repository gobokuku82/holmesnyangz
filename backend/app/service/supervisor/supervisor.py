"""
Refactored Supervisor with Dynamic Agent Execution
Agent Registry를 활용한 개선된 Supervisor
기존 기능을 유지하면서 확장성을 높인 버전
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
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
from core.agent_registry import AgentRegistry
from core.agent_adapter import AgentAdapter, initialize_agent_system

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
        model_map = {
            "intent": self.context.models.get("intent", "gpt-4o-mini"),
            "planning": self.context.models.get("planning", "gpt-4o-mini"),
            "response": self.context.models.get("response", "gpt-4o-mini"),
            "analysis": self.context.models.get("analysis", "gpt-4o-mini"),
            "search": self.context.models.get("search", "gpt-4o-mini"),
            "default": self.context.models.get("default", "gpt-4o-mini")
        }
        return model_map.get(purpose, model_map["default"])

    async def analyze_intent_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Analyze user intent using LLM

        Args:
            query: User query to analyze

        Returns:
            Intent analysis results
        """
        if self._connection_error:
            logger.error(f"LLM connection error: {self._connection_error}")
            return {
                "intent_type": "error",
                "intent": "연결 오류",
                "confidence": 0.0,
                "details": self._connection_error,
                "reasoning": "LLM 연결 실패로 인한 기본 처리",
                "fallback": True
            }

        if not self.client:
            logger.warning("No LLM client available, using fallback")
            return self._fallback_intent_analysis(query)

        try:
            # System prompt for intent analysis
            system_prompt = """당신은 부동산 관련 질문을 분석하는 전문가입니다.

사용자의 질문을 분석하여 다음 카테고리 중 하나로 분류하세요:
- 법률상담: 임대차, 전세, 매매 관련 법률 질문
- 시세조회: 부동산 가격, 시세 관련 질문
- 대출상담: 대출 조건, 금리 관련 질문
- 계약서작성: 계약서 생성 요청
- 계약서검토: 기존 계약서 검토 요청
- 종합분석: 여러 측면의 분석이 필요한 복합 질문
- unclear: 의도가 명확하지 않은 경우
- irrelevant: 부동산과 무관한 질문

JSON 형식으로 응답하세요:
{
    "intent": "카테고리명",
    "confidence": 0.0-1.0,
    "keywords": ["주요", "키워드"],
    "reasoning": "분류 이유"
}"""

            response = self.client.chat.completions.create(
                model=self.get_model("intent"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"다음 질문을 분석하세요: {query}"}
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return {
                "intent_type": result.get("intent", "unclear"),
                "intent": result.get("intent", "unclear"),
                "confidence": result.get("confidence", 0.5),
                "keywords": result.get("keywords", []),
                "reasoning": result.get("reasoning", ""),
                "llm_used": True
            }

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            return self._fallback_intent_analysis(query)

    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback intent analysis using keywords"""
        intent_keywords = {
            "법률상담": ["법", "전세", "임대", "보증금", "계약", "권리", "의무"],
            "시세조회": ["시세", "가격", "매매가", "전세가", "시장", "동향"],
            "대출상담": ["대출", "금리", "한도", "조건", "상환"],
            "계약서작성": ["작성", "만들", "생성"],
            "계약서검토": ["검토", "확인", "점검", "리뷰"],
            "종합분석": ["분석", "평가", "비교"]
        }

        detected_intent = "unclear"
        max_score = 0
        found_keywords = []

        for intent, keywords in intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in query:
                    score += 1
                    found_keywords.append(keyword)

            if score > max_score:
                max_score = score
                detected_intent = intent if score > 0 else "unclear"

        confidence = min(max_score * 0.3, 1.0)  # Simple confidence calculation

        return {
            "intent_type": detected_intent,
            "intent": detected_intent,
            "confidence": confidence,
            "keywords": found_keywords,
            "reasoning": "Keyword-based fallback analysis",
            "fallback": True
        }

    async def create_execution_plan(self, intent: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            intent: Intent analysis results
            query: Original query

        Returns:
            Execution plan with selected agents
        """
        intent_type = intent.get("intent_type", "unclear")

        if intent_type == "error":
            return {
                "error": True,
                "message": "LLM 연결 오류로 계획을 생성할 수 없습니다.",
                "details": intent.get("details", ""),
                "agents": []
            }

        # Use Registry to get available agents
        available_agents = AgentRegistry.list_agents(enabled_only=True)
        logger.info(f"Available agents from registry: {available_agents}")

        # Get agents for intent type
        selected_agents = AgentAdapter.get_agents_for_intent(intent_type)

        # Filter only enabled agents
        selected_agents = [
            agent for agent in selected_agents
            if agent in available_agents
        ]

        if not selected_agents:
            # Default to search agent if available
            if "search_agent" in available_agents:
                selected_agents = ["search_agent"]
            else:
                logger.warning("No agents available for execution")
                return {
                    "error": True,
                    "message": "실행 가능한 에이전트가 없습니다.",
                    "agents": []
                }

        # Determine execution strategy
        strategy = "sequential"  # Default strategy
        if len(selected_agents) > 1 and intent_type in ["종합분석", "리스크분석"]:
            strategy = "parallel"

        plan = {
            "agents": selected_agents,
            "strategy": strategy,
            "intent": intent_type,
            "keywords": intent.get("keywords", []),
            "confidence": intent.get("confidence", 0.5)
        }

        logger.info(f"Execution plan created: {plan}")
        return plan


class RealEstateSupervisor:
    """
    Main Supervisor for Real Estate Chatbot
    Refactored with dynamic agent execution
    """

    def __init__(self, llm_context: LLMContext = None):
        self.llm_context = llm_context or create_default_llm_context()
        self.llm_manager = LLMManager(self.llm_context)

        # Initialize agent system
        initialize_agent_system(auto_register=True)

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
        logger.info("[NODE] analyze_intent_node - Starting intent analysis")

        query = state.get("query", "")
        intent_result = await self.llm_manager.analyze_intent_with_llm(query)

        state.update({
            "current_phase": "intent_analysis",
            "intent": intent_result.get("intent", "unclear"),
            "intent_type": intent_result.get("intent_type", "unclear"),
            "intent_confidence": intent_result.get("confidence", 0.0),
            "collection_keywords": intent_result.get("keywords", [])
        })

        logger.info(f"[NODE] Intent analyzed: {state['intent_type']} (confidence: {state['intent_confidence']})")
        return state

    async def recheck_intent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recheck unclear intent with user clarification

        Args:
            state: Current state

        Returns:
            Updated state
        """
        logger.info("[NODE] recheck_intent_node - Rechecking unclear intent")

        # In production, this would interact with user for clarification
        # For now, mark as still unclear
        state["still_unclear"] = True
        state["current_phase"] = "clarification_needed"

        return state

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
        elif "연결 실패" in error_details:
            error_type = "connection_failed"
            message = "OpenAI 서비스에 연결할 수 없습니다."
            suggestion = "네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
        else:
            error_type = "general_error"
            message = "처리 중 오류가 발생했습니다."
            suggestion = "문제가 지속되면 관리자에게 문의해주세요."

        state["final_response"] = {
            "type": "error",
            "error_type": error_type,
            "message": message,
            "suggestion": suggestion,
            "details": error_details
        }

        state["response_type"] = "error"
        state["status"] = "completed"

        logger.debug(f"[NODE] error_handler_node - Error handled: {error_type}")
        return state

    async def guidance_message_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide guidance for unclear or irrelevant queries

        Args:
            state: Current state

        Returns:
            Updated state with guidance message
        """
        logger.info("Providing guidance message")

        intent_type = state.get("intent_type", "unclear")

        if intent_type == "irrelevant":
            message = "죄송하지만 부동산 관련 질문만 답변드릴 수 있습니다."
            examples = [
                "전세 보증금 인상률 제한은?",
                "강남구 아파트 시세는?",
                "주택 담보 대출 조건은?"
            ]
        else:  # unclear
            message = "질문을 더 구체적으로 설명해주시겠습니까?"
            examples = [
                "특정 지역의 시세를 알고 싶으시면: '강남구 아파트 시세'",
                "법률 상담이 필요하시면: '전세 계약 갱신 거부 가능한가요?'",
                "대출 정보가 필요하시면: 'LTV 한도는 얼마인가요?'"
            ]

        state["final_response"] = {
            "type": "guidance",
            "message": message,
            "examples": examples,
            "original_query": state.get("query", "")
        }

        state["response_type"] = "guidance"
        state["status"] = "completed"

        return state

    async def create_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create execution plan based on intent

        Args:
            state: Current state

        Returns:
            Updated state with execution plan
        """
        logger.info("[NODE] create_plan_node - Creating execution plan")

        intent_data = {
            "intent_type": state.get("intent_type", "unclear"),
            "intent": state.get("intent", "unclear"),
            "confidence": state.get("intent_confidence", 0.0),
            "keywords": state.get("collection_keywords", [])
        }

        plan = await self.llm_manager.create_execution_plan(
            intent_data,
            state.get("query", "")
        )

        if plan.get("error"):
            # Handle planning error
            state["intent_type"] = "error"
            state["intent"] = {"details": plan.get("message", "")}
            return state

        state["execution_plan"] = plan
        state["selected_agents"] = plan.get("agents", [])
        state["current_phase"] = "planning_complete"

        # Create TODOs for each agent
        todos = state.get("todos", [])
        todo_counter = state.get("todo_counter", 0)

        for agent_name in state["selected_agents"]:
            todo_counter += 1
            todo = create_todo_dict(
                id=f"agent_{todo_counter}",
                task=f"Execute {agent_name}",
                agent=agent_name,
                level="supervisor"
            )
            todos.append(todo)

        state["todos"] = todos
        state["todo_counter"] = todo_counter

        logger.info(f"[NODE] Execution plan created with {len(state['selected_agents'])} agents")
        return state

    async def execute_agents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agents dynamically using Registry

        Args:
            state: Current state

        Returns:
            Updated state with agent results
        """
        logger.info("[NODE] execute_agents_node - Starting dynamic agent execution")

        selected_agents = state.get("selected_agents", [])
        execution_plan = state.get("execution_plan", {})
        strategy = execution_plan.get("strategy", "sequential")

        logger.info(f"Executing {len(selected_agents)} agents with {strategy} strategy")

        agent_results = {}
        todos = state.get("todos", [])

        # Prepare base input for agents
        base_input = {
            "query": state["query"],
            "original_query": state.get("query"),
            "chat_session_id": state.get("chat_session_id", ""),
            "shared_context": state.get("shared_context", {}),
            "todos": todos,
            "todo_counter": state.get("todo_counter", 0),
            "collection_keywords": state.get("collection_keywords", [])
        }

        # Execute agents based on strategy
        if strategy == "parallel" and len(selected_agents) > 1:
            # Parallel execution
            tasks = []
            for agent_name in selected_agents:
                input_data = self._prepare_agent_input(agent_name, base_input, agent_results)
                task = AgentAdapter.execute_agent_dynamic(
                    agent_name,
                    input_data,
                    self.llm_context
                )
                tasks.append((agent_name, task))

            # Wait for all tasks
            for agent_name, task in tasks:
                try:
                    result = await task
                    agent_results[agent_name] = result

                    # Update TODO
                    for i, todo in enumerate(todos):
                        if todo.get("agent") == agent_name:
                            status = "completed" if result.get("status") in ["completed", "success"] else "failed"
                            todos[i] = update_todo_status(todos[i], status)
                            break

                    logger.info(f"Agent '{agent_name}' completed: {result.get('status')}")

                except Exception as e:
                    logger.error(f"Agent '{agent_name}' failed: {e}")
                    agent_results[agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }

        else:
            # Sequential execution
            for agent_name in selected_agents:
                try:
                    input_data = self._prepare_agent_input(agent_name, base_input, agent_results)

                    # Execute agent
                    result = await AgentAdapter.execute_agent_dynamic(
                        agent_name,
                        input_data,
                        self.llm_context
                    )

                    agent_results[agent_name] = result

                    # Update TODO
                    for i, todo in enumerate(todos):
                        if todo.get("agent") == agent_name:
                            status = "completed" if result.get("status") in ["completed", "success"] else "failed"
                            todos[i] = update_todo_status(todos[i], status)
                            break

                    # Merge any TODO updates from agent
                    if "todos" in result:
                        from core.todo_types import merge_todos
                        todos = merge_todos(todos, result["todos"])

                    logger.info(f"Agent '{agent_name}' completed: {result.get('status')}")

                except Exception as e:
                    logger.error(f"Failed to execute agent '{agent_name}': {e}")
                    agent_results[agent_name] = {
                        "status": "error",
                        "error": str(e)
                    }

        state["agent_results"] = agent_results
        state["todos"] = todos
        state["current_phase"] = "execution_complete"

        # Calculate execution statistics
        success_count = sum(1 for r in agent_results.values()
                          if r.get("status") in ["completed", "success"])

        state["execution_stats"] = {
            "total_agents": len(selected_agents),
            "successful": success_count,
            "failed": len(selected_agents) - success_count
        }

        logger.info(f"[NODE] Agent execution completed: {success_count}/{len(selected_agents)} successful")
        return state

    def _prepare_agent_input(
        self,
        agent_name: str,
        base_input: Dict[str, Any],
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare input data for specific agent

        Args:
            agent_name: Name of the agent
            base_input: Base input data
            agent_results: Results from previously executed agents

        Returns:
            Prepared input data
        """
        input_data = base_input.copy()

        # Add agent-specific inputs
        if agent_name == "analysis_agent":
            # Pass search results to analysis agent
            search_data = agent_results.get("search_agent", {}).get("collected_data", {})
            input_data["input_data"] = search_data
            input_data["analysis_type"] = "comprehensive"

        elif agent_name == "document_agent":
            input_data["document_type"] = "lease_contract"
            input_data["document_params"] = {}

        elif agent_name == "review_agent":
            # Pass document to review if available
            doc_data = agent_results.get("document_agent", {}).get("data", {})
            input_data["document_content"] = doc_data.get("document", "")
            input_data["review_type"] = "comprehensive"

        return input_data

    async def generate_response_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final response from agent results

        Args:
            state: Current state

        Returns:
            Updated state with final response
        """
        logger.info("[NODE] generate_response_node - Generating final response")

        agent_results = state.get("agent_results", {})
        query = state.get("query", "")

        # Collect all successful agent data
        all_data = {}
        for agent_name, result in agent_results.items():
            if result.get("status") in ["completed", "success"]:
                data = result.get("collected_data") or result.get("data", {})
                if data:
                    all_data[agent_name] = data

        # Generate natural language response using LLM if data is available
        if all_data and not self.llm_manager._connection_error and self.llm_manager.client:
            try:
                logger.info("[RESPONSE] Generating LLM-based answer")

                # Prepare context for LLM
                context = self._prepare_context_for_llm(all_data)

                # Create LLM prompt
                system_prompt = """당신은 부동산 전문 상담사입니다.
수집된 데이터를 기반으로 사용자 질문에 대한 명확하고 구체적인 답변을 제공하세요.

답변 원칙:
1. 질문에 직접적으로 답하세요
2. 구체적인 수치나 법률 조항을 인용하세요
3. 실용적인 조언을 포함하세요
4. 한국어로 자연스럽게 답변하세요
5. 답변은 간결하고 명확하게 작성하세요"""

                user_prompt = f"""사용자 질문: {query}

수집된 정보:
{json.dumps(context, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 사용자 질문에 대한 답변을 작성하세요."""

                # Call LLM
                response = self.llm_manager.client.chat.completions.create(
                    model=self.llm_manager.get_model("response"),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )

                final_answer = response.choices[0].message.content
                logger.info("[RESPONSE] LLM answer generated successfully")

                # Extract sources
                sources = self._extract_sources(all_data)

                # Create structured response
                final_response = {
                    "type": "answer",
                    "answer": final_answer,  # LLM generated natural language answer
                    "sources": sources,       # Source information
                    "data": all_data         # Original data for reference
                }

            except Exception as e:
                logger.error(f"LLM response generation failed: {e}")
                # Fallback to data-only response
                summary = f"{len(all_data)}개의 에이전트에서 데이터 수집 완료"
                final_response = {
                    "type": "processed",
                    "data": all_data,
                    "summary": summary + " (답변 생성 실패)"
                }
        else:
            # No data or connection error - fallback to simple summary
            summary = "데이터 수집 완료"
            if all_data:
                summary = f"{len(all_data)}개의 에이전트에서 데이터 수집 완료"

            logger.debug(f"[RESPONSE] all_data final: {list(all_data.keys())}")
            logger.debug(f"[RESPONSE] all_data content sample: {str(all_data)[:200]}")

            final_response = {
                "type": "processed",
                "data": all_data,
                "summary": summary
            }

        result = {
            "final_response": final_response,
            "response_type": final_response.get("type", "processed")
        }
        logger.debug(f"[NODE] generate_response_node - Completed with response type: {final_response.get('type')}, data_keys: {list(final_response.get('data', {}).keys())}")
        return result

    def _prepare_context_for_llm(self, all_data: Dict) -> Dict:
        """
        Prepare structured context from all agent data for LLM

        Args:
            all_data: Combined data from all agents

        Returns:
            Structured context dict for LLM consumption
        """
        context = {}

        # Extract from SearchAgent results
        if "search_agent" in all_data:
            search_data = all_data["search_agent"]

            # Legal search results
            if "legal_search" in search_data and search_data["legal_search"]:
                laws = search_data["legal_search"][:5]  # Top 5 laws
                context["legal_info"] = [
                    {
                        "title": law.get("law_name", ""),
                        "article": law.get("article_number", ""),
                        "content": law.get("content", "")[:500]  # First 500 chars
                    }
                    for law in laws
                ]

            # Real estate data
            if "real_estate_search" in search_data:
                context["real_estate_info"] = search_data["real_estate_search"]

            # Loan data
            if "loan_search" in search_data:
                context["loan_info"] = search_data["loan_search"]

        # Extract from AnalysisAgent results
        if "analysis_agent" in all_data:
            analysis_data = all_data["analysis_agent"]
            if "report" in analysis_data:
                context["analysis"] = {
                    "summary": analysis_data["report"].get("summary", ""),
                    "insights": analysis_data["report"].get("insights", []),
                    "recommendations": analysis_data["report"].get("recommendations", [])
                }

        # Extract from DocumentAgent results
        if "document_agent" in all_data:
            doc_data = all_data["document_agent"]
            context["generated_document"] = {
                "type": doc_data.get("document_type", ""),
                "status": doc_data.get("status", "")
            }

        # Extract from ReviewAgent results
        if "review_agent" in all_data:
            review_data = all_data["review_agent"]
            context["review_results"] = {
                "risk_factors": review_data.get("risk_factors", []),
                "recommendations": review_data.get("recommendations", [])
            }

        return context

    def _extract_sources(self, all_data: Dict) -> List[str]:
        """
        Extract source citations from collected data

        Args:
            all_data: Combined data from all agents

        Returns:
            List of source citations
        """
        sources = []

        # Extract legal sources
        if "search_agent" in all_data:
            search_data = all_data["search_agent"]
            if "legal_search" in search_data and search_data["legal_search"]:
                for law in search_data["legal_search"][:5]:
                    law_name = law.get("law_name", "")
                    article = law.get("article_number", "")
                    if law_name and article:
                        sources.append(f"{law_name} {article}")

        # Extract market data sources
        if "analysis_agent" in all_data:
            analysis_data = all_data["analysis_agent"]
            if "data_source" in analysis_data:
                sources.append(f"시장 데이터: {analysis_data['data_source']}")

        return sources

    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        llm_context: Optional[LLMContext] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user queries

        Args:
            query: User query
            session_id: Optional session ID for tracking
            llm_context: Optional LLM context override

        Returns:
            Dict containing the final state with response
        """
        logger.info(f"Starting query processing: {query[:100]}...")

        # Use override context if provided
        if llm_context:
            self.llm_context = llm_context
            self.llm_manager = LLMManager(llm_context)

        # Initialize state
        initial_state = {
            "query": query,
            "chat_session_id": session_id or "default_session",
            "shared_context": {},
            "messages": [],
            "todos": [],
            "todo_counter": 0
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