# 부동산 챗봇 백엔드 (Real Estate Chatbot Backend)

## 프로젝트 개요
LangGraph 0.6.6 기반의 부동산 전문 AI 챗봇 백엔드 시스템입니다. FastAPI를 사용하여 구축되었으며, 다양한 전문 에이전트들이 협업하여 부동산 관련 질문에 답변합니다.

## 기술 스택
- **Framework**: FastAPI, Uvicorn
- **AI/ML**: LangGraph 0.6.6, LangChain 0.3.0+
- **LLM**: Anthropic Claude, OpenAI GPT
- **Vector DB**: ChromaDB
- **Embeddings**: HuggingFace (sentence-transformers)
- **WebSocket**: 실시간 통신 지원

## 프로젝트 구조
```
backend/
├── agents/              # 전문 에이전트 모듈
│   ├── base_agent.py       # 기본 에이전트 클래스
│   ├── supervisor_agent.py # 감독 에이전트
│   ├── analyzer_agent.py   # 분석 에이전트
│   ├── finance_agent.py    # 금융 에이전트
│   ├── legal_agent.py      # 법률 에이전트
│   ├── location_agent.py   # 지역 정보 에이전트
│   ├── planner_agent.py    # 계획 수립 에이전트
│   └── price_search_agent.py # 가격 검색 에이전트
├── api/                 # API 엔드포인트
│   ├── models.py           # Pydantic 모델
│   └── routes.py           # API 라우트
├── config/              # 설정 관리
│   ├── config_loader.py    # 설정 로더
│   └── settings.py         # 환경 설정
├── core/                # 핵심 모듈
│   ├── workflow_engine.py  # 워크플로우 엔진
│   ├── graph_builder.py    # 그래프 빌더
│   ├── state.py            # 상태 관리
│   ├── context.py          # 컨텍스트 관리
│   ├── error_handlers.py   # 에러 처리
│   └── logging_config.py   # 로깅 설정
├── tools/               # 도구 모듈
│   ├── finance_tools.py    # 금융 도구
│   ├── legal_tools.py      # 법률 도구
│   ├── location_tools.py   # 지역 정보 도구
│   └── price_tools.py      # 가격 검색 도구
├── tests/               # 테스트
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_workflow.py
│   └── test_integration.py
└── main.py             # 메인 애플리케이션

```

## 주요 기능

### 1. 멀티 에이전트 시스템
- **Supervisor Agent**: 사용자 요청을 분석하고 적절한 에이전트에게 작업 할당
- **Analyzer Agent**: 부동산 데이터 분석 및 인사이트 제공
- **Finance Agent**: 대출, 금융 계산 및 투자 분석
- **Legal Agent**: 부동산 법률 정보 및 계약 관련 안내
- **Location Agent**: 지역 정보, 교통, 편의시설 정보 제공
- **Price Search Agent**: 부동산 가격 검색 및 비교
- **Planner Agent**: 부동산 구매/임대 계획 수립

### 2. 실시간 통신
- WebSocket을 통한 실시간 메시지 스트리밍
- 세션별 독립적인 워크플로우 엔진 관리
- 비동기 메시지 처리

### 3. 워크플로우 엔진
- LangGraph 기반 상태 관리
- 동적 에이전트 라우팅
- 컨텍스트 유지 및 대화 히스토리 관리

## 설치 방법

### 1. Python 환경 설정
```bash
# Python 3.12 권장
python --version

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. 의존성 설치
```bash
# 프로젝트 루트 디렉토리에서 실행
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 프로젝트 루트에 생성:
```env
# LLM API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# CORS Settings
CORS_ORIGINS=["http://localhost:3000"]
```

## 실행 방법

### 개발 서버 실행
```bash
# 프로젝트 루트 디렉토리에서
cd backend
python main.py
```

또는 uvicorn 직접 실행:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 서버 실행
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 엔드포인트

### REST API
- `GET /health` - 서버 상태 확인
- `POST /api/chat` - 동기 채팅 요청
- `GET /api/sessions/{session_id}` - 세션 정보 조회

### WebSocket
- `ws://localhost:8000/ws/{session_id}` - 실시간 채팅 연결

WebSocket 메시지 형식:
```json
{
  "type": "user_message | agent_message | system | error",
  "content": "메시지 내용",
  "metadata": {
    "agent": "agent_name",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

## 테스트

### 단위 테스트 실행
```bash
pytest backend/tests/test_agents.py
pytest backend/tests/test_tools.py
```

### 통합 테스트
```bash
pytest backend/tests/test_integration.py
```

### 전체 테스트
```bash
pytest backend/tests/ -v
```

## 개발 가이드

### 새로운 에이전트 추가
1. `backend/agents/` 디렉토리에 새 에이전트 파일 생성
2. `BaseAgent` 클래스 상속
3. `process()` 메서드 구현
4. `supervisor_agent.py`에 라우팅 로직 추가

### 새로운 도구 추가
1. `backend/tools/` 디렉토리에 도구 파일 생성
2. LangChain Tool 형식으로 구현
3. 해당 에이전트에서 도구 임포트 및 사용

## 로깅
- 로그는 `logs/` 디렉토리에 저장됨
- 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
- 일별 로그 파일 자동 생성

## 트러블슈팅

### 포트 충돌
```bash
# 8000 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000

# 다른 포트로 실행
python main.py --port 8001
```

### 메모리 부족
- ChromaDB 캐시 정리: `rm -rf .chroma/`
- 워커 수 조정: `--workers 2`

## 라이선스
MIT License