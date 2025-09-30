import sqlite3
import json
import os

# --- 설정 변수 ---

# 데이터 파일이 위치한 기본 경로
BASE_DATA_PATH = '.'
# 생성할 SQLite 데이터베이스 파일 이름
DB_NAME = 'metadata.db'

# --- 데이터베이스 및 테이블 생성 ---

def create_database_and_tables(conn):
    """SQLite 데이터베이스와 기본 테이블 3개를 생성합니다."""
    cursor = conn.cursor()

    # 1. documents 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            doc_type TEXT,
            doc_number TEXT,
            category_name TEXT,
            enforcement_date DATE,
            total_chunks INTEGER,
            file_path TEXT,
            FOREIGN KEY (category_name) REFERENCES categories (category_name)
        )
    ''')
    print("'documents' 테이블 생성 완료.")

    # 2. categories 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_name TEXT PRIMARY KEY,
            description TEXT,
            domains TEXT,
            keywords TEXT
        )
    ''')
    print("'categories' 테이블 생성 완료.")

    # 3. document_relationships 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_relationships (
            relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_doc_id TEXT NOT NULL,
            related_doc_id TEXT NOT NULL,
            relationship_type TEXT,
            FOREIGN KEY (base_doc_id) REFERENCES documents (doc_id),
            FOREIGN KEY (related_doc_id) REFERENCES documents (doc_id)
        )
    ''')
    print("'document_relationships' 테이블 생성 완료.")

    conn.commit()

# --- 데이터 삽입 함수 ---

def insert_categories_data(conn, base_path):
    """category_taxonomy.json 파일의 데이터를 'categories' 테이블에 삽입합니다."""
    file_path = os.path.join(base_path, 'metadata_index', 'category_taxonomy.json')
    cursor = conn.cursor()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for category_key, details in data.get('categories', {}).items():
            cursor.execute('''
                INSERT OR REPLACE INTO categories (category_name, description, domains, keywords)
                VALUES (?, ?, ?, ?)
            ''', (
                category_key,
                details.get('description'),
                json.dumps(details.get('domains', []), ensure_ascii=False), # 리스트를 JSON 문자열로 저장
                json.dumps(details.get('keywords', []), ensure_ascii=False)
            ))
        conn.commit()
        print(f"{cursor.rowcount}개의 카테고리 정보 삽입 완료.")
    except FileNotFoundError:
        print(f"Error: '{file_path}' 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' 파일이 유효한 JSON 형식이 아닙니다.")


def insert_documents_data(conn, base_path):
    """metadata_index.json 파일의 데이터를 'documents' 테이블에 삽입합니다."""
    file_path = os.path.join(base_path, 'metadata_index.json')
    cursor = conn.cursor()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for doc in data.get('documents', []):
            cursor.execute('''
                INSERT OR REPLACE INTO documents (doc_id, title, doc_type, doc_number, category_name, enforcement_date, total_chunks, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc.get('doc_id'),
                doc.get('title'),
                doc.get('doc_type'),
                doc.get('doc_number'),
                doc.get('category'),
                doc.get('enforcement_date'),
                doc.get('chunks'),
                doc.get('file_path')
            ))
        conn.commit()
        print(f"{cursor.rowcount}개의 문서 정보 삽입 완료.")
    except FileNotFoundError:
        print(f"Error: '{file_path}' 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' 파일이 유효한 JSON 형식이 아닙니다.")


def insert_relationships_data(conn, base_path):
    """document_registry.json 파일의 데이터를 'document_relationships' 테이블에 삽입합니다."""
    file_path = os.path.join(base_path, 'metadata_index', 'document_registry.json')
    cursor = conn.cursor()

    # 문서 제목을 doc_id로 변환하기 위한 맵 생성
    cursor.execute("SELECT title, doc_id FROM documents")
    title_to_id_map = {row[0].strip(): row[1] for row in cursor.fetchall()}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        relationships_inserted = 0
        for rel in data.get('document_relationships', []):
            base_title = rel.get('base_document', '').strip()
            # 약칭 제거 (예: " ( 약칭: ...)")
            base_title = base_title.split(' ( 약칭:')[0].strip()
            base_doc_id = title_to_id_map.get(base_title)

            if not base_doc_id:
                print(f"Warning: 기준 문서 '{base_title}'에 해당하는 doc_id를 찾을 수 없습니다. 건너뜁니다.")
                continue

            for related_doc in rel.get('related_documents', []):
                related_title = related_doc.get('title', '').strip()
                related_title = related_title.split(' ( 약칭:')[0].strip()
                related_doc_id = title_to_id_map.get(related_title)

                if not related_doc_id:
                    print(f"Warning: 관련 문서 '{related_title}'에 해당하는 doc_id를 찾을 수 없습니다. 건너뜁니다.")
                    continue
                
                # 관계 유형은 "관련문서"로 통일하거나 필요 시 로직 추가
                relationship_type = "관련문서"
                
                cursor.execute('''
                    INSERT INTO document_relationships (base_doc_id, related_doc_id, relationship_type)
                    VALUES (?, ?, ?)
                ''', (base_doc_id, related_doc_id, relationship_type))
                relationships_inserted += 1

        conn.commit()
        print(f"{relationships_inserted}개의 문서 관계 정보 삽입 완료.")
    except FileNotFoundError:
        print(f"Error: '{file_path}' 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' 파일이 유효한 JSON 형식이 아닙니다.")


def main():
    """메인 실행 함수: DB 연결, 테이블 생성, 데이터 삽입"""
    
    # 기존 DB 파일이 있다면 삭제하여 매번 새로 생성
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"기존 '{DB_NAME}' 파일을 삭제했습니다.")

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        print(f"SQLite 데이터베이스 '{DB_NAME}'에 성공적으로 연결했습니다.")
        
        print("\n--- 1. 테이블 생성 시작 ---")
        create_database_and_tables(conn)
        
        print("\n--- 2. 데이터 삽입 시작 ---")
        # 데이터 삽입 순서가 중요 (참조 무결성)
        insert_categories_data(conn, BASE_DATA_PATH)
        insert_documents_data(conn, BASE_DATA_PATH)
        insert_relationships_data(conn, BASE_DATA_PATH)
        
        print("\n--- 모든 작업이 완료되었습니다. ---")

    except sqlite3.Error as e:
        print(f"데이터베이스 작업 중 오류 발생: {e}")
    finally:
        if conn:
            conn.close()
            print(f"\n데이터베이스 연결을 닫았습니다.")

if __name__ == '__main__':
    main()