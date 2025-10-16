# WebSocket 403 Forbidden 에러 근본 원인 분석 및 수정 계획

**작성일**: 2025-10-16
**상태**: 분석 완료 - 실행 대기
**문제**: 프론트엔드가 "세션을 초기화하는 중..."에서 멈춤, WebSocket 403 Forbidden

---

## 📋 Executive Summary

### 문제 상황
- **증상**: 프론트엔드 무한 로딩 ("세션을 초기화하는 중...")
- **백엔드 로그**: `WebSocket rejected: invalid session session-xxx (403 Forbidden)`
- **근본 원인**: `validate_session()` 메서드가 `None`을 반환 (True/False 대신)

### 발견된 원인
1. ~~`postgres_session_manager.py`의 `validate_session()` 메서드 버그~~ ✅ **이미 수정됨**
2. **실제 문제**: 서버 리로드 타이밍 문제로 수정 전 코드 실행
3. **추가 잠재적 문제**: DB 연결 에러 가능성

---

## 🔍 1. 근본 원인 분석

### 1-1. 로그 분석 (사용자 제공)

```
2025-10-16 09:23:13 - Session created (PostgreSQL): session-92383112... ✅
2025-10-16 09:23:15 - 🔍 [DEBUG] Attempting to validate WebSocket session: session-92383112...
2025-10-16 09:23:15 - 🔍 [DEBUG] Validation result: None ❌ (Should be True/False!)
2025-10-16 09:23:15 - 🔍 [DEBUG] Direct DB check: FOUND ✅ (DB에는 존재함!)
2025-10-16 09:23:15 - WebSocket rejected: invalid session session-92383112... (403)
WARNING: WatchFiles detected changes in 'chat_api.py'. Reloading... ⚠️ (파일 수정 감지)
2025-10-16 09:28:46 - Server reloaded ✅ (새 코드 적용)
```

**핵심 문제**:
1. `validate_session()`이 **None** 반환 (True/False가 아님!)
2. `if not validation_result:` → `if not None:` → `True` → 연결 거부
3. DB에는 세션이 **실제로 존재**하는데도 검증 실패

### 1-2. 코드 분석

#### 문제의 코드 (수정 전 - 09:23:15 실행 시점)

**파일**: `postgres_session_manager.py` Line 89-128

```python
async def validate_session(self, session_id: str) -> bool:
    async for db_session in get_async_db():
        try:
            # 세션 조회
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return False  # ❌ 문제: finally:break 때문에 실행 안됨

            # updated_at 갱신
            await db_session.execute(...)
            await db_session.commit()

            return True  # ❌ 문제: finally:break 때문에 실행 안됨

        except Exception as e:
            return False  # ❌ 문제: finally:break 때문에 실행 안됨
        finally:
            break  # ⚠️ 문제의 원인: generator 종료 전에 break

    # ❌ 여기에 도달하면 return 문이 없음 → None 반환!
```

**왜 None이 반환되는가?**

Python의 `finally` 블록은 `try` 또는 `except` 블록이 **완료되기 전**에 실행됩니다.
따라서:

1. `try` 블록에서 `return True` 시도
2. `finally` 블록 실행 → `break` 실행 → generator 종료
3. `return True`가 **실행되지 않음**
4. 함수 끝에 도달 → **암시적 `return None`**

#### 수정된 코드 (현재 파일 상태)

**파일**: `postgres_session_manager.py` Line 89-128 (수정됨)

```python
async def validate_session(self, session_id: str) -> bool:
    result_value = False  # ✅ 기본값 설정
    async for db_session in get_async_db():
        try:
            # 세션 조회
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"Session not found: {session_id}")
                result_value = False  # ✅ 변수에 저장
            else:
                # updated_at 갱신
                await db_session.execute(
                    update(ChatSession)
                    .where(ChatSession.session_id == session_id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
                await db_session.commit()

                logger.debug(f"Session validated: {session_id}")
                result_value = True  # ✅ 변수에 저장

        except Exception as e:
            logger.error(f"Failed to validate session: {e}")
            result_value = False  # ✅ 변수에 저장
        finally:
            break  # generator 종료

    return result_value  # ✅ finally 이후에 반환
```

