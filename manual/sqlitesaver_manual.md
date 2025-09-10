# LangGraph 0.6+ `SqliteSaver` 매뉴얼

## 1. 소개

`SqliteSaver`는 체크포인트를 SQLite 데이터베이스에 저장할 수 있는 **경량 동기식(checkpoint saver)** 클래스입니다.  
데모나 소규모 프로젝트 용도로 설계되었으며, 여러 스레드에 확장하기에는 적합하지 않습니다.  
비동기 버전은 `AsyncSqliteSaver`를 참고하세요.

---

## 2. 설치

`SqliteSaver`는 별도 라이브러리인 `langgraph-checkpoint-sqlite`에 포함되어 있습니다.

```bash
pip install langgraph-checkpoint-sqlite
```

---

## 3. Import 경로

LangGraph 0.6 이상에서는 공식적으로 다음과 같이 import 합니다:

```python
from langgraph.checkpoint.sqlite import SqliteSaver
```

잘못된 예시는 다음과 같습니다:

```python
# ❌ 존재하지 않는 패키지 경로
from langgraph_checkpoint_sqlite import SqliteSaver
```

---

## 4. 사용 예시 (동기식)

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# SQLite 연결
conn = sqlite3.connect("checkpoints.sqlite")
memory = SqliteSaver(conn)

# 그래프 정의
builder = StateGraph(int)
builder.add_node("add_one", lambda x: x + 1)
builder.set_entry_point("add_one")
builder.set_finish_point("add_one")

# 그래프 컴파일
graph = builder.compile(checkpointer=memory)

# 실행 및 상태 조회
config = {"configurable": {"thread_id": "1"}}
result = graph.invoke(3, config)
state = graph.get_state(config)
```

---

## 5. `from_conn_string` 팩토리 메서드

`SqliteSaver`는 `from_conn_string()` 팩토리 메서드를 제공합니다.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    # 체크포인트 저장
    checkpointer.put(write_config, checkpoint, {}, {})
    # 체크포인트 조회
    checkpointer.get(read_config)
    # 리스트 확인
    list(checkpointer.list(read_config))
```

비동기 버전인 `AsyncSqliteSaver`도 동일하게 사용할 수 있습니다.

---

## 6. 버전별 주의 사항

- LangGraph **v0.2~0.2.1** 시점에는 `SqliteSaver` 관련 import 문제가 보고됨.  
- v0.6 이상에서는 `langgraph.checkpoint.sqlite` 경로가 정상 작동함.

---

## 7. 요약 표

| 항목             | 설명 |
|------------------|------|
| 클래스 이름       | `SqliteSaver` (동기식), `AsyncSqliteSaver` (비동기식) |
| 설치 패키지       | `langgraph-checkpoint-sqlite` |
| Import 경로       | `from langgraph.checkpoint.sqlite import SqliteSaver` |
| 연결 생성 방법    | `SqliteSaver(conn)` 또는 `SqliteSaver.from_conn_string(":memory:")` |
| 주요 기능         | 체크포인트 저장/조회/리스트, `thread_id` 기반 persistence |
| 종속성 조건       | LangGraph v0.6 이상 |
| 주의사항          | 다중 스레드 환경에는 부적합, 필요시 `AsyncSqliteSaver` 고려 |

---

## 8. 참고

- [LangGraph GitHub Discussions](https://github.com/langchain-ai/langgraph/discussions/3707)
- [PyPI: langgraph-checkpoint-sqlite](https://pypi.org/project/langgraph-checkpoint-sqlite/)
- [LangChain Blog: LangGraph v0.2](https://blog.langchain.com/langgraph-v0-2/)

