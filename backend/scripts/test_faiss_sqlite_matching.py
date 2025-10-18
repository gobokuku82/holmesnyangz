"""
FAISS-SQLite 매칭 종합 테스트
Phase 1: 기본 데이터 일관성 검증
Phase 2: 200개 질문 기반 검색 품질 테스트
Phase 3: 통계 리포트 생성
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import sqlite3
import pickle
import json
import numpy as np
import faiss
from datetime import datetime
from collections import defaultdict
from sentence_transformers import SentenceTransformer

# Paths
FAISS_INDEX_PATH = backend_dir / "data" / "storage" / "legal_info" / "faiss_db" / "legal_documents.index"
FAISS_METADATA_PATH = backend_dir / "data" / "storage" / "legal_info" / "faiss_db" / "legal_metadata.pkl"
SQLITE_DB_PATH = backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db"
QUESTIONS_PATH = backend_dir / "data" / "storage" / "legal_info" / "tests" / "부동산_법률_예시질문_200개.json"
MODEL_PATH = backend_dir / "app" / "ml_models" / "KURE_v1"

# Report paths
REPORT_DIR = backend_dir.parent / "reports" / "database"
REPORT_JSON = REPORT_DIR / f"MATCHING_TEST_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
REPORT_MD = REPORT_DIR / f"MATCHING_TEST_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"


def phase1_basic_consistency():
    """Phase 1: 기본 데이터 일관성 검증"""

    print("=" * 80)
    print("Phase 1: 기본 데이터 일관성 검증")
    print("=" * 80)

    # 1. FAISS 메타데이터 로드
    print("\n[1/4] FAISS 메타데이터 로드 중...")
    with open(FAISS_METADATA_PATH, 'rb') as f:
        faiss_metadata = pickle.load(f)
    print(f"   ✅ FAISS 메타데이터: {len(faiss_metadata)}개")

    # 2. SQLite 연결
    print("\n[2/4] SQLite DB 연결 중...")
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM articles")
    sqlite_count = cursor.fetchone()['count']
    print(f"   ✅ SQLite 조항: {sqlite_count}개")

    # 3. 수량 비교
    print("\n[3/4] 데이터 수량 비교...")
    count_match = len(faiss_metadata) == sqlite_count

    if count_match:
        print(f"   ✅ 수량 일치: {len(faiss_metadata)}개 = {sqlite_count}개")
    else:
        print(f"   ❌ 수량 불일치: FAISS {len(faiss_metadata)}개 vs SQLite {sqlite_count}개")

    # 4. chunk_id 매칭 테스트
    print("\n[4/4] chunk_id 기반 1:1 매칭 테스트...")

    success_count = 0
    fail_count = 0
    failed_items = []

    for metadata in faiss_metadata:
        chunk_id = metadata.get('chunk_id', '')

        cursor.execute(
            """
            SELECT a.article_number, a.article_title, l.title as law_title
            FROM articles a
            JOIN laws l ON a.law_id = l.law_id
            WHERE a.chunk_ids LIKE ?
            """,
            (f'%"{chunk_id}"%',)
        )
        result = cursor.fetchone()

        if result:
            success_count += 1
        else:
            fail_count += 1
            if len(failed_items) < 10:
                failed_items.append({
                    'chunk_id': chunk_id,
                    'faiss_law': metadata.get('law_title', ''),
                    'faiss_article': metadata.get('article_number', '')
                })

    # 결과 출력
    print(f"\n{'='*80}")
    print("Phase 1 결과")
    print(f"{'='*80}")
    print(f"   총 테스트: {len(faiss_metadata)}개")
    print(f"   ✅ 성공: {success_count}개 ({success_count/len(faiss_metadata)*100:.1f}%)")
    print(f"   ❌ 실패: {fail_count}개 ({fail_count/len(faiss_metadata)*100:.1f}%)")

    if success_count == len(faiss_metadata):
        print(f"\n   🎉 완벽! 모든 FAISS 벡터가 SQLite와 매칭됩니다!")

    # 실패 항목 출력
    if failed_items:
        print(f"\n   실패 항목 (처음 10개):")
        for item in failed_items:
            print(f"      - {item['chunk_id']}: {item['faiss_law']} {item['faiss_article']}")

    conn.close()

    return {
        'faiss_count': len(faiss_metadata),
        'sqlite_count': sqlite_count,
        'count_match': count_match,
        'matching_success': success_count,
        'matching_fail': fail_count,
        'matching_rate': success_count / len(faiss_metadata) * 100,
        'failed_items': failed_items
    }


def phase2_question_search(run_full_test=True):
    """Phase 2: 200개 질문 기반 검색 품질 테스트"""

    print("\n" + "=" * 80)
    print("Phase 2: 200개 질문 검색 품질 테스트")
    print("=" * 80)

    # 1. 질문 파일 로드
    print("\n[1/6] 질문 파일 로드 중...")
    if not QUESTIONS_PATH.exists():
        print(f"   ❌ 질문 파일 없음: {QUESTIONS_PATH}")
        return None

    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        questions_data = json.load(f)

    all_questions = []
    for category in questions_data['categories']:
        for q in category['questions']:
            q['category_name'] = category['category_name']
            all_questions.append(q)

    print(f"   ✅ 총 {len(all_questions)}개 질문 로드")

    # 2. FAISS 인덱스 로드
    print("\n[2/6] FAISS 인덱스 로드 중...")
    index = faiss.read_index(str(FAISS_INDEX_PATH))

    with open(FAISS_METADATA_PATH, 'rb') as f:
        faiss_metadata = pickle.load(f)

    print(f"   ✅ FAISS 인덱스: {index.ntotal}개 벡터")

    # 3. 임베딩 모델 로드
    print("\n[3/6] 임베딩 모델 로드 중...")
    if MODEL_PATH.exists():
        print(f"   - 경로: {MODEL_PATH}")
        model = SentenceTransformer(str(MODEL_PATH))
    else:
        print(f"   ⚠️  KURE_v1 없음, 대체 모델 사용")
        model = SentenceTransformer('jhgan/ko-sbert-multitask')

    print(f"   ✅ 모델 로드 완료 (차원: {model.get_sentence_embedding_dimension()})")

    # 4. SQLite 연결
    print("\n[4/6] SQLite DB 연결 중...")
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    print(f"   ✅ SQLite 연결 완료")

    # 5. 질문별 검색 실행
    print(f"\n[5/6] {len(all_questions)}개 질문 검색 중...")

    # 쿼리 전처리 함수 (hybrid_legal_search.py와 동일)
    def enhance_query_for_search(query: str) -> str:
        """쿼리를 문서 형식과 유사하게 변환"""
        legal_terms = [
            "자격시험", "응시", "조건", "등록", "중개사", "중개업", "공인중개사",
            "전세금", "인상률", "임대차", "계약", "보증금", "갱신", "임차인",
            "임대인", "월세", "전세", "계약서", "설명의무",
            "주택", "공동주택", "아파트", "다세대", "분양", "임대주택",
            "금지행위", "손해배상", "권리", "의무", "벌칙", "과태료",
            "신고", "허가", "승인", "검사", "확인", "제출"
        ]

        keywords = []
        for term in legal_terms:
            patterns = [term, f"{term}에", f"{term}의", f"{term}을", f"{term}를",
                       f"{term}은", f"{term}는", f"{term}이", f"{term}가"]
            if any(p in query for p in patterns):
                if term not in keywords:
                    keywords.append(term)

        if keywords:
            title = " ".join(keywords[:3])
            return f"{title}\n{query}"
        return query

    # 법률 계층 구조 재정렬 함수
    def rerank_by_legal_hierarchy(results, n_results=3):
        """법률 계층 구조를 고려하여 검색 결과 재정렬"""
        doc_type_weights = {
            "법률": 3.0,
            "시행령": 2.0,
            "시행규칙": 1.0,
            "대법원규칙": 1.5,
            "용어집": 0.5
        }

        reranked = []
        for i, (result, dist) in enumerate(zip(results, distances[0][:len(results)])):
            doc_type = result.get('doc_type', '시행규칙')
            similarity_score = 1.0 / (1.0 + dist)
            weight = doc_type_weights.get(doc_type, 1.0)
            final_score = similarity_score * weight

            reranked.append({
                "index": i,
                "score": final_score,
                "result": result
            })

        reranked.sort(key=lambda x: x["score"], reverse=True)
        return [item["result"] for item in reranked[:n_results]]

    results = []
    category_stats = defaultdict(lambda: {'total': 0, 'law_match': 0})
    law_frequency = defaultdict(int)
    difficulty_stats = defaultdict(lambda: {'total': 0, 'law_match': 0})

    for i, question in enumerate(all_questions):
        if (i + 1) % 20 == 0:
            print(f"   진행 중: {i+1}/{len(all_questions)} ({(i+1)/len(all_questions)*100:.1f}%)")

        # ⭐ 쿼리 전처리 추가
        question_text = question['question']
        enhanced_query = enhance_query_for_search(question_text)

        # 질문 임베딩 (전처리된 쿼리 사용)
        query_embedding = model.encode([enhanced_query], convert_to_tensor=False).astype('float32')

        # ⭐ FAISS 검색 (재정렬을 위해 Top 9 검색)
        distances, indices = index.search(query_embedding, 9)

        # 임시 검색 결과 수집
        temp_results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= len(faiss_metadata):
                continue

            meta = faiss_metadata[idx]
            chunk_id = meta.get('chunk_id', '')

            # SQLite 매칭
            cursor.execute(
                """
                SELECT a.article_number, a.article_title, l.title as law_title, l.doc_type
                FROM articles a
                JOIN laws l ON a.law_id = l.law_id
                WHERE a.chunk_ids LIKE ?
                """,
                (f'%"{chunk_id}"%',)
            )
            sqlite_result = cursor.fetchone()

            if sqlite_result:
                temp_results.append({
                    'rank': rank + 1,
                    'law_title': sqlite_result['law_title'],
                    'article_number': sqlite_result['article_number'],
                    'article_title': sqlite_result['article_title'],
                    'doc_type': sqlite_result['doc_type'],
                    'distance': float(dist),
                    'chunk_id': chunk_id
                })

        # ⭐ 법률 계층 구조로 재정렬
        search_results = rerank_by_legal_hierarchy(temp_results, n_results=3)

        # 통계 수집
        law_matched = False
        for result in search_results:
            # 법령 빈도 카운트
            law_frequency[result['law_title']] += 1

            # related_law 매칭 확인
            if question['related_law'] in result['law_title']:
                law_matched = True

        # 통계 업데이트
        category_stats[question['category_name']]['total'] += 1
        if law_matched:
            category_stats[question['category_name']]['law_match'] += 1

        difficulty_stats[question['difficulty']]['total'] += 1
        if law_matched:
            difficulty_stats[question['difficulty']]['law_match'] += 1

        results.append({
            'id': question['id'],
            'question': question_text,
            'related_law': question['related_law'],
            'category': question['category_name'],
            'difficulty': question['difficulty'],
            'topic': question['topic'],
            'law_matched': law_matched,
            'search_results': search_results
        })

    print(f"   ✅ 검색 완료: {len(results)}개")

    # 6. 통계 계산
    print("\n[6/6] 통계 분석 중...")

    total_questions = len(results)
    total_law_matches = sum(1 for r in results if r['law_matched'])
    law_match_rate = total_law_matches / total_questions * 100

    # SQLite 매칭 성공률
    total_sqlite_matches = sum(len(r['search_results']) for r in results)
    expected_sqlite_matches = total_questions * 3  # 각 질문당 Top 3

    print(f"   ✅ 통계 분석 완료")

    conn.close()

    # 결과 출력
    print(f"\n{'='*80}")
    print("Phase 2 결과")
    print(f"{'='*80}")
    print(f"   총 질문: {total_questions}개")
    print(f"   ✅ related_law 일치: {total_law_matches}개 ({law_match_rate:.1f}%)")
    print(f"   ✅ SQLite 매칭: {total_sqlite_matches}/{expected_sqlite_matches}개 ({total_sqlite_matches/expected_sqlite_matches*100:.1f}%)")

    print(f"\n   카테고리별 정확도:")
    for cat_name, stats in sorted(category_stats.items()):
        rate = stats['law_match'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"      - {cat_name}: {stats['law_match']}/{stats['total']} ({rate:.1f}%)")

    print(f"\n   난이도별 정확도:")
    for diff, stats in sorted(difficulty_stats.items()):
        rate = stats['law_match'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"      - {diff}: {stats['law_match']}/{stats['total']} ({rate:.1f}%)")

    print(f"\n   법령 검색 빈도 Top 10:")
    for i, (law, count) in enumerate(sorted(law_frequency.items(), key=lambda x: x[1], reverse=True)[:10], 1):
        print(f"      {i}. {law[:50]}: {count}회")

    return {
        'total_questions': total_questions,
        'law_match_count': total_law_matches,
        'law_match_rate': law_match_rate,
        'sqlite_match_count': total_sqlite_matches,
        'sqlite_match_expected': expected_sqlite_matches,
        'sqlite_match_rate': total_sqlite_matches / expected_sqlite_matches * 100,
        'category_stats': dict(category_stats),
        'difficulty_stats': dict(difficulty_stats),
        'law_frequency': dict(law_frequency),
        'detailed_results': results[:10]  # 처음 10개만 저장
    }


def phase3_generate_report(phase1_result, phase2_result):
    """Phase 3: 통계 리포트 생성"""

    print("\n" + "=" * 80)
    print("Phase 3: 통계 리포트 생성")
    print("=" * 80)

    # 리포트 디렉토리 생성
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. JSON 리포트
    print("\n[1/2] JSON 리포트 생성 중...")
    report_data = {
        'test_date': datetime.now().isoformat(),
        'phase1_basic_consistency': phase1_result,
        'phase2_question_search': phase2_result
    }

    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"   ✅ JSON 리포트 저장: {REPORT_JSON.name}")

    # 2. Markdown 리포트
    print("\n[2/2] Markdown 리포트 생성 중...")

    md_content = f"""# FAISS-SQLite 매칭 테스트 결과