**수정 포인트**:
1. `result_value` 변수 사용 (finally 블록 이전에 값 저장)
2. `finally: break` 이후에 `return result_value` 실행
3. **이제 항상 True 또는 False 반환**

---

### 1-3. 왜 여전히 문제가 발생했는가?

**타임라인 분석**:

| 시각 | 이벤트 | 파일 상태 |
|------|--------|----------|
| 09:23:13 | POST /start 성공 (세션 생성) | 수정 전 코드 |
| 09:23:15 | WebSocket 연결 시도 | 수정 전 코드 |
| 09:23:15 | `validate_session()` 실행 → `None` 반환 | 수정 전 코드 |
| 09:23:15 | 403 Forbidden | 수정 전 코드 |
| 09:23:15 | **WatchFiles detected changes** | **파일 수정됨** |
| 09:28:46 | **Server reloaded** | **수정 후 코드** |

**결론**: 파일은 이미 수정되었지만, **서버가 재시작되기 전**에는 여전히 **수정 전 코드가 메모리에 로드**되어 있었습니다.

---

## 🔧 2. 해결 방안

### Option 1: 서버 재시작 (가장 간단)

**단계**:
1. 백엔드 서버 재시작 (Ctrl+C → `uvicorn app.main:app --reload`)
2. 프론트엔드 새로고침 (F5)
3. 정상 작동 확인

**예상 결과**:
```
✅ Session created (PostgreSQL): session-xxx
🔍 Validating WebSocket session: session-xxx
🔍 Validation result: True  # ← None이 아니라 True!
✅ Session validated: session-xxx
WebSocket connection accepted (101 Switching Protocols)
```

---

### Option 2: 검증 강화 (안전성 확보)

현재 코드가 수정되었지만, **다른 메서드들**도 같은 패턴을 사용하고 있습니다.

#### 2-1. 같은 패턴을 사용하는 메서드들

**파일**: `postgres_session_manager.py`

| 메서드 | 라인 | 반환 타입 | 문제 여부 |
|--------|------|----------|----------|
| `create_session()` | 38-87 | `Tuple[str, datetime]` | ⚠️ 검토 필요 |
| `validate_session()` | 89-128 | `bool` | ✅ 수정됨 |
| `get_session()` | 130-164 | `Optional[Dict]` | ⚠️ 검토 필요 |
| `delete_session()` | 165-203 | `bool` | ⚠️ 검토 필요 |
| `cleanup_expired_sessions()` | 234-278 | `int` | ⚠️ 검토 필요 |
| `get_active_session_count()` | 280-304 | `int` | ⚠️ 검토 필요 |
| `extend_session()` | 306-338 | `bool` | ⚠️ 검토 필요 |

#### 2-2. `get_session()` 메서드 검토

**현재 코드** (Line 130-164):
```python
async def get_session(self, session_id: str) -> Optional[Dict]:
    async for db_session in get_async_db():
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                return None  # ❌ finally:break 때문에 실행 안될 가능성

            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "expires_at": session.created_at + self.session_ttl
            }  # ❌ finally:break 때문에 실행 안될 가능성

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None  # ❌ finally:break 때문에 실행 안될 가능성
        finally:
            break
    # ⚠️ 여기에 도달하면 return None (명시적 필요)
```

**문제**: `return` 문이 `finally: break` 이전에 있어서 **실행되지 않을 가능성** 있음

**수정 방안**:
```python
async def get_session(self, session_id: str) -> Optional[Dict]:
    result_value = None  # ✅ 기본값
    async for db_session in get_async_db():
        try:
            query = select(ChatSession).where(ChatSession.session_id == session_id)
            result = await db_session.execute(query)
            session = result.scalar_one_or_none()

            if not session:
                result_value = None
            else:
                result_value = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "title": session.title,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "expires_at": session.created_at + self.session_ttl
                }

        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            result_value = None
        finally:
            break

    return result_value  # ✅ finally 이후 반환
```

