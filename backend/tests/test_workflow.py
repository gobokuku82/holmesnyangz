"""
Workflow and StateGraph Tests
워크플로우와 상태 그래프 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from backend.core.state import AgentState, create_initial_state, validate_state
from backend.core.context import RealEstateContext, ContextFactory
from backend.core.graph_builder import RealEstateGraphBuilder
from backend.core.workflow_engine import AsyncWorkflowEngine, WorkflowEngineFactory


class TestState:
    """State 관리 테스트"""
    
    def test_create_initial_state(self):
        """초기 상태 생성 테스트"""
        state = create_initial_state("테스트 쿼리")
        
        assert state["query"] == "테스트 쿼리"
        assert state["messages"] == []
        assert state["workflow_status"] == "initialized"
        assert state["errors"] == {}
        assert state["retry_count"] == 0
    
    def test_validate_state(self):
        """상태 검증 테스트"""
        # 유효한 상태
        valid_state = create_initial_state("테스트")
        is_valid, errors = validate_state(valid_state)
        assert is_valid == True
        assert len(errors) == 0
        
        # 잘못된 상태
        invalid_state = {"query": ""}  # 필수 필드 누락
        is_valid, errors = validate_state(invalid_state)
        assert is_valid == False
        assert len(errors) > 0


class TestGraphBuilder:
    """GraphBuilder 테스트"""
    
    @pytest.fixture
    def context(self):
        return ContextFactory.create_for_testing()
    
    @pytest.fixture
    def builder(self, context):
        return RealEstateGraphBuilder(context)
    
    def test_initialize_agents(self, builder):
        """에이전트 초기화 테스트"""
        agents = builder.agents
        
        assert "analyzer" in agents
        assert "planner" in agents
        assert "supervisor" in agents
        
        # Context에서 활성화된 에이전트만 초기화
        for agent_id in builder.context.available_agents:
            agent_key = agent_id.replace("_agent", "").replace("_", "_")
            if agent_key in ["price_search", "finance", "location", "legal"]:
                assert agent_key in agents
    
    def test_build_graph(self, builder):
        """그래프 빌드 테스트"""
        graph = builder.build()
        
        assert graph is not None
        # 노드 확인
        assert hasattr(graph, 'nodes')
    
    @pytest.mark.asyncio
    async def test_analyze_node(self, builder):
        """분석 노드 테스트"""
        state = create_initial_state("강남구 아파트 시세")
        
        with patch.object(builder.agents["analyzer"], 'analyze') as mock_analyze:
            mock_analyze.return_value = {
                "intent": "price_inquiry",
                "entities": {"location": "강남구"},
                "confidence": 0.9
            }
            
            result = await builder._analyze_node(state)
            
            assert result["intent"] == "price_inquiry"
            assert result["entities"]["location"] == "강남구"
            assert result["workflow_status"] == "analyzed"
    
    @pytest.mark.asyncio
    async def test_plan_node(self, builder):
        """계획 노드 테스트"""
        state = create_initial_state("테스트")
        state["intent"] = "price_inquiry"
        state["entities"] = {"location": "강남구"}
        
        with patch.object(builder.agents["planner"], 'plan') as mock_plan:
            mock_plan.return_value = {
                "steps": ["가격 조회"],
                "agents": ["price_search_agent"],
                "strategy": "sequential"
            }
            
            result = await builder._plan_node(state)
            
            assert result["plan"] == ["가격 조회"]
            assert result["selected_agents"] == ["price_search_agent"]
            assert result["execution_strategy"] == "sequential"
            assert result["workflow_status"] == "planned"
    
    @pytest.mark.asyncio
    async def test_error_handler_node(self, builder):
        """에러 처리 노드 테스트"""
        state = create_initial_state("테스트")
        state["errors"] = {"test_error": "Test error message"}
        state["retry_count"] = 0
        
        # 에러 복구 활성화
        builder.context.features["enable_error_recovery"] = True
        
        result = await builder._error_handler_node(state)
        
        assert result["workflow_status"] in ["retry", "failed"]
        assert result["retry_count"] > 0 or result["workflow_status"] == "failed"
    
    def test_routing_functions(self, builder):
        """라우팅 함수 테스트"""
        # _should_execute 테스트
        state = create_initial_state("테스트")
        state["workflow_status"] = "planned"
        state["selected_agents"] = ["price_search_agent"]
        state["current_agent_index"] = 0
        
        result = builder._should_execute(state)
        assert result == "execute"
        
        # 완료 상태
        state["workflow_status"] = "completed"
        result = builder._should_execute(state)
        assert result == "end"
        
        # _check_execution_status 테스트
        state["workflow_status"] = "executing"
        result = builder._check_execution_status(state)
        assert result == "aggregate"
        
        state["workflow_status"] = "retry"
        result = builder._check_execution_status(state)
        assert result == "retry"


class TestWorkflowEngine:
    """워크플로우 엔진 테스트"""
    
    @pytest.fixture
    async def engine(self):
        engine = await WorkflowEngineFactory.create_for_testing()
        yield engine
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, engine):
        """엔진 초기화 테스트"""
        assert engine._initialized == True
        assert engine.graph is not None
        assert engine.context is not None
    
    @pytest.mark.asyncio
    async def test_execute_query(self, engine):
        """쿼리 실행 테스트"""
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "query": "테스트 쿼리",
                "final_response": "테스트 응답",
                "workflow_status": "completed",
                "execution_metrics": {
                    "total_time": 1.5,
                    "agents_called": 1
                },
                "confidence_scores": {"overall": 0.9}
            }
            
            result = await engine.execute(
                query="테스트 쿼리",
                thread_id="test_thread_1"
            )
            
            assert result["workflow_status"] == "completed"
            assert result["final_response"] == "테스트 응답"
            assert "metrics" in result
            assert result["metrics"]["thread_id"] == "test_thread_1"
    
    @pytest.mark.asyncio
    async def test_streaming_execution(self, engine):
        """스트리밍 실행 테스트"""
        events = []
        
        with patch.object(engine.graph, 'astream_events') as mock_stream:
            async def mock_events(*args, **kwargs):
                yield {"event": "on_chain_start", "name": "analyze"}
                yield {"event": "on_llm_stream", "data": {"chunk": "테스트"}}
                yield {"event": "on_chain_end", "name": "analyze"}
            
            mock_stream.return_value = mock_events()
            
            async for event in engine.stream_events("테스트 쿼리"):
                events.append(event)
        
        assert len(events) == 3
        assert events[0]["type"] == "chain_start"
        assert events[1]["type"] == "token"
        assert events[1]["content"] == "테스트"
    
    @pytest.mark.asyncio
    async def test_thread_management(self, engine):
        """스레드 관리 테스트"""
        # 체크포인팅이 비활성화된 경우
        if not engine.enable_checkpointing:
            state = await engine.get_state("test_thread")
            assert state is None
            
            threads = await engine.list_threads()
            assert threads == []
            
            deleted = await engine.delete_thread("test_thread")
            assert deleted == False
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, engine):
        """타임아웃 처리 테스트"""
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            # 타임아웃 시뮬레이션
            async def timeout_simulation(*args, **kwargs):
                await asyncio.sleep(100)  # 긴 시간 대기
            
            mock_invoke.side_effect = timeout_simulation
            
            # 짧은 타임아웃 설정
            engine.context.max_execution_time = 0.1
            
            result = await engine.execute("테스트 쿼리")
            
            assert "error" in result
            assert result["workflow_status"] in ["timeout", "error"]


class TestWorkflowFactory:
    """워크플로우 팩토리 테스트"""
    
    @pytest.mark.asyncio
    async def test_create_for_user(self):
        """사용자용 엔진 생성 테스트"""
        engine = await WorkflowEngineFactory.create_for_user(
            user_id="test_user",
            user_name="Test User"
        )
        
        assert engine.context.user_role == "user"
        assert engine.context.user_id == "test_user"
        assert engine.enable_checkpointing == True
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_create_for_admin(self):
        """관리자용 엔진 생성 테스트"""
        engine = await WorkflowEngineFactory.create_for_admin(
            user_id="admin_user",
            user_name="Admin"
        )
        
        assert engine.context.user_role == "admin"
        assert engine.context.max_tokens == 4000
        assert engine.context.features["enable_human_in_loop"] == True
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_create_for_guest(self):
        """게스트용 엔진 생성 테스트"""
        engine = await WorkflowEngineFactory.create_for_guest()
        
        assert engine.context.user_role == "guest"
        assert engine.enable_checkpointing == False  # 게스트는 체크포인팅 비활성화
        assert len(engine.context.available_agents) < 5  # 제한된 에이전트
        
        await engine.close()


class TestEndToEndWorkflow:
    """전체 워크플로우 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_simple_price_inquiry_flow(self):
        """간단한 가격 조회 플로우"""
        engine = await WorkflowEngineFactory.create_for_testing()
        
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "query": "강남구 아파트 시세",
                "intent": "price_inquiry",
                "entities": {"location": "강남구", "property_type": "아파트"},
                "selected_agents": ["price_search_agent"],
                "agent_results": {
                    "price_search_agent": {
                        "success": True,
                        "content": "강남구 아파트 평균 시세: 평당 5,000만원"
                    }
                },
                "final_response": "강남구 아파트 평균 시세는 평당 5,000만원입니다.",
                "workflow_status": "completed",
                "execution_metrics": {"total_time": 2.0, "agents_called": 1},
                "confidence_scores": {"overall": 0.95}
            }
            
            result = await engine.execute("강남구 아파트 시세")
            
            assert result["workflow_status"] == "completed"
            assert "5,000만원" in result["final_response"]
            assert result["metrics"]["agents_called"] == 1
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_complex_consultation_flow(self):
        """복잡한 상담 플로우"""
        engine = await WorkflowEngineFactory.create_for_testing()
        
        with patch.object(engine.graph, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "query": "10억 예산으로 강남 아파트 구매 상담",
                "intent": "purchase_consultation",
                "entities": {
                    "budget": 1000000000,
                    "location": "강남구",
                    "property_type": "아파트"
                },
                "selected_agents": [
                    "price_search_agent",
                    "finance_agent",
                    "legal_agent"
                ],
                "agent_results": {
                    "price_search_agent": {
                        "success": True,
                        "content": "예산 내 구매 가능 물건 10개"
                    },
                    "finance_agent": {
                        "success": True,
                        "content": "최대 대출 6억, 월 상환액 250만원"
                    },
                    "legal_agent": {
                        "success": True,
                        "content": "취득세 3,000만원"
                    }
                },
                "final_response": "종합 상담 결과: 구매 가능 물건 10개, 대출 6억, 취득세 3,000만원",
                "workflow_status": "completed",
                "execution_metrics": {"total_time": 5.0, "agents_called": 3},
                "confidence_scores": {"overall": 0.88}
            }
            
            result = await engine.execute("10억 예산으로 강남 아파트 구매 상담")
            
            assert result["workflow_status"] == "completed"
            assert result["metrics"]["agents_called"] == 3
            assert len(result["selected_agents"]) == 3
        
        await engine.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])