**테스트 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Phase 1: 기본 데이터 일관성 검증

### 데이터 수량
- FAISS 벡터: **{phase1_result['faiss_count']:,}개**
- SQLite 레코드: **{phase1_result['sqlite_count']:,}개**
- 수량 일치: **{'✅ 일치' if phase1_result['count_match'] else '❌ 불일치'}**

### chunk_id 매칭
- 총 테스트: {phase1_result['faiss_count']:,}개
- ✅ 성공: {phase1_result['matching_success']:,}개 ({phase1_result['matching_rate']:.1f}%)
- ❌ 실패: {phase1_result['matching_fail']:,}개

**결론**: {'🎉 완벽한 1:1 매칭!' if phase1_result['matching_fail'] == 0 else f'⚠️ {phase1_result["matching_fail"]}개 매칭 실패'}

---

"""

    if phase2_result:
        md_content += f"""## Phase 2: 200개 질문 검색 품질 테스트

### 전체 통계
- 총 질문: **{phase2_result['total_questions']}개**
- related_law 일치: **{phase2_result['law_match_count']}개 ({phase2_result['law_match_rate']:.1f}%)**
- SQLite 매칭: **{phase2_result['sqlite_match_count']}/{phase2_result['sqlite_match_expected']}개 ({phase2_result['sqlite_match_rate']:.1f}%)**

