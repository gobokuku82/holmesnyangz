"""
Pytest Configuration and Fixtures
테스트 설정 및 공통 픽스처
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import logging

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)


# === 이벤트 루프 설정 ===

@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# === Mock LLM ===

@pytest.fixture
def mock_llm():
    """Mock Language Model"""
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value=Mock(content="Mock response"))
    return llm


@pytest.fixture
def mock_llm_with_json():
    """JSON 응답을 반환하는 Mock LLM"""
    llm = Mock()
    llm.ainvoke = AsyncMock(return_value=Mock(
        content='{"result": "success", "data": "test"}'
    ))
    return llm


# === Mock 에이전트 ===

@pytest.fixture
def mock_agent():
    """Mock Agent"""
    agent = Mock()
    agent.execute = AsyncMock(return_value={
        "success": True,
        "content": "Mock agent result"
    })
    agent.analyze = AsyncMock(return_value={
        "intent": "test",
        "entities": {},
        "confidence": 0.9
    })
    agent.plan = AsyncMock(return_value={
        "steps": ["step1"],
        "agents": ["agent1"],
        "strategy": "sequential"
    })
    return agent


# === Mock 워크플로우 엔진 ===

@pytest.fixture
def mock_engine():
    """Mock Workflow Engine"""
    from backend.core.workflow_engine import AsyncWorkflowEngine
    
    engine = Mock(spec=AsyncWorkflowEngine)
    engine.execute = AsyncMock(return_value={
        "final_response": "Test response",
        "workflow_status": "completed",
        "metrics": {
            "thread_id": "test_thread",
            "execution_time": 1.0,
            "agents_called": 1,
            "confidence": 0.9
        }
    })
    engine.get_state = AsyncMock(return_value={
        "query": "test",
        "messages": []
    })
    engine.list_threads = AsyncMock(return_value=[])
    engine.delete_thread = AsyncMock(return_value=True)
    engine.close = AsyncMock()
    
    # Context 추가
    engine.context = Mock(
        user_id="test_user",
        session_id="test_session",
        available_agents=["analyzer_agent", "price_search_agent"],
        features={"enable_memory": True}
    )
    
    return engine


# === 테스트 데이터 ===

@pytest.fixture
def sample_query():
    """샘플 쿼리"""
    return "강남구 아파트 시세가 어떻게 되나요?"


@pytest.fixture
def sample_entities():
    """샘플 엔티티"""
    return {
        "location": "강남구",
        "property_type": "아파트"
    }


@pytest.fixture
def sample_state():
    """샘플 상태"""
    from backend.core.state import create_initial_state
    state = create_initial_state("테스트 쿼리")
    state["intent"] = "price_inquiry"
    state["entities"] = {"location": "강남구"}
    return state


# === 테스트 컨텍스트 ===

@pytest.fixture
def test_context():
    """테스트용 컨텍스트"""
    from backend.core.context import ContextFactory
    return ContextFactory.create_for_testing()


@pytest.fixture
def user_context():
    """사용자 컨텍스트"""
    from backend.core.context import ContextFactory
    return ContextFactory.create_for_user(
        user_id="test_user",
        user_name="Test User"
    )


# === 환경 설정 ===

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """테스트 환경 설정"""
    # 환경 변수 설정
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    
    # CORS 설정
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')
    
    yield
    
    # 정리 작업
    # 필요시 추가


# === 데이터베이스 모킹 ===

@pytest.fixture
async def mock_db():
    """Mock Database Connection"""
    db = Mock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock(return_value=None)
    db.fetch_all = AsyncMock(return_value=[])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


# === 캐시 모킹 ===

@pytest.fixture
def mock_cache():
    """Mock Cache"""
    cache = Mock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    return cache


# === HTTP 클라이언트 모킹 ===

@pytest.fixture
def mock_http_client():
    """Mock HTTP Client"""
    client = Mock()
    client.get = AsyncMock(return_value=Mock(
        status_code=200,
        json=lambda: {"status": "success"}
    ))
    client.post = AsyncMock(return_value=Mock(
        status_code=200,
        json=lambda: {"result": "created"}
    ))
    return client


# === 파일 시스템 모킹 ===

@pytest.fixture
def temp_dir(tmp_path):
    """임시 디렉토리"""
    return tmp_path


@pytest.fixture
def mock_file_content():
    """Mock 파일 내용"""
    return """
    # Test Configuration
    test_key: test_value
    agents:
      - name: test_agent
        enabled: true
    """


# === 테스트 마커 ===

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async"
    )


# === 테스트 헬퍼 함수 ===

def assert_success_response(response):
    """성공 응답 검증"""
    assert response.get("success") == True
    assert "error" not in response


def assert_error_response(response):
    """에러 응답 검증"""
    assert response.get("success") == False or "error" in response


async def wait_for_condition(condition_func, timeout=5, interval=0.1):
    """조건이 충족될 때까지 대기"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False