---

#### 2-3. 모든 메서드 패턴 통일

**수정 원칙**:
1. **모든 메서드에 `result_value` 변수 사용**
2. **`finally: break` 이전에 변수에 값 저장**
3. **`finally` 이후에 `return result_value`**

**수정 대상 메서드**:
- `create_session()` - Line 38-87
- `get_session()` - Line 130-164
- `delete_session()` - Line 165-203
- `cleanup_expired_sessions()` - Line 234-278
- `get_active_session_count()` - Line 280-304
- `extend_session()` - Line 306-338

**예상 작업 시간**: 약 15분

---

### Option 3: DB 연결 검증 추가 (디버깅 강화)

현재 `validate_session()`은 DB 조회 실패 시 로그만 남깁니다.
더 명확한 에러 메시지를 추가하면 향후 문제 진단이 쉬워집니다.

**수정 방안**:
```python
async def validate_session(self, session_id: str) -> bool:
    result_value = False

    try:
        async for db_session in get_async_db():
            try:
                # DB 연결 확인
                await db_session.execute("SELECT 1")
                logger.debug(f"DB connection OK for session validation")

                # 세션 조회
                query = select(ChatSession).where(ChatSession.session_id == session_id)
                result = await db_session.execute(query)
                session = result.scalar_one_or_none()

                if not session:
                    logger.warning(f"Session not found in DB: {session_id}")
                    result_value = False
                else:
                    # updated_at 갱신
                    await db_session.execute(
                        update(ChatSession)
                        .where(ChatSession.session_id == session_id)
                        .values(updated_at=datetime.now(timezone.utc))
                    )
                    await db_session.commit()

                    logger.debug(f"Session validated: {session_id}")
                    result_value = True

            except Exception as e:
                logger.error(f"Failed to validate session (DB error): {e}", exc_info=True)
                result_value = False
            finally:
                break
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}", exc_info=True)
        result_value = False

    logger.debug(f"validate_session() returning: {result_value} (type: {type(result_value)})")
    return result_value
```

**추가된 검증**:
1. `SELECT 1` - DB 연결 확인
2. 더 자세한 로그 메시지
3. 반환값 타입 로깅 (`None` vs `bool` 구분)

---

## 📊 3. 실행 계획

### Phase 0: 즉시 테스트 (서버 재시작)

**목표**: 현재 수정된 코드가 정상 작동하는지 확인

**단계**:
1. 백엔드 서버 재시작
   ```bash
   # 터미널에서 Ctrl+C
   uvicorn app.main:app --reload
   ```

2. 프론트엔드 새로고침 (F5)

3. 로그 확인
   ```
   예상 로그:
   ✅ Session created (PostgreSQL): session-xxx
   🔍 Validating WebSocket session: session-xxx
   🔍 Validation result: True  # ← 이제 True!
   ✅ Session validated: session-xxx
   INFO: ('127.0.0.1', xxxxx) - "WebSocket /api/v1/chat/ws/session-xxx" 101
   ```

**예상 결과**: 정상 작동 (90% 확률)

---

### Phase 1: 안전성 강화 (권장)

**목표**: 다른 메서드들도 같은 패턴으로 수정

**파일**: `backend/app/api/postgres_session_manager.py`

**수정 대상**:
1. ✅ `validate_session()` (이미 수정됨)
2. ⚠️ `create_session()` Line 38-87
3. ⚠️ `get_session()` Line 130-164
4. ⚠️ `delete_session()` Line 165-203
5. ⚠️ `cleanup_expired_sessions()` Line 234-278
6. ⚠️ `get_active_session_count()` Line 280-304
7. ⚠️ `extend_session()` Line 306-338

**수정 패턴** (모든 메서드 동일):
```python
async def method_name(...) -> ReturnType:
    result_value = default_value  # ✅ 1. 기본값 설정

    async for db_session in get_async_db():
        try:
            # ... 로직 ...
            result_value = calculated_value  # ✅ 2. 변수에 저장
        except Exception as e:
            result_value = error_value  # ✅ 3. 에러 시 값 저장
        finally:
            break

    return result_value  # ✅ 4. finally 이후 반환
```

