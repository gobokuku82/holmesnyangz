"""
Async Workflow Engine for LangGraph 0.6.6
비동기 실행 엔진 with Context API support
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage, AIMessage

from backend.core.state import AgentState, create_initial_state
from backend.core.context import RealEstateContext, ContextFactory
from backend.core.graph_builder import RealEstateGraphBuilder


logger = logging.getLogger(__name__)


class AsyncWorkflowEngine:
    """
    LangGraph 0.6.6 비동기 워크플로우 엔진
    AsyncSqliteSaver를 사용한 체크포인팅 지원
    """
    
    def __init__(
        self,
        context: RealEstateContext,
        checkpoint_db: Optional[str] = "checkpoints.db",
        enable_checkpointing: bool = True
    ):
        """
        Args:
            context: 실행 컨텍스트
            checkpoint_db: 체크포인트 DB 경로
            enable_checkpointing: 체크포인팅 활성화 여부
        """
        self.context = context
        self.checkpoint_db = checkpoint_db
        self.enable_checkpointing = enable_checkpointing
        self.graph: Optional[StateGraph] = None
        self.checkpointer: Optional[AsyncSqliteSaver] = None
        self._initialized = False
        
    async def initialize(self):
        """엔진 초기화"""
        if self._initialized:
            return
            
        # 그래프 빌더 생성 및 컴파일
        builder = RealEstateGraphBuilder(self.context)
        self.graph = builder.build()
        
        # 체크포인터 초기화
        if self.enable_checkpointing:
            self.checkpointer = await self._create_checkpointer()
            
        self._initialized = True
        logger.info(f"Workflow engine initialized for session: {self.context.session_id}")
    
    async def _create_checkpointer(self) -> AsyncSqliteSaver:
        """AsyncSqliteSaver 생성"""
        # AsyncSqliteSaver는 컨텍스트 매니저로 사용
        return AsyncSqliteSaver.from_conn_string(self.checkpoint_db)
    
    @asynccontextmanager
    async def _get_checkpointer_context(self):
        """체크포인터 컨텍스트 매니저"""
        if self.enable_checkpointing:
            async with AsyncSqliteSaver.from_conn_string(self.checkpoint_db) as saver:
                yield saver
        else:
            yield None
    
    async def execute(
        self,
        query: str,
        thread_id: Optional[str] = None,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """
        워크플로우 실행
        
        Args:
            query: 사용자 쿼리
            thread_id: 대화 스레드 ID
            streaming: 스트리밍 모드 여부
            
        Returns:
            실행 결과
        """
        if not self._initialized:
            await self.initialize()
        
        # 스레드 ID 생성
        if not thread_id:
            thread_id = f"{self.context.session_id}_{datetime.now().timestamp()}"
        
        # 초기 상태 생성
        initial_state = create_initial_state(query)
        initial_state["messages"] = [HumanMessage(content=query)]
        
        # 실행 설정
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": self.context.user_id,
                "session_id": self.context.session_id
            },
            "recursion_limit": 10,
            "callbacks": []
        }
        
        try:
            async with self._get_checkpointer_context() as checkpointer:
                if checkpointer:
                    # 체크포인터가 있는 경우 컴파일 시 포함
                    graph = self.graph.compile(checkpointer=checkpointer)
                else:
                    graph = self.graph
                
                if streaming and self.context.features.get("enable_streaming"):
                    # 스트리밍 실행
                    result = await self._execute_streaming(graph, initial_state, config)
                else:
                    # 일반 실행
                    result = await self._execute_batch(graph, initial_state, config)
                
                # 실행 메트릭 추가
                result["metrics"] = {
                    "thread_id": thread_id,
                    "execution_time": result.get("execution_metrics", {}).get("total_time", 0),
                    "agents_called": result.get("execution_metrics", {}).get("agents_called", 0),
                    "confidence": result.get("confidence_scores", {}).get("overall", 0)
                }
                
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Workflow timeout for thread {thread_id}")
            return {
                "error": "Workflow execution timeout",
                "thread_id": thread_id,
                "workflow_status": "timeout"
            }
        except Exception as e:
            logger.error(f"Workflow error for thread {thread_id}: {str(e)}")
            return {
                "error": str(e),
                "thread_id": thread_id,
                "workflow_status": "error"
            }
    
    async def _execute_batch(
        self,
        graph: StateGraph,
        initial_state: AgentState,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """배치 실행 (비스트리밍)"""
        # 타임아웃 설정
        timeout = self.context.max_execution_time
        
        # 그래프 실행
        final_state = await asyncio.wait_for(
            graph.ainvoke(initial_state, config),
            timeout=timeout
        )
        
        return final_state
    
    async def _execute_streaming(
        self,
        graph: StateGraph,
        initial_state: AgentState,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """스트리밍 실행"""
        timeout = self.context.max_execution_time
        final_state = None
        
        try:
            # 스트리밍으로 실행
            async with asyncio.timeout(timeout):
                async for chunk in graph.astream(initial_state, config):
                    # 중간 상태 처리 (필요시 yield 가능)
                    final_state = chunk
                    
                    # 상태 로깅
                    if "workflow_status" in chunk:
                        logger.debug(f"Workflow status: {chunk['workflow_status']}")
                        
        except asyncio.TimeoutError:
            raise
            
        return final_state or initial_state
    
    async def get_state(
        self,
        thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        스레드의 현재 상태 조회
        
        Args:
            thread_id: 대화 스레드 ID
            
        Returns:
            현재 상태 또는 None
        """
        if not self.enable_checkpointing:
            return None
            
        async with self._get_checkpointer_context() as checkpointer:
            if not checkpointer:
                return None
                
            config = {"configurable": {"thread_id": thread_id}}
            
            # 체크포인트에서 상태 조회
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                return checkpoint_tuple.checkpoint.get("channel_values", {})
            
            return None
    
    async def list_threads(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        사용자의 대화 스레드 목록 조회
        
        Args:
            limit: 최대 조회 개수
            
        Returns:
            스레드 목록
        """
        if not self.enable_checkpointing:
            return []
            
        threads = []
        
        async with self._get_checkpointer_context() as checkpointer:
            if not checkpointer:
                return []
                
            # 사용자 세션의 모든 스레드 조회
            filter_config = {
                "configurable": {
                    "user_id": self.context.user_id,
                    "session_id": self.context.session_id
                }
            }
            
            count = 0
            async for checkpoint in checkpointer.alist(filter_config):
                if count >= limit:
                    break
                    
                thread_info = {
                    "thread_id": checkpoint.config.get("configurable", {}).get("thread_id"),
                    "created_at": checkpoint.metadata.get("created_at"),
                    "last_update": checkpoint.metadata.get("updated_at"),
                    "status": checkpoint.checkpoint.get("channel_values", {}).get("workflow_status")
                }
                threads.append(thread_info)
                count += 1
                
        return threads
    
    async def delete_thread(self, thread_id: str) -> bool:
        """
        스레드 삭제
        
        Args:
            thread_id: 삭제할 스레드 ID
            
        Returns:
            삭제 성공 여부
        """
        if not self.enable_checkpointing:
            return False
            
        async with self._get_checkpointer_context() as checkpointer:
            if not checkpointer:
                return False
                
            config = {"configurable": {"thread_id": thread_id}}
            
            try:
                await checkpointer.adelete(config)
                logger.info(f"Thread {thread_id} deleted")
                return True
            except Exception as e:
                logger.error(f"Failed to delete thread {thread_id}: {str(e)}")
                return False
    
    async def stream_events(
        self,
        query: str,
        thread_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        이벤트 스트리밍 (SSE용)
        
        Args:
            query: 사용자 쿼리
            thread_id: 대화 스레드 ID
            
        Yields:
            이벤트 데이터
        """
        if not self._initialized:
            await self.initialize()
            
        if not thread_id:
            thread_id = f"{self.context.session_id}_{datetime.now().timestamp()}"
            
        initial_state = create_initial_state(query)
        initial_state["messages"] = [HumanMessage(content=query)]
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": self.context.user_id
            }
        }
        
        async with self._get_checkpointer_context() as checkpointer:
            if checkpointer:
                graph = self.graph.compile(checkpointer=checkpointer)
            else:
                graph = self.graph
                
            # 스트리밍 이벤트 생성
            async for event in graph.astream_events(initial_state, config, version="v1"):
                # 이벤트 타입별 처리
                if event["event"] == "on_chain_start":
                    yield {
                        "type": "chain_start",
                        "name": event["name"],
                        "timestamp": datetime.now().isoformat()
                    }
                elif event["event"] == "on_chain_end":
                    yield {
                        "type": "chain_end",
                        "name": event["name"],
                        "output": event.get("data", {}).get("output"),
                        "timestamp": datetime.now().isoformat()
                    }
                elif event["event"] == "on_llm_stream":
                    # LLM 스트리밍 토큰
                    yield {
                        "type": "token",
                        "content": event.get("data", {}).get("chunk", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                elif event["event"] == "on_tool_start":
                    yield {
                        "type": "tool_start",
                        "tool": event["name"],
                        "timestamp": datetime.now().isoformat()
                    }
                elif event["event"] == "on_tool_end":
                    yield {
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": event.get("data", {}).get("output"),
                        "timestamp": datetime.now().isoformat()
                    }
    
    async def close(self):
        """엔진 종료"""
        if self.checkpointer:
            # AsyncSqliteSaver는 컨텍스트 매니저로 자동 정리됨
            pass
            
        self._initialized = False
        logger.info("Workflow engine closed")


class WorkflowEngineFactory:
    """워크플로우 엔진 팩토리"""
    
    @staticmethod
    async def create_for_user(
        user_id: str,
        user_name: str,
        checkpoint_db: Optional[str] = "checkpoints.db"
    ) -> AsyncWorkflowEngine:
        """일반 사용자용 엔진 생성"""
        context = ContextFactory.create_for_user(
            user_id=user_id,
            user_name=user_name
        )
        
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=checkpoint_db,
            enable_checkpointing=True
        )
        
        await engine.initialize()
        return engine
    
    @staticmethod
    async def create_for_admin(
        user_id: str,
        user_name: str,
        checkpoint_db: Optional[str] = "checkpoints.db"
    ) -> AsyncWorkflowEngine:
        """관리자용 엔진 생성"""
        context = ContextFactory.create_for_admin(
            user_id=user_id,
            user_name=user_name
        )
        
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=checkpoint_db,
            enable_checkpointing=True
        )
        
        await engine.initialize()
        return engine
    
    @staticmethod
    async def create_for_guest(
        checkpoint_db: Optional[str] = None
    ) -> AsyncWorkflowEngine:
        """게스트용 엔진 생성 (체크포인팅 비활성화)"""
        context = ContextFactory.create_for_guest()
        
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=checkpoint_db,
            enable_checkpointing=False  # 게스트는 체크포인팅 비활성화
        )
        
        await engine.initialize()
        return engine
    
    @staticmethod
    async def create_for_testing() -> AsyncWorkflowEngine:
        """테스트용 엔진 생성"""
        context = ContextFactory.create_for_testing()
        
        engine = AsyncWorkflowEngine(
            context=context,
            checkpoint_db=":memory:",  # 메모리 DB 사용
            enable_checkpointing=True
        )
        
        await engine.initialize()
        return engine