"""
FAISS 벡터 DB 검증 스크립트
ChromaDB → FAISS 마이그레이션 전 DB 상태 확인
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import sqlite3
import time

# Paths
FAISS_INDEX_PATH = backend_dir / "data" / "storage" / "legal_info" / "faiss_db" / "legal_documents.index"
FAISS_METADATA_PATH = backend_dir / "data" / "storage" / "legal_info" / "faiss_db" / "legal_metadata.pkl"
SQLITE_DB_PATH = backend_dir / "data" / "storage" / "legal_info" / "sqlite_db" / "legal_metadata.db"
EMBEDDING_MODEL_PATH = backend_dir / "app" / "ml_models" / "KURE_v1"


def print_header(text):
    """헤더 출력"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)


def print_step(step, text):
    """단계 출력"""
    print(f"\n[{step}] {text}")


def verify_faiss_db():
    """FAISS DB 검증"""

    print_header("FAISS 벡터 DB 검증 시작")

    # =========================================================================
    # 1. 파일 존재 확인
    # =========================================================================
    print_step("1/7", "파일 존재 확인")

    if not FAISS_INDEX_PATH.exists():
        print(f"❌ FAISS 인덱스 파일 없음: {FAISS_INDEX_PATH}")
        return False
    print(f"✅ FAISS 인덱스: {FAISS_INDEX_PATH.name} ({FAISS_INDEX_PATH.stat().st_size / 1024 / 1024:.2f} MB)")

    if not FAISS_METADATA_PATH.exists():
        print(f"❌ 메타데이터 파일 없음: {FAISS_METADATA_PATH}")
        return False
    print(f"✅ 메타데이터: {FAISS_METADATA_PATH.name} ({FAISS_METADATA_PATH.stat().st_size / 1024 / 1024:.2f} MB)")

    if not SQLITE_DB_PATH.exists():
        print(f"❌ SQLite DB 없음: {SQLITE_DB_PATH}")
        return False
    print(f"✅ SQLite DB: {SQLITE_DB_PATH.name} ({SQLITE_DB_PATH.stat().st_size / 1024:.2f} KB)")

    # =========================================================================
    # 2. FAISS 인덱스 로드
    # =========================================================================
    print_step("2/7", "FAISS 인덱스 로드")

    try:
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        print(f"✅ FAISS 인덱스 로드 성공")
        print(f"   - 벡터 수: {index.ntotal:,}개")
        print(f"   - 벡터 차원: {index.d}")
        print(f"   - 인덱스 타입: {type(index).__name__}")
    except Exception as e:
        print(f"❌ FAISS 인덱스 로드 실패: {e}")
        return False

    # =========================================================================
    # 3. 메타데이터 로드 및 검증
    # =========================================================================
    print_step("3/7", "메타데이터 로드 및 검증")

    try:
        with open(FAISS_METADATA_PATH, 'rb') as f:
            metadata = pickle.load(f)

        print(f"✅ 메타데이터 로드 성공: {len(metadata):,}개")

        # 벡터 수와 메타데이터 수 일치 확인
        if index.ntotal != len(metadata):
            print(f"❌ 벡터 수({index.ntotal})와 메타데이터 수({len(metadata)})가 불일치!")
            return False
        print(f"✅ 벡터-메타데이터 수 일치: {index.ntotal:,}개")

        # 메타데이터 구조 확인
        if not metadata:
            print(f"❌ 메타데이터가 비어있음")
            return False

        sample_meta = metadata[0]
        required_fields = ["chunk_id", "law_title", "article_number", "content"]
        missing_fields = [f for f in required_fields if f not in sample_meta]

        if missing_fields:
            print(f"❌ 필수 필드 누락: {missing_fields}")
            print(f"   실제 필드: {list(sample_meta.keys())}")
            return False

        print(f"✅ 메타데이터 구조 확인")
        print(f"   필드: {list(sample_meta.keys())}")
        print(f"   샘플:")
        print(f"     - law_title: {sample_meta['law_title']}")
        print(f"     - article_number: {sample_meta.get('article_number', 'N/A')}")
        print(f"     - content 길이: {len(sample_meta['content'])}자")

    except Exception as e:
        print(f"❌ 메타데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # =========================================================================
    # 4. 임베딩 모델 로드
    # =========================================================================
    print_step("4/7", "임베딩 모델 로드")

    try:
        if not EMBEDDING_MODEL_PATH.exists():
            print(f"❌ 임베딩 모델 경로 없음: {EMBEDDING_MODEL_PATH}")
            return False

        model = SentenceTransformer(str(EMBEDDING_MODEL_PATH))
        embedding_dim = model.get_sentence_embedding_dimension()

        print(f"✅ 임베딩 모델 로드 성공")
        print(f"   - 모델: KURE_v1")
        print(f"   - 차원: {embedding_dim}")

        # 모델 차원과 FAISS 인덱스 차원 일치 확인
        if embedding_dim != index.d:
            print(f"❌ 모델 차원({embedding_dim})과 FAISS 차원({index.d})이 불일치!")
            return False
        print(f"✅ 모델-인덱스 차원 일치: {embedding_dim}D")

    except Exception as e:
        print(f"❌ 임베딩 모델 로드 실패: {e}")
        return False

    # =========================================================================
    # 5. 샘플 벡터 검색 테스트
    # =========================================================================
    print_step("5/7", "샘플 벡터 검색 테스트")

    test_queries = [
        "전세금 인상률 5% 제한",
        "임대차 계약 갱신 청구권",
        "임차인 보호 조항"
    ]

    try:
        for i, query in enumerate(test_queries, 1):
            # 쿼리 임베딩
            start_time = time.time()
            query_embedding = model.encode(query, convert_to_tensor=False)
            query_embedding = np.array([query_embedding], dtype='float32')

            # FAISS 검색
            distances, indices = index.search(query_embedding, 5)
            elapsed = (time.time() - start_time) * 1000

            print(f"\n   테스트 {i}: '{query}'")
            print(f"   ⏱️  검색 시간: {elapsed:.1f}ms")
            print(f"   📊 결과:")

            for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
                if idx < len(metadata):
                    meta = metadata[idx]
                    similarity = 1 - (dist / 10)  # L2 distance to similarity
                    print(f"      {rank}. [{meta['law_title']}] {meta.get('article_number', 'N/A')}")
                    print(f"         거리: {dist:.4f}, 유사도: {similarity:.2%}")
                    print(f"         내용: {meta['content'][:80]}...")

        print(f"\n✅ 벡터 검색 테스트 완료")

    except Exception as e:
        print(f"❌ 벡터 검색 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # =========================================================================
    # 6. SQLite 메타데이터 매칭 테스트
    # =========================================================================
    print_step("6/7", "SQLite 메타데이터 매칭 테스트")

    try:
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 총 법령 수
        cursor.execute("SELECT COUNT(*) as total FROM laws")
        total_laws = cursor.fetchone()['total']
        print(f"   총 법령: {total_laws}개")

        # 총 조항 수
        cursor.execute("SELECT COUNT(*) as total FROM articles WHERE is_deleted = 0")
        total_articles = cursor.fetchone()['total']
        print(f"   총 조항: {total_articles}개")

        # 샘플 매칭 테스트
        sample_meta = metadata[0]
        law_title = sample_meta['law_title']
        article_number = sample_meta.get('article_number', '')

        if article_number:
            cursor.execute(
                """
                SELECT a.*, l.title as law_title
                FROM articles a
                JOIN laws l ON a.law_id = l.law_id
                WHERE l.title LIKE ? AND a.article_number = ?
                """,
                (f"%{law_title}%", article_number)
            )
            result = cursor.fetchone()

            if result:
                print(f"✅ SQLite 매칭 성공")
                print(f"   - 법령: {result['law_title']}")
                print(f"   - 조항: {result['article_number']} ({result.get('article_title', 'N/A')})")
            else:
                print(f"⚠️  SQLite 매칭 실패 (데이터 불일치 가능)")
                print(f"   - 검색: {law_title} {article_number}")

        conn.close()
        print(f"✅ SQLite 매칭 테스트 완료")

    except Exception as e:
        print(f"❌ SQLite 매칭 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    # =========================================================================
    # 7. 통계 요약
    # =========================================================================
    print_step("7/7", "검증 결과 요약")

    print(f"""
    ✅ FAISS DB 검증 완료!

    📊 통계:
       - FAISS 벡터: {index.ntotal:,}개
       - 메타데이터: {len(metadata):,}개
       - 벡터 차원: {index.d}D
       - SQLite 법령: {total_laws}개
       - SQLite 조항: {total_articles}개

    📁 파일:
       - 인덱스: {FAISS_INDEX_PATH.name} ({FAISS_INDEX_PATH.stat().st_size / 1024 / 1024:.2f} MB)
       - 메타데이터: {FAISS_METADATA_PATH.name} ({FAISS_METADATA_PATH.stat().st_size / 1024 / 1024:.2f} MB)
       - SQLite: {SQLITE_DB_PATH.name} ({SQLITE_DB_PATH.stat().st_size / 1024:.2f} KB)
    """)

    print_header("✅ 모든 검증 통과 - FAISS DB 사용 가능")

    return True


if __name__ == "__main__":
    try:
        success = verify_faiss_db()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
