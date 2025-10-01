"""
ChromaDB 직접 사용 예제 (LangGraph 에이전트용)
FastAPI 없이 소스코드 레벨에서 ChromaDB 사용
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path
import json
from typing import List, Dict, Optional, Any


class LegalSearchAgent:
    """법률 검색 에이전트 (ChromaDB 직접 사용)"""

    def __init__(self):
        """초기화"""
        # ChromaDB 연결
        chroma_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\legal_info\chroma_db")
        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # 컬렉션 가져오기
        self.collection = self.client.get_collection("korean_legal_documents")

        # 임베딩 모델 로드
        model_path = Path(r"C:\kdy\Projects\holmesnyangz\beta_v001\backend\data\storage\kure_v1")
        self.embedding_model = SentenceTransformer(str(model_path))

        print(f"[초기화 완료] ChromaDB 문서 수: {self.collection.count()}")

    def extract_doc_type(self, source_file: str) -> str:
        """파일명에서 문서 타입 추출"""
        if '시행규칙' in source_file:
            return '시행규칙'
        elif '시행령' in source_file:
            return '시행령'
        elif '법률' in source_file or '법(' in source_file:
            return '법률'
        elif '대법원규칙' in source_file or '법원규칙' in source_file:
            return '대법원규칙'
        elif '용어' in source_file:
            return '용어집'
        return '기타'

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        법률 문서 검색

        Args:
            query: 검색 쿼리
            category: 카테고리 ("1_공통 매매_임대차", "2_임대차_전세_월세" 등)
            is_tenant_protection: 임차인 보호 조항 여부
            is_tax_related: 세금 관련 여부
            n_results: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """

        # 쿼리 임베딩 생성
        query_embedding = self.embedding_model.encode([query])

        # 필터 구성
        where_clause = self._build_where_clause(
            category=category,
            is_tenant_protection=is_tenant_protection,
            is_tax_related=is_tax_related
        )

        # ChromaDB 검색
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 포맷팅
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]

            # 문서 타입 추출
            doc_type = self.extract_doc_type(metadata.get('source_file', ''))

            # 참조 파싱
            references = self._parse_references(metadata)

            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'doc_type': doc_type,
                'similarity': 1 - results['distances'][0][i],
                'metadata': {
                    'category': metadata.get('category', ''),
                    'article_number': metadata.get('article_number', ''),
                    'article_title': metadata.get('article_title', ''),
                    'chapter': metadata.get('chapter', ''),
                    'enforcement_date': metadata.get('enforcement_date', ''),
                    'law_title': metadata.get('law_title', ''),
                    'decree_title': metadata.get('decree_title', ''),
                    'rule_title': metadata.get('rule_title', ''),
                    'source_file': metadata.get('source_file', ''),
                    'law_references': references['law_references'],
                    'decree_references': references['decree_references'],
                    'form_references': references['form_references'],
                }
            })

        return formatted_results

    def search_by_doc_type(
        self,
        query: str,
        doc_type: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        특정 문서 타입만 검색

        Args:
            query: 검색 쿼리
            doc_type: 문서 타입 ("법률", "시행령", "시행규칙", "용어집" 등)
            n_results: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """
        # 더 많은 결과를 가져온 후 필터링
        all_results = self.search(query, n_results=n_results * 3)

        # 문서 타입 필터링
        filtered = [r for r in all_results if r['doc_type'] == doc_type]

        return filtered[:n_results]

    def get_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 특정 청크 조회

        Args:
            chunk_id: 청크 ID (예: "chunk_1")

        Returns:
            문서 정보 또는 None
        """
        try:
            result = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas"]
            )

            if result['ids']:
                metadata = result['metadatas'][0]
                return {
                    'id': result['ids'][0],
                    'text': result['documents'][0],
                    'doc_type': self.extract_doc_type(metadata.get('source_file', '')),
                    'metadata': metadata
                }
        except:
            pass

        return None

    def get_related_articles(
        self,
        article_id: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        특정 조항과 관련된 조항 찾기

        Args:
            article_id: 조항 ID
            n_results: 반환할 결과 수

        Returns:
            관련 조항 리스트
        """
        # 원본 조항 가져오기
        article = self.get_by_id(article_id)
        if not article:
            return []

        # 원본 텍스트로 유사 조항 검색
        return self.search(
            query=article['text'][:200],  # 앞부분만 사용
            n_results=n_results + 1  # 자기 자신 포함
        )[1:]  # 자기 자신 제외

    def _build_where_clause(
        self,
        category: Optional[str] = None,
        is_tenant_protection: Optional[bool] = None,
        is_tax_related: Optional[bool] = None
    ) -> Optional[Dict]:
        """필터 조건 생성"""
        conditions = []

        # 삭제된 문서 제외 (항상)
        conditions.append({"is_deleted": {"$eq": False}})

        # 카테고리 필터
        if category:
            conditions.append({"category": {"$eq": category}})

        # Boolean 필터
        if is_tenant_protection is not None:
            conditions.append({"is_tenant_protection": {"$eq": is_tenant_protection}})

        if is_tax_related is not None:
            conditions.append({"is_tax_related": {"$eq": is_tax_related}})

        # 조건 결합
        if len(conditions) == 0:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _parse_references(self, metadata: Dict) -> Dict[str, List[str]]:
        """참조 필드 파싱"""
        references = {}

        for ref_type in ['law_references', 'decree_references', 'form_references']:
            ref_value = metadata.get(ref_type, '[]')
            if isinstance(ref_value, str):
                try:
                    references[ref_type] = json.loads(ref_value)
                except:
                    references[ref_type] = []
            else:
                references[ref_type] = ref_value if ref_value else []

        return references


# ========================================
# 사용 예시
# ========================================

def main():
    """사용 예시"""

    print("=" * 60)
    print("ChromaDB 법률 검색 예시")
    print("=" * 60)

    # 에이전트 초기화
    agent = LegalSearchAgent()

    # ----------------------------------------
    # 예시 1: 기본 검색
    # ----------------------------------------
    print("\n[예시 1] 기본 검색: '임차인 보호'")
    results = agent.search("임차인 보호", n_results=3)

    for i, r in enumerate(results, 1):
        print(f"\n{i}. 문서 타입: {r['doc_type']}")
        print(f"   유사도: {r['similarity']:.3f}")
        print(f"   조항: {r['metadata']['article_number']} {r['metadata']['article_title']}")
        print(f"   내용: {r['text'][:80]}...")

    # ----------------------------------------
    # 예시 2: 카테고리 필터링
    # ----------------------------------------
    print("\n" + "=" * 60)
    print("[예시 2] 카테고리 검색: '전세 계약' in '임대차·전세·월세'")
    results = agent.search(
        query="전세 계약",
        category="2_임대차_전세_월세",
        n_results=3
    )

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['metadata']['article_number']} - {r['metadata']['article_title']}")
        print(f"   카테고리: {r['metadata']['category']}")
        print(f"   유사도: {r['similarity']:.3f}")

    # ----------------------------------------
    # 예시 3: 임차인 보호 조항만
    # ----------------------------------------
    print("\n" + "=" * 60)
    print("[예시 3] 임차인 보호 조항: '보증금 반환'")
    results = agent.search(
        query="보증금 반환",
        is_tenant_protection=True,
        n_results=3
    )

    print(f"\n총 {len(results)}개 결과")
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['metadata']['law_title'] or r['metadata']['decree_title']}")
        print(f"   {r['metadata']['article_number']} - {r['metadata']['article_title']}")
        print(f"   유사도: {r['similarity']:.3f}")

    # ----------------------------------------
    # 예시 4: 특정 문서 타입만
    # ----------------------------------------
    print("\n" + "=" * 60)
    print("[예시 4] 법률 문서만: '공인중개사 자격'")
    results = agent.search_by_doc_type(
        query="공인중개사 자격",
        doc_type="법률",
        n_results=3
    )

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['doc_type']} - {r['metadata']['law_title']}")
        print(f"   {r['metadata']['article_number']}: {r['text'][:80]}...")

    # ----------------------------------------
    # 예시 5: ID로 조회
    # ----------------------------------------
    print("\n" + "=" * 60)
    print("[예시 5] ID로 조회: 'chunk_1'")
    article = agent.get_by_id("chunk_1")

    if article:
        print(f"\n문서 타입: {article['doc_type']}")
        print(f"조항: {article['metadata'].get('article_number')}")
        print(f"내용: {article['text'][:100]}...")

    # ----------------------------------------
    # 예시 6: 관련 조항 찾기
    # ----------------------------------------
    print("\n" + "=" * 60)
    print("[예시 6] 'chunk_1'과 관련된 조항")
    related = agent.get_related_articles("chunk_1", n_results=3)

    for i, r in enumerate(related, 1):
        print(f"\n{i}. {r['metadata']['article_number']}")
        print(f"   유사도: {r['similarity']:.3f}")
        print(f"   내용: {r['text'][:60]}...")

    print("\n" + "=" * 60)
    print("예시 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()