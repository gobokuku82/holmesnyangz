"""
LangSmith Integration for Real Estate Chatbot
Professional monitoring and debugging with LangSmith
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

# LangSmith setup
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "real-estate-chatbot"
# os.environ["LANGCHAIN_API_KEY"] = "your-langsmith-api-key"  # Set your API key

from langsmith import Client
from langsmith.run_helpers import traceable
from langgraph.graph import StateGraph
import logging

logger = logging.getLogger(__name__)


class LangSmithMonitor:
    """
    LangSmith monitoring wrapper for the chatbot
    Provides detailed tracing and debugging capabilities
    """
    
    def __init__(self, project_name: str = "real-estate-chatbot"):
        self.project_name = project_name
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize LangSmith client"""
        try:
            self.client = Client()
            logger.info(f"LangSmith client initialized for project: {self.project_name}")
        except Exception as e:
            logger.warning(f"LangSmith client initialization failed: {e}")
            logger.info("Continuing without LangSmith monitoring")
    
    @traceable(name="process_query", run_type="chain")
    async def traced_process_query(
        self,
        supervisor,
        query: str,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process query with LangSmith tracing
        
        Args:
            supervisor: RealEstateSupervisor instance
            query: User query
            session_id: Session ID
            metadata: Additional metadata for tracing
        
        Returns:
            Query processing result
        """
        # Add metadata to trace
        trace_metadata = {
            "session_id": session_id or "default",
            "timestamp": datetime.now().isoformat(),
            "query_length": len(query),
            **(metadata or {})
        }
        
        # Process query with tracing
        result = await supervisor.process_query(
            query=query,
            session_id=session_id
        )
        
        # Log to LangSmith
        if self.client:
            self.log_execution_metrics(result, trace_metadata)
        
        return result
    
    def log_execution_metrics(self, result: Dict[str, Any], metadata: Dict[str, Any]):
        """Log execution metrics to LangSmith"""
        try:
            metrics = {
                "intent_type": result.get("intent_type"),
                "selected_agents": result.get("selected_agents", []),
                "todo_count": len(result.get("todos", [])),
                "errors": len(result.get("errors", [])),
                "has_final_response": result.get("final_response") is not None
            }
            
            # Log as custom metrics
            logger.info(f"LangSmith metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")


class TracedSupervisor:
    """
    Wrapper for supervisor with automatic LangSmith tracing
    """
    
    def __init__(self, supervisor_class, llm_context=None):
        self.supervisor = supervisor_class(llm_context=llm_context)
        self.monitor = LangSmithMonitor()
        self._wrap_nodes()
    
    def _wrap_nodes(self):
        """Wrap all nodes with tracing"""
        # List of nodes to trace
        node_methods = [
            'analyze_intent_node',
            'create_plan_node',
            'execute_agents_node',
            'generate_response_node',
            'recheck_intent_node',
            'guidance_message_node',
            'error_handler_node'
        ]
        
        for method_name in node_methods:
            if hasattr(self.supervisor, method_name):
                original_method = getattr(self.supervisor, method_name)
                wrapped_method = self._create_traced_node(method_name, original_method)
                setattr(self.supervisor, method_name, wrapped_method)
    
    def _create_traced_node(self, node_name: str, original_method):
        """Create a traced version of a node"""
        
        @traceable(name=f"node_{node_name}", run_type="chain")
        async def traced_node(state: Dict[str, Any]) -> Dict[str, Any]:
            # Log input state
            logger.debug(f"[TRACE] {node_name} input state keys: {list(state.keys())}")
            
            # Execute original method
            result = await original_method(state)
            
            # Log output
            logger.debug(f"[TRACE] {node_name} output keys: {list(result.keys())}")
            
            return result
        
        return traced_node
    
    async def process_query(
        self,
        query: str,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process query with full tracing"""
        return await self.monitor.traced_process_query(
            self.supervisor,
            query,
            session_id,
            metadata
        )


# Configuration for LangSmith with environment variables
def setup_langsmith_env():
    """Setup LangSmith environment variables"""
    config = {
        "LANGCHAIN_TRACING_V2": "true",
        "LANGCHAIN_PROJECT": "real-estate-chatbot",
        "LANGCHAIN_ENDPOINT": "https://api.smith.langchain.com",
        # "LANGCHAIN_API_KEY": "your-api-key-here"  # Add your key
    }
    
    for key, value in config.items():
        if key != "LANGCHAIN_API_KEY" or value != "your-api-key-here":
            os.environ[key] = value
    
    print("LangSmith environment configured")
    print(f"Project: {config['LANGCHAIN_PROJECT']}")
    print(f"Tracing: {config['LANGCHAIN_TRACING_V2']}")


# Example test with LangSmith
async def test_with_langsmith():
    """Test the chatbot with LangSmith tracing"""
    
    # Setup environment
    setup_langsmith_env()
    
    # Import supervisor
    from app.service.supervisor.supervisor import RealEstateSupervisor
    
    # Create traced supervisor
    traced_supervisor = TracedSupervisor(RealEstateSupervisor)
    
    # Test queries
    test_queries = [
        "강남구 아파트 시세 알려줘",
        "부동산 투자 분석해줘",
        "전세 대출 조건은?"
    ]
    
    for query in test_queries:
        print(f"\n=== Testing: {query} ===")
        
        result = await traced_supervisor.process_query(
            query=query,
            session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            metadata={
                "test_mode": True,
                "test_type": "integration"
            }
        )
        
        # Print summary
        print(f"Intent: {result.get('intent_type')}")
        print(f"Selected Agents: {result.get('selected_agents')}")
        print(f"Final Response Type: {type(result.get('final_response'))}")
        
        # Check LangSmith dashboard for detailed traces
        print("Check LangSmith dashboard for detailed execution trace")
        print(f"https://smith.langchain.com/o/YOUR_ORG/projects/p/{os.environ.get('LANGCHAIN_PROJECT')}")


# Custom callbacks for detailed monitoring
class CustomLangSmithCallback:
    """Custom callback for additional monitoring"""
    
    @staticmethod
    def on_llm_start(serialized, prompts, **kwargs):
        """Log when LLM starts"""
        logger.info(f"LLM Start - Model: {serialized.get('name', 'unknown')}")
        logger.debug(f"Prompt length: {len(str(prompts))}")
    
    @staticmethod
    def on_llm_end(response, **kwargs):
        """Log when LLM ends"""
        logger.info("LLM End - Response received")
    
    @staticmethod
    def on_tool_start(serialized, input_str, **kwargs):
        """Log when tool starts"""
        tool_name = serialized.get("name", "unknown")
        logger.info(f"Tool Start - {tool_name}")
    
    @staticmethod
    def on_tool_end(output, **kwargs):
        """Log when tool ends"""
        logger.info("Tool End - Output received")


if __name__ == "__main__":
    # Run test with LangSmith
    asyncio.run(test_with_langsmith())