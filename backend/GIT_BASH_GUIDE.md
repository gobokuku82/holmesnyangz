# Git Bash 실행 가이드

## 🚀 한 번에 실행 (자동화 스크립트)

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# 실행 권한 부여
chmod +x run_migration.sh

# 스크립트 실행
./run_migration.sh
```

**이 스크립트가 자동으로 처리하는 내용**:
1. ✅ 아파트/오피스텔 데이터 임포트
2. ✅ 원룸 데이터 임포트
3. ✅ 빌라 데이터 임포트
4. ✅ 채팅 테이블 마이그레이션
5. ✅ 데이터 확인

---

## 📝 단계별 수동 실행 (필요시)

### 1단계: 부동산 데이터 임포트

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

# 아파트/오피스텔
uv run python scripts/import_apt_ofst.py

# 원룸
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom

# 빌라
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

### 2단계: 채팅 테이블 마이그레이션

```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

uv run python scripts/init_chat_tables.py
```

### 3단계: 데이터 확인

```bash
# 테이블 목록 확인
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

---

## ⚠️ 문제 해결

### psql 명령을 찾을 수 없는 경우

```bash
# PostgreSQL bin 경로 추가
export PATH="/c/Program Files/PostgreSQL/17/bin:$PATH"

# 또는 전체 경로로 실행
"/c/Program Files/PostgreSQL/17/bin/psql" -U postgres -d real_estate -c "SELECT version();"
```

### uv 명령을 찾을 수 없는 경우

```bash
# Python 직접 실행
python scripts/import_apt_ofst.py

# 또는 py 사용
py scripts/import_apt_ofst.py
```

---

## 💡 추천 실행 방법

**가장 간단한 방법**:
```bash
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend
chmod +x run_migration.sh
./run_migration.sh
```

실행 후 결과를 알려주세요!