### 카테고리별 정확도

| 카테고리 | 질문 수 | 일치 | 정확도 |
|---------|--------|------|--------|
"""
        for cat_name, stats in sorted(phase2_result['category_stats'].items()):
            rate = stats['law_match'] / stats['total'] * 100 if stats['total'] > 0 else 0
            md_content += f"| {cat_name} | {stats['total']} | {stats['law_match']} | {rate:.1f}% |\n"

        md_content += f"""
### 난이도별 정확도

| 난이도 | 질문 수 | 일치 | 정확도 |
|--------|--------|------|--------|
"""
        for diff, stats in sorted(phase2_result['difficulty_stats'].items()):
            rate = stats['law_match'] / stats['total'] * 100 if stats['total'] > 0 else 0
            md_content += f"| {diff} | {stats['total']} | {stats['law_match']} | {rate:.1f}% |\n"

        md_content += f"""
### 법령 검색 빈도 Top 10

| 순위 | 법령 | 검색 횟수 |
|------|------|----------|
"""
        for i, (law, count) in enumerate(sorted(phase2_result['law_frequency'].items(), key=lambda x: x[1], reverse=True)[:10], 1):
            md_content += f"| {i} | {law[:50]} | {count}회 |\n"

    md_content += f"""
---

## 종합 평가

