# LangGraph 0.6.6: `SqliteSaver` vs `AsyncSqliteSaver` 매뉴얼

## 1. 패키지 설치
두 클래스 모두 `langgraph-checkpoint-sqlite` 패키지에 포함되어 있으며, 별도로 설치해야 합니다.

```bash
pip install langgraph-checkpoint-sqlite
```

---

## 2. 클래스 개요

| 클래스 | 설명 |
|--------|------|
| **SqliteSaver** | 동기식 체크포인트 저장소. SQLite DB에 상태 저장. `sqlite3` 사용. 데모나 소규모 프로젝트에 적합. 멀티스레드에는 부적합. |
| **AsyncSqliteSaver** | 비동기식 체크포인트 저장소. `aiosqlite` 기반. `async/await` 사용. 비동기 환경(예: FastAPI)에서 효율적. |

---

## 3. 제공 기능 (공통 인터페이스)
두 클래스는 모두 `BaseCheckpointSaver` 인터페이스를 따르며 지원하는 메서드는 다음과 같습니다:  

- 동기식: `.put`, `.get_tuple`, `.list`, `.put_writes`, `.delete_thread`  
- 비동기식: `.aput`, `.aget_tuple`, `.alist`, `.aput_writes`, `.adelete_thread`, `.aget`  

즉, `AsyncSqliteSaver`는 같은 기능을 비동기적으로 제공합니다.

---

## 4. `SqliteSaver` 사용 예시 (동기식)

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# DB 연결 (check_same_thread=False 가능)
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
checkpointer = SqliteSaver(conn)

builder = StateGraph(int)
builder.add_node("add_one", lambda x: x + 1)
builder.set_entry_point("add_one")
builder.set_finish_point("add_one")

graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}
graph.get_state(config)
result = graph.invoke(3, config)
graph.get_state(config)
```

- `from_conn_string()` 클래스 메서드를 제공해, 커넥션 문자열만으로 생성 가능.

---

## 5. `AsyncSqliteSaver` 사용 예시 (비동기식)

```python
import asyncio
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as saver:
        builder = StateGraph(int)
        builder.add_node("add_one", lambda x: x + 1)
        builder.set_entry_point("add_one")
        builder.set_finish_point("add_one")

        graph = builder.compile(checkpointer=saver)

        result = await graph.ainvoke(1, {"configurable": {"thread_id": "thread-1"}})
        print(result)

asyncio.run(main())
```

- `from_conn_string()` 클래스 메서드를 비동기 컨텍스트 매니저로 제공.  
- `await saver.aput(...)`, `await saver.aget(...)`, `async for … in saver.alist(...)` 형태의 사용 가능.  
- SQLite의 I/O 성능 한계로, **프로덕션 환경에서는 PostgresSaver 같은 더 강력한 체크포인터 추천**.

---

## 6. 비교 요약

| 항목                      | SqliteSaver (동기식) | AsyncSqliteSaver (비동기식) |
|---------------------------|----------------------|-----------------------------|
| I/O 방식                 | 동기 (blocking)       | 비동기 (async/await)        |
| 사용 모듈                | `sqlite3`             | `aiosqlite`                 |
| 생성 방법                | `SqliteSaver(conn)` 또는 `.from_conn_string()` | `async with AsyncSqliteSaver.from_conn_string()` |
| 주요 메서드              | `put`, `get`, `list`, etc. | `aput`, `aget`, `alist`, etc. |
| 사용 환경                | 간단한 테스트, 데모    | FastAPI, 비동기 서버 환경   |
| 장점                    | 구현 단순, 직관적      | 높은 동시 처리 성능          |
| 단점                    | 멀티 스레드/비동기 서버에 부적합 | 코드 복잡도↑, sqlite 성능 제약 존재 |
| 추천 사용 사례           | 간단한 스크립트, 로컬 실행 | 비동기 웹 서비스, 챗봇, 고성능 API 등 |

---

## 7. 참고 문서

- [LangGraph Persistence Docs](https://langchain-ai.github.io/langgraph/concepts/persistence/)  
- [LangGraph Checkpoints Reference](https://langchain-ai.github.io/langgraph/reference/checkpoints/)  
- [PyPI: langgraph-checkpoint-sqlite](https://pypi.org/project/langgraph-checkpoint-sqlite/)

---

## 8. 주의사항

- **SqliteSaver** → 동기식, 직관적. 로컬 데모용.  
- **AsyncSqliteSaver** → 비동기식, 고성능 서버에 적합.  
- 두 클래스 모두 SQLite 성능 한계가 있으므로, 실제 운영 환경에서는 PostgresSaver 등 다른 체크포인터 고려 필요.  
