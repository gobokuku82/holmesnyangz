# 🔍 DB 데이터 확인 가이드

## 방법 1: SQL 스크립트로 확인 (가장 빠름)

```bash
# PowerShell에서 실행
psql -U postgres -d real_estate -f "C:\kdy\Projects\holmesnyangz\beta_v001\backend\quick_check.sql"
```

## 방법 2: 직접 SQL 실행

```bash
# 1. PostgreSQL 접속
psql -U postgres -d real_estate

# 2. 테이블 목록 확인
\dt

# 3. 부동산 데이터 확인
SELECT COUNT(*) FROM real_estates;
SELECT COUNT(*) FROM transactions;

# 4. 채팅 데이터 확인
SELECT COUNT(*) FROM chat_sessions;
SELECT COUNT(*) FROM chat_messages;

# 5. Session ID 형식 확인
SELECT
    CASE
        WHEN session_id LIKE 'session-%' THEN '✅ session-'
        WHEN session_id LIKE 'chat-%' THEN '❌ chat-'
        ELSE '⚠️ 기타'
    END AS 형식,
    COUNT(*) as 개수
FROM chat_sessions
GROUP BY 형식;
```

## 결과 해석

### Case A: 부동산 데이터 있음
```
real_estates  | 1000
transactions  | 5000
```
→ **주의!** `complete_rebuild_251017.sql` 실행 시 모든 부동산 데이터 삭제됨
→ 대신 `cleanup_chat_only.sql` 사용 (채팅 데이터만 삭제)

### Case B: 부동산 데이터 없음
```
real_estates  | 0
transactions  | 0
```
→ **안전!** `complete_rebuild_251017.sql` 실행 가능

### Case C: 테이블 없음
```
ERROR: relation "real_estates" does not exist
```
→ **안전!** `complete_rebuild_251017.sql` 실행 가능 (새로 생성)

## 다음 단계

### 부동산 데이터가 있는 경우:
→ `cleanup_chat_only.sql` 사용 (생성 필요)

### 부동산 데이터가 없는 경우:
→ `complete_rebuild_251017.sql` 실행

```bash
psql -U postgres -d real_estate -f "C:\kdy\Projects\holmesnyangz\beta_v001\backend\migrations\complete_rebuild_251017.sql"
```
