# 🚀 부동산 데이터 Import 최종 가이드

## ✅ 현재 상태

- **아파트/오피스텔**: 2,104개 ✅ 완료
- **빌라**: 6,631개 ⏳ 대기 중
- **원룸**: 1,013개 ⏳ 대기 중

---

## 📋 실행 방법

### 1. 아파트/오피스텔 (이미 완료)
```bash
cd /Users/macbook/Desktop/learn/side_project/backend
python scripts/import_simple.py
```
✅ **완료됨** - 2,104개 데이터 있음

---

### 2. 빌라 Import (6,631개)

```bash
cd /Users/macbook/Desktop/learn/side_project/backend
python scripts/import_villa_only.py
```

**예상 소요 시간**: 약 5-10분
**데이터**: 빌라 6,631개

**실행 중 출력 예시:**
```
============================================================
🏘️  빌라 데이터 Import
============================================================

📊 [빌라] CSV 로드: 6,631개 레코드
  📈 진행: 200/6631 (성공: 180, 중복: 20)
  📈 진행: 400/6631 (성공: 360, 중복: 40)
  ...
```

---

### 3. 원룸 Import (1,013개)

빌라 완료 후 실행:

```bash
cd /Users/macbook/Desktop/learn/side_project/backend
python scripts/import_oneroom_only.py
```

**예상 소요 시간**: 약 1-2분

---

## 🎯 빠른 실행 (모두 한 번에)

시간이 충분하다면:

```bash
cd /Users/macbook/Desktop/learn/side_project/backend

# 빌라 + 원룸 동시 import (10-15분 소요)
python scripts/import_all_types.py
```

---

## 📊 최종 예상 결과

전체 import 완료 시:

```
데이터베이스 전체 통계:
  Regions:             50개
  RealEstates:      9,748개
  Transactions:    12,000개
  NearbyFacilities: 9,748개
  RealEstateAgents: 7,644개 (빌라/원룸만)
```

---

## ⚡ 권장 실행 순서

1. **먼저 확인**
   ```bash
   cd /Users/macbook/Desktop/learn/side_project/backend
   python -c "from app.db.postgre_db import SessionLocal; from app.models.real_estate import RealEstate; db = SessionLocal(); print(f'현재: {db.query(RealEstate).count()}개'); db.close()"
   ```

2. **빌라 import**
   ```bash
   python scripts/import_villa_only.py
   ```
   ⏰ 커피 한 잔 (5-10분)

3. **확인**
   ```bash
   python -c "from app.db.postgre_db import SessionLocal; from app.models.real_estate import RealEstate; db = SessionLocal(); print(f'현재: {db.query(RealEstate).count()}개'); db.close()"
   ```

4. **원룸 import** (원하면)
   ```bash
   python scripts/import_oneroom_only.py
   ```

---

## 🐛 문제 해결

### Import가 느린 경우
- 정상입니다. 6,631개 데이터는 시간이 걸립니다.
- 진행 상황이 출력되는지 확인하세요.

### 중복 데이터
- 자동으로 건너뜁니다. 괜찮습니다.

### 메모리 부족
- 한 번에 하나씩 실행하세요:
  1. 빌라만
  2. 원룸만

---

## ✅ 완료 확인

```bash
cd backend
python -c "
from app.db.postgre_db import SessionLocal
from app.models.real_estate import RealEstate, PropertyType

db = SessionLocal()
print('=' * 50)
print('부동산 데이터 통계:')
print(f'아파트:  {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.APARTMENT).count():5,}개')
print(f'오피스텔: {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.OFFICETEL).count():5,}개')
print(f'빌라:    {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.VILLA).count():5,}개')
print(f'원룸:    {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.ONEROOM).count():5,}개')
print(f'단독주택: {db.query(RealEstate).filter(RealEstate.property_type == PropertyType.HOUSE).count():5,}개')
print('-' * 50)
print(f'전체:    {db.query(RealEstate).count():5,}개')
print('=' * 50)
db.close()
"
```
