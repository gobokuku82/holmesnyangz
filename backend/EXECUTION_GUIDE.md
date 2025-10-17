# 데이터베이스 재설정 실행 가이드

## 📋 실행 순서

### 1단계: 부동산 데이터 임포트 (테이블 자동 생성)

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend

# 아파트/오피스텔 데이터 임포트
uv run python scripts/import_apt_ofst.py

# 원룸 데이터 임포트
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# 빌라 데이터 임포트
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

**예상 결과**:
- ✅ regions, real_estates, transactions, nearby_facilities, real_estate_agents, trust_scores 테이블 생성
- ✅ 부동산 데이터 임포트 완료

---

### 2단계: 채팅 테이블 마이그레이션

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend

# 채팅 관련 테이블만 재생성
uv run python scripts/init_chat_tables.py
```

**예상 결과**:
- ✅ chat_sessions 테이블 생성
- ✅ chat_messages 테이블 생성
- ✅ checkpoints 테이블 생성 (LangGraph)
- ✅ checkpoint_blobs 테이블 생성 (LangGraph)
- ✅ checkpoint_writes 테이블 생성 (LangGraph)

---

### 3단계: 데이터 확인

#### PostgreSQL로 확인

```bash
# 모든 테이블 목록 확인
psql -U postgres -d real_estate -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

# 데이터 개수 확인
psql -U postgres -d real_estate -c "
SELECT 'real_estates' as table, COUNT(*) as count FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions
UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages
UNION ALL SELECT 'checkpoints', COUNT(*) FROM checkpoints;
"
```

**예상 결과**:
```
         table         | count
-----------------------+-------
 real_estates          |  XXXX
 transactions          |  XXXX
 chat_sessions         |     0
 chat_messages         |     0
 checkpoints           |     0
```

---

## 🔍 문제 해결

### 임포트 실패 시

**에러**: `One or more mappers failed to initialize`
- **원인**: RealEstate 모델에 trust_scores relationship 누락
- **해결**: ✅ 이미 수정 완료 ([real_estate.py:98](backend/app/models/real_estate.py#L98))

### 테이블 생성 실패 시

**에러**: `relation already exists`
- **원인**: 테이블이 이미 존재
- **해결**:
  ```bash
  # 채팅 테이블만 삭제 후 재실행
  psql -U postgres -d real_estate -c "
  DROP TABLE IF EXISTS chat_messages CASCADE;
  DROP TABLE IF EXISTS chat_sessions CASCADE;
  DROP TABLE IF EXISTS checkpoint_writes CASCADE;
  DROP TABLE IF EXISTS checkpoint_blobs CASCADE;
  DROP TABLE IF EXISTS checkpoints CASCADE;
  "

  # 다시 실행
  uv run python scripts/init_chat_tables.py
  ```

---

## ✅ 실행 후 보고할 내용

1. **각 단계별 실행 결과 (성공/실패)**
2. **에러 메시지 (있을 경우)**
3. **데이터 개수 확인 결과**

예시:
```
1단계: ✅ 성공 - real_estates: 2,895개
2단계: ✅ 성공 - chat_sessions 생성 완료
3단계: ✅ 확인 완료 - 모든 테이블 정상
```
