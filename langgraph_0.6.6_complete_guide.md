# LangGraph 0.6.6 완전 가이드라인

## 📋 목차
1. [핵심 구현 규칙](#1-핵심-구현-규칙)
2. [상태 관리](#2-상태-관리)
3. [그래프 구성](#3-그래프-구성)
4. [에러 핸들링](#4-에러-핸들링)
5. [Human-in-the-Loop](#5-human-in-the-loop)
6. [도구 통합](#6-도구-통합)
7. [프로덕션 체크리스트](#7-프로덕션-체크리스트)
8. [디버깅 전략](#8-디버깅-전략)
9. [마이그레이션 가이드](#9-마이그레이션-가이드)

---

## 1. 핵심 구현 규칙

### 기본 원칙
- **명시적 타입 정의**: 모든 상태는 TypedDict로 정의
- **불변성 지향**: 노드는 상태를 직접 수정하지 않고 dict 반환
- **단일 책임**: 각 노드는 하나의 명확한 역할만 수행
- **컴파일 필수**: 그래프는 반드시 compile() 후 실행

### 필수 import
```python
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.runtime import HandOff
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import logging
import yaml
```

---

## 2. 상태 관리

### 강화된 상태 정의
```python
class AgentState(TypedDict):
    # 기본 상태
    query: str
    messages: Annotated[List[BaseMessage], add_messages]
    plan: List[str]
    history: List[Dict[str, Any]]
    
    # 에러 관리
    errors: Dict[str, str]
    error_counts: Dict[str, int]
    retry_attempts: int
    max_retries: int
    
    # 실행 제어
    current_step: str
    workflow_status: str  # "running", "paused", "completed", "failed"
    checkpoints: List[Dict[str, Any]]
    
    # 메타데이터
    user_id: Optional[str]
    session_id: str
    timestamp: str
    config: Dict[str, Any]
```

### Reducer 패턴
```python
from operator import add
from typing import Annotated

# 리스트 병합용 reducer
def merge_lists(left: list, right: list) -> list:
    return left + right

# 딕셔너리 업데이트용 reducer
def update_dict(left: dict, right: dict) -> dict:
    return {**left, **right}

class AdvancedState(TypedDict):
    messages: Annotated[List[BaseMessage], add]
    errors: Annotated[Dict[str, str], update_dict]
    steps: Annotated[List[str], merge_lists]
```

---

## 3. 그래프 구성

### 계층적 그래프 구조
```python
class SupervisorGraph:
    def __init__(self):
        self.graph_builder = StateGraph(AgentState)
        self.setup_nodes()
        self.setup_edges()
        self.setup_conditional_routing()
    
    def setup_nodes(self):
        """노드 등록"""
        self.graph_builder.add_node("config_loader", self.load_config_node)
        self.graph_builder.add_node("analyzer", self.analyze_query_node)
        self.graph_builder.add_node("planner", self.planning_node)
        self.graph_builder.add_node("validator", self.validation_node)
        self.graph_builder.add_node("executor", self.execution_node)
        self.graph_builder.add_node("error_handler", self.error_handler_node)
        self.graph_builder.add_node("result_aggregator", self.aggregate_results_node)
    
    def setup_edges(self):
        """기본 엣지 설정"""
        self.graph_builder.add_edge(START, "config_loader")
        self.graph_builder.add_edge("config_loader", "analyzer")
        self.graph_builder.add_edge("result_aggregator", END)
    
    def setup_conditional_routing(self):
        """조건부 라우팅"""
        self.graph_builder.add_conditional_edges(
            "analyzer",
            self.route_by_complexity,
            {
                "simple": "executor",
                "complex": "planner",
                "error": "error_handler"
            }
        )
        
        self.graph_builder.add_conditional_edges(
            "executor",
            self.check_execution_result,
            {
                "success": "result_aggregator",
                "retry": "executor",
                "failed": "error_handler"
            }
        )
```

### 라우팅 함수
```python
def route_by_complexity(self, state: AgentState) -> str:
    """복잡도 기반 라우팅"""
    query = state.get("query", "")
    
    # 에러 상태 체크
    if state.get("errors"):
        return "error"
    
    # 복잡도 판단 로직
    if self.is_simple_query(query):
        return "simple"
    elif self.requires_planning(query):
        return "complex"
    else:
        return "error"

def check_execution_result(self, state: AgentState) -> str:
    """실행 결과 체크"""
    if state.get("workflow_status") == "completed":
        return "success"
    elif state.get("retry_attempts", 0) < state.get("max_retries", 3):
        return "retry"
    else:
        return "failed"
```

---

## 4. 에러 핸들링

### 포괄적 에러 처리 시스템
```python
class ErrorHandler:
    ERROR_CATEGORIES = {
        "RATE_LIMIT": ["rate limit", "too many requests", "quota exceeded"],
        "TIMEOUT": ["timeout", "timed out", "deadline exceeded"],
        "AUTH": ["unauthorized", "authentication", "forbidden"],
        "NETWORK": ["connection", "network", "unreachable"],
        "VALIDATION": ["invalid", "validation", "schema"],
        "CRITICAL": ["critical", "fatal", "system failure"]
    }
    
    @staticmethod
    def categorize_error(error_msg: str) -> str:
        """에러 분류"""
        error_lower = error_msg.lower()
        for category, keywords in ErrorHandler.ERROR_CATEGORIES.items():
            if any(keyword in error_lower for keyword in keywords):
                return category
        return "UNKNOWN"
    
    @staticmethod
    def handle_error(state: AgentState) -> AgentState:
        """에러 처리 노드"""
        errors = state.get("errors", {})
        error_counts = state.get("error_counts", {})
        
        for tool_id, error_msg in errors.items():
            error_type = ErrorHandler.categorize_error(error_msg)
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            # 에러 타입별 처리
            if error_type == "RATE_LIMIT":
                logging.warning(f"Rate limit hit: {error_msg}")
                time.sleep(60)  # 1분 대기
            elif error_type == "TIMEOUT":
                state["retry_attempts"] = state.get("retry_attempts", 0) + 1
            elif error_type == "CRITICAL":
                state["workflow_status"] = "failed"
                logging.error(f"Critical error: {error_msg}")
                # 알림 발송 로직
                
        return {
            "error_counts": error_counts,
            "workflow_status": state.get("workflow_status", "running")
        }
```

### Try-Catch 래퍼
```python
def safe_node_execution(func):
    """노드 실행 안전 래퍼"""
    def wrapper(state: AgentState) -> Dict:
        try:
            logging.debug(f"Executing node: {func.__name__}")
            result = func(state)
            logging.debug(f"Node {func.__name__} completed successfully")
            return result
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            return {
                "errors": {func.__name__: str(e)},
                "workflow_status": "error"
            }
    return wrapper
```

---

## 5. Human-in-the-Loop

### 승인 시스템
```python
from langgraph.runtime import HandOff

class ApprovalSystem:
    @staticmethod
    def approval_required_node(state: AgentState) -> Union[Dict, HandOff]:
        """승인 필요 여부 판단"""
        plan = state.get("plan", [])
        
        # 승인 필요 조건
        requires_approval = any([
            len(plan) > 5,  # 복잡한 계획
            "delete" in str(plan).lower(),  # 삭제 작업
            "production" in str(plan).lower(),  # 프로덕션 환경
            state.get("estimated_cost", 0) > 100  # 고비용 작업
        ])
        
        if requires_approval:
            print(f"승인 필요: {plan}")
            return HandOff()
        
        return {"approval_status": "auto_approved"}
    
    @staticmethod
    def human_feedback_node(state: AgentState) -> Dict:
        """사용자 피드백 처리"""
        feedback = state.get("human_feedback", {})
        
        if feedback.get("approved"):
            return {"workflow_status": "approved", "can_proceed": True}
        else:
            return {
                "workflow_status": "rejected",
                "rejection_reason": feedback.get("reason", "User rejected")
            }
```

---

## 6. 도구 통합

### Tool 정의 및 관리
```python
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent

class ToolManager:
    @staticmethod
    @tool
    def search_web(query: str) -> str:
        """웹 검색 도구
        Args:
            query: 검색 쿼리
        Returns:
            검색 결과
        """
        try:
            # 실제 검색 로직
            return f"Search results for: {query}"
        except Exception as e:
            raise ToolException(f"Web search failed: {str(e)}")
    
    @staticmethod
    @tool
    def query_database(sql: str, database: str = "default") -> str:
        """데이터베이스 쿼리 도구"""
        # SQL 유효성 검사
        if not ToolManager.validate_sql(sql):
            raise ToolException("Invalid SQL query")
        
        # 실행
        return "Query results"
    
    @staticmethod
    def create_agent_executor(llm, tools, prompt):
        """Agent Executor 생성"""
        agent = create_tool_calling_agent(llm, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="force"
        )
```

---

## 7. 프로덕션 체크리스트

### 배포 전 필수 확인사항
```python
class ProductionReadiness:
    CHECKLIST = {
        "performance": {
            "latency_target_ms": 500,
            "throughput_rps": 100,
            "memory_limit_mb": 512,
            "cpu_limit_cores": 2
        },
        "reliability": {
            "error_rate_threshold": 0.01,
            "availability_target": 0.999,
            "timeout_seconds": 30,
            "retry_policy": "exponential_backoff"
        },
        "monitoring": {
            "metrics": ["latency", "error_rate", "throughput"],
            "logging_level": "INFO",
            "tracing": True,
            "alerting": True
        },
        "security": {
            "authentication": True,
            "rate_limiting": True,
            "input_validation": True,
            "secrets_management": "vault"
        }
    }
    
    @staticmethod
    def validate_deployment():
        """배포 검증"""
        checks = []
        
        # 환경 변수 체크
        required_env = ["OPENAI_API_KEY", "DATABASE_URL", "REDIS_URL"]
        for env in required_env:
            if not os.getenv(env):
                checks.append(f"Missing environment variable: {env}")
        
        # 의존성 체크
        required_packages = ["langgraph==0.6.6", "langchain-core", "pydantic>=2.0"]
        # ... 패키지 검증 로직
        
        return len(checks) == 0, checks
```

### 체크포인트 설정
```python
from langgraph.checkpoint import MemorySaver, SqliteSaver

class CheckpointManager:
    @staticmethod
    def setup_checkpointer(storage_type="sqlite"):
        """체크포인터 설정"""
        if storage_type == "memory":
            return MemorySaver()
        elif storage_type == "sqlite":
            return SqliteSaver.from_conn_string("checkpoints.db")
        elif storage_type == "redis":
            # Redis 체크포인터 설정
            pass
        elif storage_type == "s3":
            # S3 체크포인터 설정
            pass
    
    @staticmethod
    def compile_with_checkpoint(graph_builder, checkpointer):
        """체크포인트와 함께 컴파일"""
        return graph_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=["approval_required_node"],
            interrupt_after=["critical_operation_node"]
        )
```

---

## 8. 디버깅 전략

### 통합 디버깅 시스템
```python
import logging
from datetime import datetime
from langsmith import trace

class DebugSystem:
    def __init__(self, debug_level="INFO"):
        self.setup_logging(debug_level)
        self.setup_tracing()
    
    def setup_logging(self, level):
        """로깅 설정"""
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'langgraph_{datetime.now():%Y%m%d}.log'),
                logging.StreamHandler()
            ]
        )
    
    def setup_tracing(self):
        """LangSmith 트레이싱 설정"""
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "langgraph-chatbot"
    
    @staticmethod
    @trace
    def debug_node(func):
        """노드 디버깅 데코레이터"""
        def wrapper(state: AgentState) -> Dict:
            node_name = func.__name__
            logging.debug(f"[{node_name}] Input state: {state}")
            
            start_time = time.time()
            result = func(state)
            execution_time = time.time() - start_time
            
            logging.debug(f"[{node_name}] Output: {result}")
            logging.info(f"[{node_name}] Execution time: {execution_time:.2f}s")
            
            return result
        return wrapper
    
    @staticmethod
    def validate_state(state: AgentState):
        """상태 유효성 검증"""
        issues = []
        
        # 필수 필드 체크
        required_fields = ["query", "session_id", "workflow_status"]
        for field in required_fields:
            if field not in state:
                issues.append(f"Missing required field: {field}")
        
        # 타입 체크
        if "messages" in state and not isinstance(state["messages"], list):
            issues.append("'messages' must be a list")
        
        if issues:
            logging.error(f"State validation failed: {issues}")
            raise ValueError(f"Invalid state: {issues}")
```

---

## 9. 마이그레이션 가이드

### LangGraph 0.2.x → 0.6.x 마이그레이션
```python
class MigrationHelper:
    """버전 마이그레이션 헬퍼"""
    
    @staticmethod
    def migrate_state_definition(old_state: dict) -> TypedDict:
        """구버전 상태 정의 마이그레이션"""
        # 0.2.x 스타일
        # state = {"messages": [], "context": {}}
        
        # 0.6.x 스타일
        class NewState(TypedDict):
            messages: Annotated[List[BaseMessage], add_messages]
            context: Dict[str, Any]
        
        return NewState
    
    @staticmethod
    def migrate_agent_executor(old_code: str) -> str:
        """AgentExecutor 마이그레이션"""
        replacements = {
            "from langchain.agents import initialize_agent": 
                "from langchain.agents import create_tool_calling_agent, AgentExecutor",
            "initialize_agent(": "create_tool_calling_agent(",
            "agent_kwargs=": "# agent_kwargs deprecated, use direct parameters",
            "return_intermediate_steps=True": "# Now handled by graph state"
        }
        
        new_code = old_code
        for old, new in replacements.items():
            new_code = new_code.replace(old, new)
        
        return new_code
```

---

## 10. YAML 설정 통합

### supervisor_rules.yaml
```yaml
# Supervisor 실행 규칙
version: "0.6.6"
supervisor:
  name: "Main Supervisor"
  
  query_analysis:
    simple_patterns:
      - "^(what|who|when|where) is"
      - "^tell me about"
      - "^define"
    complex_patterns:
      - "analyze .* and compare"
      - "create .* plan"
      - "evaluate .* options"
    
  routing_rules:
    - condition: "simple_query"
      route_to: "direct_executor"
      max_time: 10
    - condition: "complex_query"
      route_to: "planner"
      max_time: 60
    - condition: "requires_research"
      route_to: "research_agent"
      max_time: 120
  
  error_policies:
    rate_limit:
      strategy: "exponential_backoff"
      initial_delay: 1
      max_delay: 60
      max_retries: 5
    timeout:
      strategy: "retry_with_timeout_increase"
      multiplier: 1.5
      max_attempts: 3
    critical:
      strategy: "immediate_alert"
      notification_channels: ["slack", "email"]
  
  performance:
    enable_caching: true
    cache_ttl: 3600
    parallel_execution: true
    max_workers: 4
```

### 설정 로더
```python
class ConfigLoader:
    @staticmethod
    def load_yaml_config(filepath: str) -> Dict:
        """YAML 설정 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 설정 검증
        ConfigLoader.validate_config(config)
        return config
    
    @staticmethod
    def validate_config(config: Dict):
        """설정 유효성 검증"""
        required_keys = ["version", "supervisor", "query_analysis", "routing_rules"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        # 버전 체크
        if config["version"] != "0.6.6":
            logging.warning(f"Config version mismatch: {config['version']}")
```

---

## 11. 테스트 전략

### 포괄적 테스트 스위트
```python
import pytest
from unittest.mock import Mock, patch

class TestSuite:
    @pytest.fixture
    def sample_state(self):
        """테스트용 상태 픽스처"""
        return {
            "query": "Test query",
            "messages": [],
            "session_id": "test-session",
            "workflow_status": "running",
            "errors": {},
            "retry_attempts": 0,
            "max_retries": 3
        }
    
    def test_node_execution(self, sample_state):
        """노드 실행 테스트"""
        node = AnalyzerNode()
        result = node.execute(sample_state)
        
        assert "complexity" in result
        assert result["workflow_status"] in ["running", "completed", "error"]
    
    def test_error_handling(self, sample_state):
        """에러 처리 테스트"""
        sample_state["errors"] = {"test_node": "Rate limit exceeded"}
        
        handler = ErrorHandler()
        result = handler.handle_error(sample_state)
        
        assert "error_counts" in result
        assert result["error_counts"]["RATE_LIMIT"] == 1
    
    def test_graph_compilation(self):
        """그래프 컴파일 테스트"""
        graph = SupervisorGraph()
        compiled = graph.compile()
        
        assert compiled is not None
        assert hasattr(compiled, 'invoke')
        assert hasattr(compiled, 'stream')
    
    @patch('requests.get')
    def test_tool_execution(self, mock_get):
        """도구 실행 테스트"""
        mock_get.return_value.json.return_value = {"result": "success"}
        
        tool = ToolManager.search_web
        result = tool.invoke({"query": "test"})
        
        assert "success" in result
```

---

## 12. 모니터링 및 옵저버빌리티

### 메트릭 수집
```python
from prometheus_client import Counter, Histogram, Gauge
import time

class MetricsCollector:
    # 메트릭 정의
    node_executions = Counter('langgraph_node_executions_total', 
                             'Total node executions', ['node_name'])
    node_errors = Counter('langgraph_node_errors_total', 
                         'Total node errors', ['node_name', 'error_type'])
    execution_time = Histogram('langgraph_execution_duration_seconds',
                              'Execution duration', ['operation'])
    active_workflows = Gauge('langgraph_active_workflows',
                           'Currently active workflows')
    
    @staticmethod
    def track_node_execution(node_name: str):
        """노드 실행 추적"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                MetricsCollector.node_executions.labels(node_name=node_name).inc()
                MetricsCollector.active_workflows.inc()
                
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_type = type(e).__name__
                    MetricsCollector.node_errors.labels(
                        node_name=node_name, 
                        error_type=error_type
                    ).inc()
                    raise
                finally:
                    duration = time.time() - start
                    MetricsCollector.execution_time.labels(
                        operation=node_name
                    ).observe(duration)
                    MetricsCollector.active_workflows.dec()
            
            return wrapper
        return decorator
```

---

## 13. 보안 고려사항

### 입력 검증 및 새니타이징
```python
import re
from typing import Any

class SecurityManager:
    @staticmethod
    def sanitize_input(user_input: str) -> str:
        """사용자 입력 새니타이징"""
        # SQL 인젝션 방지
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise ValueError("Potentially malicious input detected")
        
        # XSS 방지
        user_input = re.sub(r'<script.*?</script>', '', user_input, flags=re.DOTALL)
        user_input = re.sub(r'<.*?>', '', user_input)
        
        # 길이 제한
        max_length = 1000
        if len(user_input) > max_length:
            user_input = user_input[:max_length]
        
        return user_input
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """API 키 검증"""
        if not api_key:
            return False
        
        # 형식 검증
        if not re.match(r'^sk-[a-zA-Z0-9]{48}$', api_key):
            return False
        
        return True
    
    @staticmethod
    def rate_limit_check(user_id: str, operation: str) -> bool:
        """레이트 리미팅 체크"""
        # Redis를 사용한 레이트 리미팅 구현
        # 예시 코드
        return True
```

---

## 14. 최종 통합 예제

### 완전한 챗봇 구현
```python
class LangGraphChatbot:
    def __init__(self, config_path="supervisor_rules.yaml"):
        # 설정 로드
        self.config = ConfigLoader.load_yaml_config(config_path)
        
        # 디버깅 시스템 초기화
        self.debug_system = DebugSystem(debug_level="INFO")
        
        # 메트릭 수집기 초기화
        self.metrics = MetricsCollector()
        
        # 보안 관리자 초기화
        self.security = SecurityManager()
        
        # 그래프 빌드
        self.graph = self.build_graph()
    
    def build_graph(self) -> CompiledGraph:
        """그래프 구성 및 컴파일"""
        builder = StateGraph(AgentState)
        
        # 노드 추가
        builder.add_node("input_validation", self.validate_input_node)
        builder.add_node("analyzer", self.analyze_node)
        builder.add_node("planner", self.plan_node)
        builder.add_node("executor", self.execute_node)
        builder.add_node("error_handler", ErrorHandler.handle_error)
        builder.add_node("result_formatter", self.format_result_node)
        
        # 엣지 설정
        builder.add_edge(START, "input_validation")
        builder.add_edge("input_validation", "analyzer")
        
        # 조건부 라우팅
        builder.add_conditional_edges(
            "analyzer",
            self.route_by_analysis,
            {
                "simple": "executor",
                "complex": "planner",
                "error": "error_handler"
            }
        )
        
        builder.add_edge("planner", "executor")
        builder.add_edge("executor", "result_formatter")
        builder.add_edge("error_handler", "result_formatter")
        builder.add_edge("result_formatter", END)
        
        # 체크포인터 설정
        checkpointer = CheckpointManager.setup_checkpointer("sqlite")
        
        # 컴파일
        return builder.compile(checkpointer=checkpointer)
    
    @MetricsCollector.track_node_execution("input_validation")
    def validate_input_node(self, state: AgentState) -> Dict:
        """입력 검증 노드"""
        try:
            query = state.get("query", "")
            sanitized = self.security.sanitize_input(query)
            return {"query": sanitized, "validation_status": "passed"}
        except ValueError as e:
            return {"errors": {"validation": str(e)}, "workflow_status": "failed"}
    
    def run(self, user_input: str, user_id: str = None) -> Dict:
        """챗봇 실행"""
        # 초기 상태 생성
        initial_state = {
            "query": user_input,
            "user_id": user_id or "anonymous",
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "messages": [HumanMessage(content=user_input)],
            "workflow_status": "running",
            "errors": {},
            "retry_attempts": 0,
            "max_retries": 3
        }
        
        # 그래프 실행
        try:
            # 스트리밍 실행
            for step in self.graph.stream(initial_state):
                logging.info(f"Step completed: {step}")
                
                # 중간 결과 처리
                if "errors" in step and step["errors"]:
                    logging.error(f"Error in step: {step['errors']}")
            
            # 최종 결과 반환
            final_state = self.graph.invoke(initial_state)
            return final_state
            
        except Exception as e:
            logging.error(f"Chatbot execution failed: {str(e)}")
            return {
                "error": str(e),
                "workflow_status": "failed"
            }

# 사용 예시
if __name__ == "__main__":
    # 챗봇 초기화
    chatbot = LangGraphChatbot()
    
    # 실행
    result = chatbot.run(
        user_input="분기별 매출 보고서를 작성하고 전년 대비 성장률을 분석해줘",
        user_id="user123"
    )
    
    print(f"Result: {result}")
```

---

## 결론

이 가이드라인은 LangGraph 0.6.6을 사용한 프로덕션 레벨 챗봇 개발에 필요한 모든 핵심 요소를 다룹니다:

✅ **완전한 에러 처리** - 모든 예외 상황 대비
✅ **버전 호환성** - 0.2.x → 0.6.x 마이그레이션 지원
✅ **프로덕션 준비** - 모니터링, 로깅, 메트릭
✅ **보안** - 입력 검증, 레이트 리미팅
✅ **확장성** - 계층적 구조, 병렬 처리
✅ **디버깅** - LangSmith 통합, 상세 로깅
✅ **테스트** - 포괄적 테스트 전략

이 문서를 rules.md와 manual.md로 분리하여 사용하시면, Claude Desktop의 구버전 데이터로 인한 오류를 최소화하고 안정적인 챗봇을 개발할 수 있습니다.