**예상 작업 시간**: 15-20분

---

### Phase 2: 디버깅 로그 정리

**목표**: 디버깅 로그 제거 또는 레벨 조정

**파일**: `backend/app/api/chat_api.py` Line 210-221

**현재 코드**:
```python
# 1. 세션 검증
logger.info(f"🔍 Validating WebSocket session: {session_id}")

validation_result = await session_mgr.validate_session(session_id)
logger.info(f"🔍 Validation result: {validation_result}")

if not validation_result:
    await websocket.close(code=4004, reason="Session not found or expired")
    logger.warning(f"WebSocket rejected: invalid session {session_id}")
    return

logger.info(f"✅ Session validated: {session_id}")
```

**수정 방안**:
```python
# 1. 세션 검증
validation_result = await session_mgr.validate_session(session_id)

if not validation_result:
    await websocket.close(code=4004, reason="Session not found or expired")
    logger.warning(f"WebSocket rejected: invalid session {session_id}")
    return

logger.debug(f"Session validated: {session_id}")
```

**변경 사항**:
1. `logger.info` → `logger.debug` (상세 로그는 debug 레벨로)
2. 이모지 제거 (프로덕션 환경에서는 불필요)
3. 핵심 로그만 유지

---

## 🧪 4. 테스트 시나리오

### Test Case 1: 정상 세션 생성 및 WebSocket 연결

**단계**:
1. 프론트엔드 페이지 열기
2. "세션을 초기화하는 중..." 확인
3. 로딩 완료 후 채팅 인터페이스 표시 확인

**예상 로그** (백엔드):
```
✅ Session created (PostgreSQL): session-abc123
🔍 Validating WebSocket session: session-abc123
🔍 Validation result: True
✅ Session validated: session-abc123
INFO: ('127.0.0.1', 12345) - "WebSocket /api/v1/chat/ws/session-abc123" 101
```

**예상 결과**: ✅ 성공

---

### Test Case 2: 만료된 세션 처리

**단계**:
1. sessionStorage에서 `holmes_session_id` 수동 설정 (존재하지 않는 세션 ID)
2. 페이지 새로고침

**예상 로그** (백엔드):
```
⚠️ Session expired or invalid
🔄 Creating new session...
✅ Session created (PostgreSQL): session-xyz789
✅ Session validated: session-xyz789
```

**예상 결과**: ✅ 자동으로 새 세션 생성

---

### Test Case 3: DB 연결 실패 시뮬레이션

**단계**:
1. PostgreSQL 서버 중지
2. 프론트엔드 페이지 열기

**예상 로그** (백엔드):
```
❌ Failed to create session: (DB connection error)
```

**예상 결과**: ❌ 프론트엔드에 에러 메시지 표시

---

## 🚨 5. 리스크 및 대응

### Risk 1: 서버 재시작 후에도 여전히 403 에러

**원인 가능성**:
1. DB에 세션이 실제로 없음
2. DB 연결 실패
3. 타임존 문제 (created_at vs updated_at)

**대응 방안**:
```sql
-- PostgreSQL에서 직접 확인
SELECT session_id, user_id, title, created_at, updated_at
FROM chat_sessions
ORDER BY created_at DESC
LIMIT 5;
```

---

### Risk 2: `get_session()` 메서드가 None 반환

**원인**: `get_session()`도 같은 패턴 사용

**영향**:
- `chat_api.py` Line 122-136: 세션 정보 조회 실패
- `chat_api.py` Line 160-162: user_id 추출 실패

**대응 방안**: Phase 1 실행 (모든 메서드 수정)

---

### Risk 3: 프론트엔드가 잘못된 session_id 전송

**원인**: `use-session.ts`의 세션 검증 로직 문제

**확인 방법**:
```javascript
// 브라우저 콘솔 (F12)
console.log(sessionStorage.getItem('holmes_session_id'))
```

