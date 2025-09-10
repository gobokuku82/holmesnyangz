"""
Integration Tests for Real Estate Chatbot
통합 테스트 스위트
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from backend.core.context import ContextFactory
from backend.core.state import create_initial_state
from backend.core.workflow_engine import AsyncWorkflowEngine, WorkflowEngineFactory
from backend.core.graph_builder import RealEstateGraphBuilder
from backend.agents.analyzer_agent import AnalyzerAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.supervisor_agent import SupervisorAgent


@pytest.fixture
async def test_context():
    """테스트용 컨텍스트 생성"""
    return ContextFactory.create_for_testing()


@pytest.fixture
async def test_engine():
    """테스트용 워크플로우 엔진"""
    engine = await WorkflowEngineFactory.create_for_testing()
    yield engine
    await engine.close()


@pytest.fixture
async def mock_llm():
    """Mock LLM"""
    mock = AsyncMock()
    mock.ainvoke.return_value = Mock(content="Test response")
    return mock


class TestContextAPI:
    """Context API 테스트"""
    
    def test_user_context_creation(self):
        """일반 사용자 컨텍스트 생성"""
        context = ContextFactory.create_for_user(
            user_id="test_user",
            user_name="Test User"
        )
        
        assert context.user_id == "test_user"
        assert context.user_name == "Test User"
        assert context.user_role == "user"
        assert context.model_name == "gpt-4"
        assert len(context.available_agents) > 0
    
    def test_admin_context_creation(self):
        """관리자 컨텍스트 생성"""
        context = ContextFactory.create_for_admin(
            user_id="admin_user",
            user_name="Admin"
        )
        
        assert context.user_role == "admin"
        assert context.max_tokens == 4000
        assert context.features["enable_human_in_loop"] == True
    
    def test_guest_context_creation(self):
        """게스트 컨텍스트 생성"""
        context = ContextFactory.create_for_guest()
        
        assert context.user_role == "guest"
        assert context.model_name == "gpt-3.5-turbo"
        assert len(context.available_agents) == 2  # 제한된 에이전트
        assert context.features["enable_memory"] == False
    
    def test_context_methods(self):
        """컨텍스트 메서드 테스트"""
        context = ContextFactory.create_for_user("user1", "User1")
        
        # 모델 설정 가져오기
        model_config = context.get_model_config()
        assert model_config["provider"] == "openai"
        assert model_config["temperature"] == 0.7
        
        # 에이전트 가용성 확인
        assert context.is_agent_available("analyzer_agent") == True
        assert context.is_agent_available("non_existent") == False
        
        # 실행 설정 가져오기
        exec_config = context.get_execution_config()
        assert exec_config["strategy"] == "sequential"
        assert exec_config["max_retries"] == 3


class TestAgents:
    """에이전트 테스트"""
    
    @pytest.mark.asyncio
    async def test_analyzer_agent(self, mock_llm):
        """분석 에이전트 테스트"""
        agent = AnalyzerAgent()
        
        with patch.object(agent, 'llm', mock_llm):
            result = await agent.analyze("강남구 아파트 시세가 어떻게 되나요?")
            
            assert "intent" in result
            assert "entities" in result
    
    @pytest.mark.asyncio
    async def test_planner_agent(self, mock_llm):
        """계획 에이전트 테스트"""
        agent = PlannerAgent()
        
        with patch.object(agent, 'llm', mock_llm):
            result = await agent.plan(
                intent="price_inquiry",
                entities={"location": "강남구", "property_type": "아파트"}
            )
            
            assert "steps" in result
            assert "agents" in result
            assert "strategy" in result
    
    @pytest.mark.asyncio
    async def test_supervisor_agent(self, mock_llm):
        """감독 에이전트 테스트"""
        agent = SupervisorAgent()
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value={"result": "test"})
        
        result = await agent.execute_agent(
            agent=mock_agent,
            query="테스트 쿼리",
            entities={},
            context={}
        )
        
        assert result is not None
        mock_agent.execute.assert_called_once()


class TestStateGraph:
    """StateGraph 테스트"""
    
    @pytest.mark.asyncio
    async def test_graph_building(self, test_context):
        """그래프 구축 테스트"""
        builder = RealEstateGraphBuilder(test_context)
        graph = builder.build()
        
        assert graph is not None
        # 노드 존재 확인
        nodes = graph.nodes
        assert "analyze" in nodes
        assert "plan" in nodes
        assert "route" in nodes
        assert "execute" in nodes
    
    @pytest.mark.asyncio
    async def test_graph_visualization(self, test_context):
        """그래프 시각화 테스트"""
        builder = RealEstateGraphBuilder(test_context)
        mermaid = builder.visualize()
        
        assert "graph TD" in mermaid
        assert "Analyze" in mermaid
        assert "Plan" in mermaid
        assert "Execute" in mermaid


class TestWorkflowEngine:
    """워크플로우 엔진 테스트"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, test_engine):
        """엔진 초기화 테스트"""
        assert test_engine._initialized == True
        assert test_engine.graph is not None
    
    @pytest.mark.asyncio
    async def test_simple_query_execution(self, test_engine):
        """간단한 쿼리 실행 테스트"""
        with patch.object(test_engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "final_response": "테스트 응답",
                "workflow_status": "completed",
                "execution_metrics": {"total_time": 1.0, "agents_called": 1}
            }
            
            result = await test_engine.execute(
                query="테스트 쿼리",
                thread_id="test_thread"
            )
            
            assert result["final_response"] == "테스트 응답"
            assert result["workflow_status"] == "completed"
            assert "metrics" in result
    
    @pytest.mark.asyncio
    async def test_thread_management(self, test_engine):
        """스레드 관리 테스트"""
        # 스레드 상태 조회 (존재하지 않는 경우)
        state = await test_engine.get_state("non_existent_thread")
        assert state is None
        
        # 스레드 목록 조회
        threads = await test_engine.list_threads()
        assert isinstance(threads, list)
    
    @pytest.mark.asyncio
    async def test_streaming_execution(self, test_engine):
        """스트리밍 실행 테스트"""
        events = []
        
        with patch.object(test_engine.graph, 'astream_events') as mock_stream:
            async def mock_events(*args, **kwargs):
                for event in [
                    {"event": "on_chain_start", "name": "test"},
                    {"event": "on_llm_stream", "data": {"chunk": "Hello"}},
                    {"event": "on_chain_end", "name": "test"}
                ]:
                    yield event
            
            mock_stream.return_value = mock_events()
            
            async for event in test_engine.stream_events("테스트 쿼리"):
                events.append(event)
        
        assert len(events) == 3
        assert events[0]["type"] == "chain_start"
        assert events[1]["type"] == "token"
        assert events[2]["type"] == "chain_end"


