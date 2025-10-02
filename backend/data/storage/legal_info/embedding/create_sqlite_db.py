"""
ChromaDB 메타데이터 기반 SQLite DB 생성 스크립트

목적: ChromaDB의 메타데이터를 분석하여 laws, articles 테이블 생성

실행 방법:
    python backend/data/storage/legal_info/embedding/create_sqlite_db.py
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Set
import chromadb
from collections import defaultdict

# 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[5]
CHROMA_PATH = PROJECT_ROOT / "backend" / "data" / "storage" / "legal_info" / "chroma_db"
SQLITE_PATH = PROJECT_ROOT / "backend" / "data" / "storage" / "legal_info" / "legal_metadata.db"
SCHEMA_PATH = PROJECT_ROOT / "backend" / "data" / "storage" / "legal_info" / "sqlite_db" / "schema.sql"


def create_tables(conn):
    """테이블 생성"""

    # schema.sql 읽기
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)
            print("[OK] schema.sql 기반 테이블 생성")
    else:
        # schema.sql 없으면 직접 생성
        conn.executescript("""
        -- laws 테이블
        CREATE TABLE IF NOT EXISTS laws (
            law_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,
            title TEXT NOT NULL,
            number TEXT,
            enforcement_date TEXT,
            category TEXT NOT NULL,
            total_articles INTEGER DEFAULT 0,
            last_article TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(title, number, doc_type)
        );

        -- articles 테이블
        CREATE TABLE IF NOT EXISTS articles (
            article_id INTEGER PRIMARY KEY AUTOINCREMENT,
            law_id INTEGER NOT NULL,
            article_number TEXT NOT NULL,
            article_title TEXT,
            chapter TEXT,
            section TEXT,
            is_deleted INTEGER DEFAULT 0,
            is_tenant_protection INTEGER DEFAULT 0,
            is_tax_related INTEGER DEFAULT 0,
            is_delegation INTEGER DEFAULT 0,
            is_penalty_related INTEGER DEFAULT 0,
            chunk_ids TEXT,
            metadata_json TEXT,
            FOREIGN KEY (law_id) REFERENCES laws(law_id),
            UNIQUE(law_id, article_number)
        );

        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_laws_title ON laws(title);
        CREATE INDEX IF NOT EXISTS idx_laws_doc_type ON laws(doc_type);
        CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(category);
        CREATE INDEX IF NOT EXISTS idx_articles_law_id ON articles(law_id);
        CREATE INDEX IF NOT EXISTS idx_articles_number ON articles(article_number);
        """)
        print("[OK] 기본 테이블 생성")


def extract_from_chromadb():
    """ChromaDB에서 메타데이터 추출"""
    print("\n[1] ChromaDB 메타데이터 추출 중...")

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("korean_legal_documents")

    total_count = collection.count()
    print(f"   전체 문서: {total_count}개")

    # 모든 메타데이터 가져오기 (배치 처리)
    batch_size = 1000
    all_data = []

    for offset in range(0, total_count, batch_size):
        results = collection.get(
            limit=batch_size,
            offset=offset,
            include=['metadatas']
        )

        for doc_id, metadata in zip(results['ids'], results['metadatas']):
            all_data.append({
                'id': doc_id,
                'metadata': metadata
            })

        print(f"   진행: {len(all_data)}/{total_count}")

    print(f"[OK] {len(all_data)}개 문서 메타데이터 추출 완료\n")
    return all_data


def group_by_law(all_data: List[Dict]) -> Dict:
    """법령별로 그룹화"""
    print("[2] 법령별 그룹화 중...")

    laws_dict = defaultdict(lambda: {
        'metadata': {},
        'articles': defaultdict(list)
    })

    for item in all_data:
        meta = item['metadata']
        doc_id = item['id']

        title = meta.get('title', 'Unknown')
        article_number = meta.get('article_number', '')

        # 법령 정보 저장 (첫 번째 문서 기준)
        if not laws_dict[title]['metadata']:
            laws_dict[title]['metadata'] = {
                'title': title,
                'doc_type': meta.get('doc_type', ''),
                'number': meta.get('number', ''),
                'enforcement_date': meta.get('enforcement_date', ''),
                'category': meta.get('category', ''),
            }

        # 조항 정보 저장
        laws_dict[title]['articles'][article_number].append({
            'chunk_id': doc_id,
            'article_title': meta.get('article_title', ''),
            'chapter': meta.get('chapter', ''),
            'is_deleted': meta.get('is_deleted', False),
            'is_tenant_protection': meta.get('is_tenant_protection', False),
            'is_tax_related': meta.get('is_tax_related', False),
            'is_delegation': meta.get('is_delegation', False),
            'is_penalty_related': meta.get('is_penalty_related', False),
        })

    print(f"[OK] {len(laws_dict)}개 법령으로 그룹화 완료\n")
    return laws_dict


def insert_into_sqlite(conn, laws_dict: Dict):
    """SQLite DB에 삽입"""
    print("[3] SQLite DB에 삽입 중...")

    cursor = conn.cursor()
    law_count = 0
    article_count = 0

    for title, law_data in laws_dict.items():
        law_meta = law_data['metadata']
        articles = law_data['articles']

        # laws 테이블에 삽입
        total_articles = len(articles)
        last_article = max(articles.keys(), key=lambda x: x) if articles else ''

        cursor.execute("""
            INSERT INTO laws (doc_type, title, number, enforcement_date, category, total_articles, last_article)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            law_meta['doc_type'],
            law_meta['title'],
            law_meta['number'],
            law_meta['enforcement_date'],
            law_meta['category'],
            total_articles,
            last_article
        ))

        law_id = cursor.lastrowid
        law_count += 1

        # articles 테이블에 삽입
        for article_number, chunks in articles.items():
            if not article_number:
                continue

            # 첫 번째 청크 기준으로 조항 정보 저장
            first_chunk = chunks[0]

            # chunk_ids를 JSON 배열로 저장
            chunk_ids = json.dumps([c['chunk_id'] for c in chunks], ensure_ascii=False)

            cursor.execute("""
                INSERT INTO articles (
                    law_id, article_number, article_title, chapter,
                    chunk_ids, is_deleted, is_tenant_protection, is_tax_related,
                    is_delegation, is_penalty_related
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                law_id,
                article_number,
                first_chunk['article_title'],
                first_chunk['chapter'],
                chunk_ids,
                first_chunk['is_deleted'],
                first_chunk['is_tenant_protection'],
                first_chunk['is_tax_related'],
                first_chunk['is_delegation'],
                first_chunk['is_penalty_related']
            ))

            article_count += 1

    conn.commit()
    print(f"[OK] laws: {law_count}개, articles: {article_count}개 삽입 완료\n")

    return law_count, article_count


def verify_database(conn):
    """데이터베이스 검증"""
    print("[4] 데이터베이스 검증 중...")

    cursor = conn.cursor()

    # 전체 통계
    cursor.execute("SELECT COUNT(*) FROM laws")
    law_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM articles")
    article_count = cursor.fetchone()[0]

    print(f"   laws: {law_count}개")
    print(f"   articles: {article_count}개")

    # doc_type 분포
    print("\n   doc_type 분포:")
    cursor.execute("""
        SELECT doc_type, COUNT(*) as cnt
        FROM laws
        GROUP BY doc_type
        ORDER BY cnt DESC
    """)
    for row in cursor.fetchall():
        print(f"     - {row[0]}: {row[1]}개")

    # 샘플 데이터 확인
    print("\n   샘플 laws (3개):")
    cursor.execute("""
        SELECT title, doc_type, total_articles
        FROM laws
        LIMIT 3
    """)
    for row in cursor.fetchall():
        print(f"     - {row[0]} ({row[1]}): {row[2]}개 조항")

    # 특정 조문 검색 테스트
    print("\n   특정 조문 검색 테스트:")
    test_cases = [
        ("주택임대차보호법", "제7조"),
        ("부동산등기법", "제73조"),
        ("공인중개사법", "제33조"),
    ]

    for law_title, article_number in test_cases:
        cursor.execute("""
            SELECT a.chunk_ids
            FROM articles a
            JOIN laws l ON a.law_id = l.law_id
            WHERE l.title LIKE ? AND a.article_number = ?
        """, (f"%{law_title}%", article_number))

        result = cursor.fetchone()
        if result:
            chunk_ids = json.loads(result[0])
            print(f"     [{law_title} {article_number}] {len(chunk_ids)}개 청크 발견")
        else:
            print(f"     [{law_title} {article_number}] 없음")

    print("\n[OK] 검증 완료\n")


def main():
    print("="*60)
    print("SQLite DB 생성 시작")
    print("="*60 + "\n")

    # 기존 DB 백업
    if SQLITE_PATH.exists():
        backup_path = SQLITE_PATH.parent / f"legal_metadata_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy2(SQLITE_PATH, backup_path)
        print(f"[OK] 기존 DB 백업: {backup_path}\n")
        SQLITE_PATH.unlink()

    # 1. ChromaDB에서 메타데이터 추출
    all_data = extract_from_chromadb()

    # 2. 법령별로 그룹화
    laws_dict = group_by_law(all_data)

    # 3. SQLite DB 생성
    conn = sqlite3.connect(SQLITE_PATH)
    create_tables(conn)

    # 4. 데이터 삽입
    law_count, article_count = insert_into_sqlite(conn, laws_dict)

    # 5. 검증
    verify_database(conn)

    conn.close()

    print("="*60)
    print("SQLite DB 생성 완료!")
    print("="*60)
    print(f"파일 위치: {SQLITE_PATH}")
    print(f"laws: {law_count}개")
    print(f"articles: {article_count}개")
    print("="*60)


if __name__ == "__main__":
    from datetime import datetime
    main()
