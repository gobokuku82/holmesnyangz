# 답변 생성 로직 개선 보고서

## 개선 날짜
2025-10-02

## 문제점
사용자가 지적한 핵심 문제:
> "답변은 어디서 생성하지? agent가 data를 만들면 판단해서 출력하는 로직이 구현이 되어있는가? 예를 들면 법률 검색하면 검색한 법률만 나열하고 사용자가 원한 질문에 대한 제대로 된 답을 못주는거 같아."

### 발견된 이슈
- `generate_response_node`가 단순히 수집된 데이터를 포맷팅만 하고 있었음
- LLM을 통한 자연어 답변 생성 로직이 없었음
- 사용자는 원시 데이터가 아닌 질문에 대한 **답변**을 원함

## 해결 방안

### 1. LLM 기반 답변 생성 추가
`supervisor/supervisor.py`의 `generate_response_node` 메서드에 LLM 호출 추가:

```python
# 수집된 데이터가 있고 LLM이 사용 가능한 경우
if all_data and not self.llm_manager._connection_error and self.llm_manager.client:
    # 1. 컨텍스트 준비
    context = self._prepare_context_for_llm(all_data)

    # 2. LLM 프롬프트 생성
    system_prompt = """당신은 부동산 전문 상담사입니다.
    수집된 데이터를 기반으로 사용자 질문에 대한 명확하고 구체적인 답변을 제공하세요."""

    # 3. LLM 호출 (GPT-4)
    response = self.llm_manager.client.chat.completions.create(
        model=self.llm_manager.get_model("response"),
        messages=[...],
        temperature=0.3,
        max_tokens=1000
    )

    # 4. 구조화된 응답 생성
    final_response = {
        "type": "answer",
        "answer": final_answer,  # LLM이 생성한 자연어 답변
        "sources": sources,       # 출처 정보
        "data": all_data         # 원본 데이터 (참조용)
    }
```

### 2. 헬퍼 메서드 추가

#### `_prepare_context_for_llm(self, all_data: Dict) -> Dict`
- 각 에이전트의 데이터를 LLM이 이해하기 쉬운 형태로 구조화
- 법률 검색: 상위 5개 법률의 제목, 조항, 내용
- 분석 결과: 요약, 인사이트, 추천사항
- 문서 생성: 생성된 문서 정보
- 계약 검토: 위험 요소, 추천사항

#### `_extract_sources(self, all_data: Dict) -> List[str]`
- 수집된 데이터에서 출처 정보 추출
- 법률 출처: "주택임대차보호법 제7조"
- 시장 데이터 출처: "시장 데이터: [source]"

## 구현 결과

### 테스트 결과
```
Query: 전세금 5% 올리는게 가능한가요?

[SUCCESS - Natural Language Answer Generated]

Answer:
----------------------------------------
전세금 5% 인상은 가능합니다. 관련법 및 제한 사항은 다음과 같습니다.

1. **법적 근거**: 임대인은 계약에 따라 전세금 인상을 임대차기간 또는 보증금액의 증액이 있은 후 1년 이내에는 청구할 수 없습니다.
   단, 증액 청구를 하더라도 증액은 임대료나 보증금의 20분의 1을 초과할 수 없습니다(주택임대차보호법 제7조).

2. **실제 적용**: 일반적인 주거용임대차의 경우, 임대인은 전세금의 5% 이내 인상이 가능합니다.
   이는 최고한도 규정이므로 지역 관례나 임대차 시장의 수급 상황에 따라 조정해야 합니다.

3. **실용적인 조언**: 실제 전세금을 인상하고자 한다면, 임대인과 서면으로 합의된 내용을 확인하고,
   인상 시점과 금액을 명확히 하여 분쟁의 소지를 미연에 방지하는 것이 중요합니다.

결론적으로, 전세금 5% 인상은 법적으로 가능하지만, 계약 조건과 지역 관례를 반드시 확인해야 합니다.
----------------------------------------
```

### 개선 전후 비교

#### 개선 전
- 단순 데이터 나열
- 법률 조항만 보여줌
- 사용자 질문에 대한 직접적인 답변 없음

#### 개선 후
- ✅ 자연어로 된 명확한 답변 제공
- ✅ 법률 근거 포함
- ✅ 실용적인 조언 추가
- ✅ 결론 제시
- ✅ 원본 데이터도 참조 가능하도록 유지

## 기술 스택
- OpenAI GPT-4 (gpt-4o-mini) for response generation
- Temperature: 0.3 (정확성 중시)
- Max tokens: 1000 (충분한 답변 길이)

## 파일 변경 사항

### 1. `supervisor/supervisor.py`
- `generate_response_node` 메서드 수정 (lines 1059-1118)
- `_prepare_context_for_llm` 메서드 추가 (lines 1340-1402)
- `_extract_sources` 메서드 추가 (lines 1404-1432)

### 2. 테스트 파일 생성
- `tests/test_answer_generation.py` - 종합 테스트
- `tests/test_simple_answer.py` - 단위 테스트
- `tests/test_final_answer_gen.py` - 통합 테스트

## 향후 개선 사항

1. **답변 품질 향상**
   - 더 상세한 프롬프트 엔지니어링
   - 도메인별 특화된 답변 템플릿

2. **성능 최적화**
   - 답변 캐싱
   - 스트리밍 응답 지원

3. **다국어 지원**
   - 영어/중국어 답변 생성
   - 언어 자동 감지

4. **피드백 메커니즘**
   - 사용자 만족도 추적
   - 답변 품질 자동 평가

## 결론
사용자가 지적한 핵심 문제를 성공적으로 해결했습니다. 이제 시스템은:
- 수집된 데이터를 바탕으로 **자연어 답변을 생성**합니다
- 법률 조항을 단순 나열하는 대신 **질문에 대한 직접적인 답을 제공**합니다
- 답변에 **법적 근거와 실용적 조언을 포함**합니다
- 투명성을 위해 **원본 데이터와 출처 정보도 함께 제공**합니다