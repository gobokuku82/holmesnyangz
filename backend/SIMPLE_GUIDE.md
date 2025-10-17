# 간단 실행 가이드 (Git Bash)

## ✅ 현재 위치 확인
```bash
pwd
# 출력: /c/kdy/Projects/holmesnyangz/beta_v001/backend
```

---

## 🗑️ 1단계: 기존 테이블 전체 삭제 (깔끔하게 시작)

**결론: 삭제하는 것을 추천합니다!**

이유:
- 기존 스키마와 새 스키마 충돌 방지
- 채팅 테이블 오류 완전 제거
- RealEstate-TrustScore relationship 문제 해결

### 실행 명령어:

```bash
psql -U postgres -d real_estate -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
"
```

**예상 출력**:
```
DROP SCHEMA
CREATE SCHEMA
GRANT
GRANT
```

---

## 📦 2단계: 모든 테이블 생성 + 부동산 데이터 임포트

```bash
# 모든 테이블 생성 (chat + real_estate)
uv run python scripts/init_db.py

# 부동산 데이터 임포트
uv run python scripts/import_apt_ofst.py
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
```

**예상 결과**:
- ✅ 모든 테이블 생성 완료
- ✅ 부동산 데이터 임포트 완료
- ✅ 채팅 테이블 준비 완료 (빈 상태)

---

## 🔍 3단계: 확인

```bash
psql -U postgres -d real_estate -c "
SELECT 'real_estates' as table, COUNT(*) FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions;
"
```

**예상 출력**:
```
    table     | count
--------------+-------
 real_estates | 2895
 transactions | XXXX
 chat_sessions|    0
```

---

## 💡 요약

**추천 순서**:
1. ✅ DROP SCHEMA (기존 삭제)
2. ✅ init_db.py (모든 테이블 생성)
3. ✅ import 스크립트 3개 실행
4. ✅ 확인

**기존 테이블 삭제 안 하면?**
- ❌ 스키마 충돌 가능
- ❌ Relationship 오류 가능
- ❌ 채팅 테이블 불일치 가능

**답변: 기존 테이블 삭제하고 새로 시작하는 것을 추천합니다!**