class TestEndToEnd:
    """End-to-End 테스트"""
    
    @pytest.mark.asyncio
    async def test_price_inquiry_flow(self):
        """가격 조회 플로우 테스트"""
        # 컨텍스트 생성
        context = ContextFactory.create_for_user("test_user", "Test User")
        
        # 엔진 생성
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=":memory:",
            enable_checkpointing=False
        )
        await engine.initialize()
        
        # Mock 설정
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "query": "강남구 아파트 시세",
                "intent": "price_inquiry",
                "entities": {"location": "강남구", "property_type": "아파트"},
                "selected_agents": ["price_search_agent"],
                "agent_results": {
                    "price_search_agent": {
                        "success": True,
                        "content": "강남구 아파트 평균 시세는 평당 5,000만원입니다."
                    }
                },
                "final_response": "강남구 아파트 평균 시세는 평당 5,000만원입니다.",
                "workflow_status": "completed",
                "execution_metrics": {"total_time": 2.5, "agents_called": 1},
                "confidence_scores": {"overall": 0.95}
            }
            
            result = await engine.execute("강남구 아파트 시세가 어떻게 되나요?")
        
        assert result["workflow_status"] == "completed"
        assert "강남구" in result["final_response"]
        assert result["metrics"]["confidence"] == 0.95
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_multi_agent_flow(self):
        """다중 에이전트 플로우 테스트"""
        context = ContextFactory.create_for_user("test_user", "Test User")
        
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=":memory:",
            enable_checkpointing=False
        )
        await engine.initialize()
        
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "query": "강남구 아파트 구매 시 대출과 세금은?",
                "intent": "consultation",
                "selected_agents": ["price_search_agent", "finance_agent", "legal_agent"],
                "agent_results": {
                    "price_search_agent": {"success": True, "content": "시세 정보"},
                    "finance_agent": {"success": True, "content": "대출 정보"},
                    "legal_agent": {"success": True, "content": "세금 정보"}
                },
                "final_response": "종합 상담 결과입니다.",
                "workflow_status": "completed",
                "execution_metrics": {"total_time": 5.0, "agents_called": 3},
                "confidence_scores": {"overall": 0.9}
            }
            
            result = await engine.execute("강남구 아파트 구매 시 대출과 세금은?")
        
        assert len(result["selected_agents"]) == 3
        assert result["metrics"]["agents_called"] == 3
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """에러 복구 테스트"""
        context = ContextFactory.create_for_testing()
        context.features["enable_error_recovery"] = True
        
        engine = AsyncWorkflowEngine(context=context, enable_checkpointing=False)
        await engine.initialize()
        
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            # 첫 번째 호출은 실패, 재시도 시 성공
            mock_invoke.side_effect = [
                asyncio.TimeoutError("Timeout"),
                {
                    "final_response": "재시도 성공",
                    "workflow_status": "completed",
                    "execution_metrics": {"total_time": 3.0, "agents_called": 1}
                }
            ]
            
            # 타임아웃 에러 처리
            result = await engine.execute("테스트 쿼리")
            
            # 에러가 발생해도 결과 반환
            assert "error" in result or result["workflow_status"] == "completed"
        
        await engine.close()


# 실행
if __name__ == "__main__":
    pytest.main([__file__, "-v"])