"""

    if phase1_result['matching_fail'] == 0:
        md_content += "✅ **Phase 1**: 완벽한 FAISS-SQLite 데이터 일관성\n"
    else:
        md_content += f"⚠️ **Phase 1**: {phase1_result['matching_fail']}개 매칭 실패\n"

    if phase2_result and phase2_result['law_match_rate'] >= 70:
        md_content += f"✅ **Phase 2**: 우수한 검색 품질 ({phase2_result['law_match_rate']:.1f}%)\n"
    elif phase2_result:
        md_content += f"⚠️ **Phase 2**: 검색 품질 개선 필요 ({phase2_result['law_match_rate']:.1f}%)\n"

    md_content += f"""
---

**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"   ✅ Markdown 리포트 저장: {REPORT_MD.name}")

    print(f"\n{'='*80}")
    print("Phase 3 완료")
    print(f"{'='*80}")
    print(f"   - JSON: {REPORT_JSON}")
    print(f"   - Markdown: {REPORT_MD}")


def main():
    """메인 테스트 함수"""

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "FAISS-SQLite 매칭 종합 테스트" + " " * 28 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Phase 1: 기본 일관성 검증
    phase1_result = phase1_basic_consistency()

    # Phase 2: 200개 질문 검색 테스트
    print("\n계속 진행하시겠습니까? (Phase 2는 약 5분 소요)")
    print("Enter: 계속 진행 / Ctrl+C: 중단")
    try:
        input()
        phase2_result = phase2_question_search()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        phase2_result = None

    # Phase 3: 리포트 생성
    phase3_generate_report(phase1_result, phase2_result)

    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 30 + "테스트 완료" + " " * 36 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Exit code
    if phase1_result['matching_fail'] > 0:
        return 1

    if phase2_result and phase2_result['law_match_rate'] < 70:
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