**대응 방안**: sessionStorage 초기화
```javascript
sessionStorage.removeItem('holmes_session_id')
location.reload()
```

---

## 📝 6. 체크리스트

### Phase 0: 즉시 테스트
- [ ] 백엔드 서버 재시작 (Ctrl+C → `uvicorn app.main:app --reload`)
- [ ] 프론트엔드 새로고침 (F5)
- [ ] 로그 확인 (`Validation result: True` 확인)
- [ ] WebSocket 연결 성공 확인 (101 Switching Protocols)
- [ ] 채팅 인터페이스 정상 표시 확인

### Phase 1: 안전성 강화 (권장)
- [ ] `get_session()` 메서드 수정
- [ ] `delete_session()` 메서드 수정
- [ ] `cleanup_expired_sessions()` 메서드 수정
- [ ] `get_active_session_count()` 메서드 수정
- [ ] `extend_session()` 메서드 수정
- [ ] `create_session()` 메서드 검토 (이미 `result` 변수 사용 중)
- [ ] 모든 메서드 테스트

### Phase 2: 디버깅 로그 정리
- [ ] `chat_api.py` 디버깅 로그 레벨 조정
- [ ] `postgres_session_manager.py` 로그 레벨 조정
- [ ] 불필요한 이모지 제거

---

## 💡 7. 추가 개선 사항 (선택)

### 7-1. DB 연결 풀 모니터링

**목적**: DB 연결 문제 조기 발견

**구현**:
```python
# postgres_session_manager.py
async def health_check(self) -> bool:
    """DB 연결 상태 확인"""
    try:
        async for db_session in get_async_db():
            await db_session.execute("SELECT 1")
            logger.info("DB health check OK")
            return True
    except Exception as e:
        logger.error(f"DB health check FAILED: {e}")
        return False
```

---

### 7-2. 세션 TTL 자동 연장

**목적**: 활성 사용자의 세션 자동 갱신

**구현**:
```python
# validate_session()에서 자동 연장
if session and (datetime.now(timezone.utc) - session.updated_at).seconds > 600:
    # 10분 이상 경과 시 TTL 연장
    await self.extend_session(session_id)
```

---

### 7-3. 세션 메타데이터 활용

**목적**: 디버깅 정보 추가

**구현**:
```python
# create_session()에서 메타데이터 저장
metadata = {
    "user_agent": request.headers.get("User-Agent"),
    "ip_address": request.client.host,
    "created_via": "POST /start"
}
```

---

## 📚 8. 참고 문서

- [MIGRATION_COMPLETION_REPORT_251016.md](./MIGRATION_COMPLETION_REPORT_251016.md) - 마이그레이션 완료 보고서
- [plan_of_schema_migration_adaptation_FINAL_251015.md](./plan_of_schema_migration_adaptation_FINAL_251015.md) - Phase 0-C 계획서
- Python `finally` 블록 동작: https://docs.python.org/3/reference/compound_stmts.html#finally

---

## ✅ 9. 결론 및 권장 사항

### 근본 원인
**`postgres_session_manager.py`의 `validate_session()` 메서드에서 `finally: break` 패턴으로 인해 `return` 문이 실행되지 않고 `None`을 반환**

### 현재 상태
- ✅ `validate_session()` **이미 수정됨**
- ⚠️ 서버 재시작 필요 (수정된 코드 로드)
- ⚠️ 다른 메서드들도 같은 패턴 사용 중 (잠재적 버그)

### 권장 실행 순서
1. **즉시 실행**: Phase 0 (서버 재시작 및 테스트) - **5분**
2. **당일 실행**: Phase 1 (안전성 강화) - **15분**
3. **선택 실행**: Phase 2 (로그 정리) - **5분**

**총 예상 작업 시간**: 25분

### 성공 확률
- **Phase 0만 실행**: 90% (현재 코드가 수정되어 있으므로)
- **Phase 0 + 1 실행**: 99% (모든 메서드 패턴 통일)

---

**보고서 종료**

작성자: Claude Code
작성일: 2025-10-16
