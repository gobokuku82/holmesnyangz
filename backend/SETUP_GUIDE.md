# 🚀 DB 설정 가이드 (완전 정리본)

## 📋 목차
1. [방법 A: 전체 초기화 (추천)](#방법-a-전체-초기화-추천)
2. [방법 B: 부동산만 초기화 (채팅 보존)](#방법-b-부동산만-초기화-채팅-보존)
3. [데이터 확인](#데이터-확인)

---

## 방법 A: 전체 초기화 (추천)

**언제 사용?**
- 처음 시작할 때
- 모든 데이터를 깔끔하게 초기화하고 싶을 때
- 채팅 데이터가 없거나 삭제해도 될 때

### ✅ 실행 (Git Bash)

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# Step 1: 모든 테이블 생성 (채팅 + 부동산)
uv run python scripts/init_db.py

# Step 2: 부동산 데이터 Import
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### 📊 예상 결과

**Step 1 후**:
```
✅ 테이블 생성 완료
생성된 테이블:
  - users
  - user_profiles
  - chat_sessions
  - chat_messages
  - checkpoints
  - regions
  - real_estates
  - transactions
  - nearby_facilities
  ...
```

**Step 2 후**:
- 아파트/오피스텔: ~2,104개
- 원룸: ~1,010개
- 빌라: ~6,631개
- **총 ~9,745개 부동산 매물**

---

## 방법 B: 부동산만 초기화 (채팅 보존)

**언제 사용?**
- 기존 채팅 데이터를 보존하고 싶을 때
- 부동산 데이터만 다시 import 하고 싶을 때

### ✅ 실행 (Git Bash)

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# Step 1: 부동산 테이블만 초기화 (채팅 보존)
uv run python scripts/init_db_estate_only.py

# Step 2: 부동산 데이터 Import
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### 📊 예상 결과

**Step 1 후**:
```
✅ 부동산 테이블 초기화 완료!

생성된 테이블:
  - regions
  - real_estates
  - transactions
  - nearby_facilities
  - real_estate_agents
  - trust_scores
  - user_favorites

채팅 테이블 보존됨:
  ✅ chat_sessions
  ✅ chat_messages
  ✅ checkpoints
```

---

## 데이터 확인

### 전체 데이터 개수 확인

```bash
psql -U postgres -d real_estate -c "
SELECT 'real_estates' as table, COUNT(*) as count FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'regions', COUNT(*) FROM regions
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions
UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages;
"
```

**예상 출력**:
```
     table      | count
----------------+-------
 real_estates   | 9,745
 transactions   | 15,000+
 regions        | 50+
 chat_sessions  | 0 (또는 기존 데이터)
 chat_messages  | 0 (또는 기존 데이터)
```

### 부동산 타입별 확인

```bash
psql -U postgres -d real_estate -c "
SELECT property_type, COUNT(*) as count
FROM real_estates
GROUP BY property_type
ORDER BY count DESC;
"
```

**예상 출력**:
```
 property_type | count
---------------+-------
 villa         | 6,631
 apartment     | 2,000+
 oneroom       | 1,010
 officetel     | 100+
```

---

## 🔧 문제 해결

### Q1: `uv: command not found`
```bash
# Python으로 직접 실행
python scripts/init_db.py
python scripts/import_apt_ofst.py
```

### Q2: Import 중 에러 발생
```bash
# 개별 에러는 무시하고 계속 진행됨
# 최종 통계에서 "성공 X개, 실패 X개" 확인
# 실패가 100개 미만이면 정상
```

### Q3: ENUM 타입 에러
```
propertytype 열거형의 입력 값이 잘못됨
```

**해결**: `init_db.py` 사용 (Python이 자동으로 ENUM 생성)

```bash
# SQL 파일 말고 Python 사용
uv run python scripts/init_db.py
```

### Q4: 테이블이 이미 존재함
```bash
# 기존 테이블 삭제 후 재생성
uv run python scripts/init_db.py  # 자동으로 DROP CASCADE
```

---

## 📝 요약

| 방법 | 채팅 데이터 | 부동산 데이터 | 명령어 |
|------|-----------|-------------|--------|
| **방법 A** | ❌ 삭제됨 | ✅ 새로 생성 | `init_db.py` → import |
| **방법 B** | ✅ 보존됨 | ✅ 새로 생성 | `init_db_estate_only.py` → import |

---

## 🎯 추천

### 처음 시작하는 경우
→ **방법 A** 사용

```bash
uv run python scripts/init_db.py
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### 채팅 데이터가 있는 경우
→ **방법 B** 사용

```bash
uv run python scripts/init_db_estate_only.py
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

---

## ✅ 완료 후

```bash
# 1. Backend 서버 시작
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend
uvicorn app.main:app --reload

# 2. Frontend 서버 시작 (새 터미널)
cd /c/kdy/Projects/holmesnyangz/beta_v001/frontend
npm run dev

# 3. 브라우저에서 테스트
# http://localhost:3000
```

---

**작성일**: 2025-10-17
**목적**: DB 설정 완전 정리 (채팅/부동산 분리)
