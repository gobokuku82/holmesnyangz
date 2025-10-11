# 주택임대차 계약서 생성 시스템

## 📋 개요

주택임대차 표준계약서를 DOCX 템플릿 기반으로 자동 생성하는 시스템입니다.

## 🗂️ 파일 구조

```
backend/
├── data/storage/documents/
│   ├── 주택임대차 표준계약서.docx              # 원본 템플릿
│   ├── 주택임대차 표준계약서_with_placeholders.docx  # 플레이스홀더 버전 (자동 사용)
│   ├── lease_contract_input_schema.json       # 입력 데이터 스키마
│   └── generated/                             # 생성된 계약서 저장 폴더
│       └── 주택임대차계약서_YYYYMMDD_HHMMSS.docx
│
├── app/service_agent/tools/
│   └── lease_contract_generator_tool.py       # 계약서 생성 Tool
│
├── analyze_template.py                        # 템플릿 구조 분석 스크립트
├── add_placeholders_to_template.py           # 플레이스홀더 추가 스크립트
└── test_lease_contract_generation.py         # 테스트 스크립트
```

## 🔧 개선 사항

### 1. 플레이스홀더 기반 매핑
기존: 하드코딩된 셀 인덱스 (예: `table.rows[2].cells[2]`)
개선: 플레이스홀더 검색 및 치환 방식 (예: `{{address_road}}` → 실제 주소)

**장점:**
- ✅ 템플릿 구조 변경에 유연하게 대응
- ✅ 코드 가독성 향상
- ✅ 유지보수 용이

### 2. 자동 템플릿 선택
- 플레이스홀더 버전이 있으면 자동으로 사용
- 없으면 원본 템플릿 사용 (후방 호환성 유지)

### 3. 전체 테이블 순회
- 모든 테이블을 순회하며 플레이스홀더 치환
- 수동 매핑 불필요

## 📝 사용 방법

### 1. 기본 사용 (Python 코드)

```python
from app.service_agent.tools.lease_contract_generator_tool import LeaseContractGeneratorTool

tool = LeaseContractGeneratorTool()

result = await tool.execute(
    address_road="서울특별시 강남구 테헤란로 123",
    address_detail="456호 (101동 10층)",
    rental_area="85",
    deposit="500,000,000",
    deposit_hangeul="오억",
    start_date="2024년 1월 1일",
    end_date="2026년 1월 1일",
    lessor_name="홍길동",
    lessee_name="김철수"
)

print(result['docx_path'])  # 생성된 파일 경로
```

### 2. 테스트 실행

```bash
cd backend
python test_lease_contract_generation.py
```

## 🔑 필수 필드

반드시 입력해야 하는 필드:
- `address_road`: 도로명 주소
- `deposit`: 보증금
- `start_date`: 계약 시작일
- `end_date`: 계약 종료일
- `lessor_name`: 임대인 이름
- `lessee_name`: 임차인 이름

## 📌 선택 필드

선택적으로 입력 가능:
- `address_detail`: 상세주소 (동/층/호)
- `rental_area`: 임차 면적
- `deposit_hangeul`: 보증금 한글
- `contract_payment`: 계약금
- `monthly_rent`: 월세
- `monthly_rent_day`: 월세 납부일
- `management_fee`: 관리비
- `lessor_address`: 임대인 주소
- `lessor_phone`: 임대인 전화
- `lessee_address`: 임차인 주소
- `lessee_phone`: 임차인 전화
- `special_terms`: 특약사항

## 🛠️ 템플릿 커스터마이징

### 플레이스홀더 추가 방법

1. 원본 템플릿에 플레이스홀더 추가:
```bash
python add_placeholders_to_template.py
```

2. 플레이스홀더 형식:
```
{{field_name}}
```

예시:
- `{{address_road}}` → 도로명 주소
- `{{deposit}}` → 보증금
- `{{lessor_name}}` → 임대인 이름

### 새 필드 추가하기

1. `lease_contract_generator_tool.py`의 `_fill_tables()` 메서드에 플레이스홀더 매핑 추가:
```python
placeholder_map = {
    "{{new_field}}": fields.get("new_field", ""),
    # ... 기존 필드들
}
```

2. 템플릿에 `{{new_field}}` 플레이스홀더 추가

3. 스키마 파일에 필드 정의 추가

## ✅ 검증 결과

테스트 결과:
- ✅ 전세 계약서: 모든 필드 정상 입력
- ✅ 월세 계약서: 모든 필드 정상 입력
- ✅ 플레이스홀더 치환: 정상 작동
- ✅ 파일 생성: 정상 작동

## 📚 참고

- 스키마 상세 정보: `lease_contract_input_schema.json`
- 템플릿 구조 분석: `python analyze_template.py`
