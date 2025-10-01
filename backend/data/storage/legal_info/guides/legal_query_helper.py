"""
Legal Metadata Query Helper
Provides fast filtering and metadata queries for LangGraph agents
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta


class LegalQueryHelper:
    """Helper class for querying legal metadata SQLite database"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info")
            db_path = str(base_path / "sqlite_db" / "legal_metadata.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # === Law Information Queries ===

    def get_law_by_title(self, title: str, fuzzy: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get law information by title

        Args:
            title: Law title (exact or partial)
            fuzzy: If True, use LIKE search; if False, exact match

        Returns:
            Law information dict or None
        """
        cursor = self.conn.cursor()

        if fuzzy:
            result = cursor.execute("""
                SELECT * FROM laws
                WHERE title LIKE ?
                LIMIT 1
            """, (f'%{title}%',)).fetchone()
        else:
            result = cursor.execute("""
                SELECT * FROM laws
                WHERE title = ?
                LIMIT 1
            """, (title,)).fetchone()

        return dict(result) if result else None

    def get_law_total_articles(self, title: str) -> Optional[int]:
        """
        특정 법률이 몇 조까지 있는지 조회

        Args:
            title: 법률명 (부분 일치)

        Returns:
            총 조항 수
        """
        law = self.get_law_by_title(title, fuzzy=True)
        return law['total_articles'] if law else None

    def get_law_last_article(self, title: str) -> Optional[str]:
        """
        특정 법률의 마지막 조항 번호

        Args:
            title: 법률명

        Returns:
            마지막 조항 번호 (예: '제50조')
        """
        law = self.get_law_by_title(title, fuzzy=True)
        return law['last_article'] if law else None

    def get_law_enforcement_date(self, title: str) -> Optional[str]:
        """
        특정 법률의 시행일

        Args:
            title: 법률명

        Returns:
            시행일 (예: '2024. 12. 27.')
        """
        law = self.get_law_by_title(title, fuzzy=True)
        return law['enforcement_date'] if law else None

    def get_laws_by_enforcement_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        시행일 범위로 법률 검색

        Args:
            start_date: 시작일 (예: '2024. 1. 1.')
            end_date: 종료일 (예: '2024. 12. 31.')

        Returns:
            법률 정보 리스트
        """
        cursor = self.conn.cursor()

        results = cursor.execute("""
            SELECT * FROM laws
            WHERE enforcement_date BETWEEN ? AND ?
            ORDER BY enforcement_date
        """, (start_date, end_date)).fetchall()

        return [dict(row) for row in results]

    def get_laws_by_similar_enforcement_date(
        self,
        reference_title: str,
        days_before: int = 30,
        days_after: int = 30
    ) -> List[Dict[str, Any]]:
        """
        특정 법률 시행일과 비슷한 시기에 시행된 법률들 찾기

        Args:
            reference_title: 기준 법률명
            days_before: 기준일 이전 일수
            days_after: 기준일 이후 일수

        Returns:
            비슷한 시기에 시행된 법률 리스트
        """
        # Get reference law's enforcement date
        law = self.get_law_by_title(reference_title, fuzzy=True)
        if not law or not law['enforcement_date']:
            return []

        ref_date = law['enforcement_date']

        # Parse Korean date format (예: '2024. 12. 27.')
        try:
            # Simple string-based range for Korean date format
            # This is approximate - for exact date arithmetic, would need date parsing
            cursor = self.conn.cursor()

            results = cursor.execute("""
                SELECT * FROM laws
                WHERE enforcement_date IS NOT NULL
                  AND enforcement_date != ''
                  AND title != ?
                ORDER BY enforcement_date
            """, (law['title'],)).fetchall()

            # Return all for now - could implement exact date filtering if needed
            return [dict(row) for row in results]

        except:
            return []

    def get_laws_by_doc_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """
        문서 타입별 법률 검색

        Args:
            doc_type: 법률/시행령/시행규칙/대법원규칙/용어집/기타

        Returns:
            법률 정보 리스트
        """
        cursor = self.conn.cursor()

        results = cursor.execute("""
            SELECT * FROM laws
            WHERE doc_type = ?
            ORDER BY title
        """, (doc_type,)).fetchall()

        return [dict(row) for row in results]

    def get_laws_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        카테고리별 법률 검색

        Args:
            category: 카테고리명

        Returns:
            법률 정보 리스트
        """
        cursor = self.conn.cursor()

        results = cursor.execute("""
            SELECT * FROM laws
            WHERE category = ?
            ORDER BY title
        """, (category,)).fetchall()

        return [dict(row) for row in results]

    # === Article Queries ===

    def get_articles_by_law(
        self,
        title: str,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        특정 법률의 모든 조항 조회

        Args:
            title: 법률명
            include_deleted: 삭제된 조항 포함 여부

        Returns:
            조항 정보 리스트
        """
        law = self.get_law_by_title(title, fuzzy=True)
        if not law:
            return []

        cursor = self.conn.cursor()

        if include_deleted:
            query = """
                SELECT * FROM articles
                WHERE law_id = ?
                ORDER BY article_number
            """
        else:
            query = """
                SELECT * FROM articles
                WHERE law_id = ? AND is_deleted = 0
                ORDER BY article_number
            """

        results = cursor.execute(query, (law['law_id'],)).fetchall()
        return [dict(row) for row in results]

    def get_article_chunk_ids(self, title: str, article_number: str) -> List[str]:
        """
        특정 조항의 ChromaDB chunk ID 조회

        Args:
            title: 법률명
            article_number: 조항 번호 (예: '제1조')

        Returns:
            ChromaDB chunk ID 리스트
        """
        law = self.get_law_by_title(title, fuzzy=True)
        if not law:
            return []

        cursor = self.conn.cursor()

        result = cursor.execute("""
            SELECT chunk_ids FROM articles
            WHERE law_id = ? AND article_number = ?
        """, (law['law_id'], article_number)).fetchone()

        if result and result['chunk_ids']:
            return json.loads(result['chunk_ids'])
        return []

    def get_special_articles(
        self,
        article_type: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        특수 조항 검색 (임차인 보호, 세금, 위임, 벌칙)

        Args:
            article_type: tenant_protection/tax_related/delegation/penalty_related
            category: 선택적 카테고리 필터

        Returns:
            조항 정보 리스트 (with law info)
        """
        cursor = self.conn.cursor()

        field_map = {
            'tenant_protection': 'is_tenant_protection',
            'tax_related': 'is_tax_related',
            'delegation': 'is_delegation',
            'penalty_related': 'is_penalty_related'
        }

        field = field_map.get(article_type)
        if not field:
            return []

        if category:
            query = f"""
                SELECT a.*, l.title as law_title, l.doc_type, l.category
                FROM articles a
                JOIN laws l ON a.law_id = l.law_id
                WHERE a.{field} = 1 AND l.category = ?
                ORDER BY l.title, a.article_number
            """
            results = cursor.execute(query, (category,)).fetchall()
        else:
            query = f"""
                SELECT a.*, l.title as law_title, l.doc_type, l.category
                FROM articles a
                JOIN laws l ON a.law_id = l.law_id
                WHERE a.{field} = 1
                ORDER BY l.title, a.article_number
            """
            results = cursor.execute(query).fetchall()

        return [dict(row) for row in results]

    # === Filter Generation for ChromaDB ===

    def build_chromadb_filter(
        self,
        doc_type: Optional[str] = None,
        category: Optional[str] = None,
        law_title: Optional[str] = None,
        article_type: Optional[str] = None,
        exclude_deleted: bool = True
    ) -> Dict[str, Any]:
        """
        ChromaDB 검색용 필터 생성

        Args:
            doc_type: 문서 타입
            category: 카테고리
            law_title: 법률명
            article_type: 특수 조항 타입
            exclude_deleted: 삭제 조항 제외

        Returns:
            ChromaDB where 필터
        """
        filters = []

        if doc_type:
            filters.append({"doc_type": doc_type})

        if category:
            filters.append({"category": category})

        if law_title:
            # Find exact law title from database
            law = self.get_law_by_title(law_title, fuzzy=True)
            if law:
                # Use appropriate field based on doc_type
                if law['doc_type'] == '법률':
                    filters.append({"law_title": law['title']})
                elif law['doc_type'] == '시행령':
                    filters.append({"decree_title": law['title']})
                elif law['doc_type'] == '시행규칙':
                    filters.append({"rule_title": law['title']})

        if article_type:
            field_map = {
                'tenant_protection': 'is_tenant_protection',
                'tax_related': 'is_tax_related',
                'delegation': 'is_delegation',
                'penalty_related': 'is_penalty_related'
            }
            field = field_map.get(article_type)
            if field:
                filters.append({field: True})  # Boolean, not string

        if exclude_deleted:
            filters.append({"is_deleted": False})  # Boolean, not string

        # Combine filters
        if len(filters) == 0:
            return {}
        elif len(filters) == 1:
            return filters[0]
        else:
            return {"$and": filters}

    def get_chunk_ids_for_law(
        self,
        title: str,
        include_deleted: bool = False
    ) -> List[str]:
        """
        특정 법률의 모든 chunk ID 가져오기

        Args:
            title: 법률명
            include_deleted: 삭제 조항 포함 여부

        Returns:
            ChromaDB chunk ID 리스트
        """
        articles = self.get_articles_by_law(title, include_deleted)
        chunk_ids = []

        for article in articles:
            if article['chunk_ids']:
                chunk_ids.extend(json.loads(article['chunk_ids']))

        return chunk_ids

    # === Search Helpers ===

    def search_laws(self, keyword: str) -> List[Dict[str, Any]]:
        """
        법률명 검색

        Args:
            keyword: 검색 키워드

        Returns:
            매칭되는 법률 리스트
        """
        cursor = self.conn.cursor()

        results = cursor.execute("""
            SELECT * FROM laws
            WHERE title LIKE ?
            ORDER BY title
        """, (f'%{keyword}%',)).fetchall()

        return [dict(row) for row in results]

    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        cursor = self.conn.cursor()

        stats = {}

        # Total counts
        stats['total_laws'] = cursor.execute("SELECT COUNT(*) FROM laws").fetchone()[0]
        stats['total_articles'] = cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

        # By doc_type
        stats['by_doc_type'] = {}
        for row in cursor.execute("SELECT doc_type, COUNT(*) as count FROM laws GROUP BY doc_type"):
            stats['by_doc_type'][row[0]] = row[1]

        # By category
        stats['by_category'] = {}
        for row in cursor.execute("SELECT category, COUNT(*) as count FROM laws GROUP BY category"):
            stats['by_category'][row[0]] = row[1]

        return stats


# === Convenience Functions ===

def quick_query(question: str) -> Optional[str]:
    """
    자연어 질문에 대한 빠른 답변

    Args:
        question: 사용자 질문

    Returns:
        답변 문자열
    """
    with LegalQueryHelper() as helper:
        # "~이 몇 조까지?"
        if '몇 조' in question or '몇조' in question:
            for law in helper.search_laws(''):
                if law['title'] in question:
                    return f"{law['title']}은(는) 총 {law['total_articles']}개 조항이 있으며, 마지막 조항은 {law['last_article']}입니다."

        # "언제 시행?"
        if '언제' in question and ('시행' in question or '발효' in question):
            for law in helper.search_laws(''):
                if law['title'] in question:
                    return f"{law['title']}의 시행일은 {law['enforcement_date']}입니다."

    return None


if __name__ == "__main__":
    # Example usage
    with LegalQueryHelper() as helper:
        print("=== Legal Query Helper Examples ===\n")

        # Example 1: 법률 정보 조회
        print("1. 공인중개사법은 몇 조까지?")
        total = helper.get_law_total_articles("공인중개사법")
        last = helper.get_law_last_article("공인중개사법")
        print(f"   총 {total}개 조항, 마지막: {last}\n")

        # Example 2: 시행일 조회
        print("2. 공인중개사법 시행일은?")
        date = helper.get_law_enforcement_date("공인중개사법")
        print(f"   시행일: {date}\n")

        # Example 3: 특수 조항 검색
        print("3. 임차인 보호 조항 검색")
        articles = helper.get_special_articles("tenant_protection")
        print(f"   총 {len(articles)}개 조항 발견\n")

        # Example 4: ChromaDB 필터 생성
        print("4. ChromaDB 필터 생성 (법률 + 임대차 카테고리)")
        filter_dict = helper.build_chromadb_filter(
            doc_type="법률",
            category="2_임대차_전세_월세",
            exclude_deleted=True
        )
        print(f"   필터: {filter_dict}\n")

        # Example 5: 통계
        print("5. 데이터베이스 통계")
        stats = helper.get_statistics()
        print(f"   총 법률: {stats['total_laws']}")
        print(f"   총 조항: {stats['total_articles']}")
