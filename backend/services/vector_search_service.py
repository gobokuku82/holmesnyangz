"""
Vector Search Service
벡터 검색 서비스 (청약 통계, 대출 정보 등)
"""

import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

logger = logging.getLogger(__name__)


class VectorSearchService:
    """
    벡터 기반 검색 서비스
    TF-IDF 벡터화 및 코사인 유사도 기반 검색
    """
    
    def __init__(self, mock_data_path: str = "database/mockup"):
        """
        Args:
            mock_data_path: Mock 데이터 디렉토리 경로
        """
        self.data_path = Path(mock_data_path)
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.9
        )
        self.vectors = {}
        self.documents = {}
        self.metadata = {}
        
        self._initialize_vectors()
    
    def _initialize_vectors(self):
        """벡터 데이터 초기화"""
        # 청약 통계 데이터 벡터화
        self._vectorize_subscription_stats()
        
        # 대출 정보 벡터화
        self._vectorize_loan_info()
        
        logger.info("Vector search service initialized")
    
    def _vectorize_subscription_stats(self):
        """청약 통계 데이터 벡터화"""
        try:
            file_path = self.data_path / "subscription_statistics.json"
            if not file_path.exists():
                logger.warning("Subscription statistics file not found")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 문서 생성
            documents = []
            metadata = []
            
            # 청약 결과 벡터화
            for item in data.get("subscription_results", []):
                doc_text = self._create_subscription_document(item)
                documents.append(doc_text)
                metadata.append({
                    "type": "subscription_result",
                    "id": item.get("id"),
                    "data": item
                })
            
            # 당첨 패턴 벡터화
            for pattern in data.get("winning_patterns", []):
                doc_text = self._create_pattern_document(pattern)
                documents.append(doc_text)
                metadata.append({
                    "type": "winning_pattern",
                    "id": pattern.get("id"),
                    "data": pattern
                })
            
            # 지역 통계 벡터화
            for stat in data.get("regional_statistics", []):
                doc_text = self._create_regional_stat_document(stat)
                documents.append(doc_text)
                metadata.append({
                    "type": "regional_stat",
                    "region": stat.get("region"),
                    "data": stat
                })
            
            if documents:
                # TF-IDF 벡터화
                vectors = self.vectorizer.fit_transform(documents)
                self.vectors["subscription"] = vectors
                self.documents["subscription"] = documents
                self.metadata["subscription"] = metadata
                
                logger.info(f"Vectorized {len(documents)} subscription documents")
        
        except Exception as e:
            logger.error(f"Failed to vectorize subscription stats: {e}")
    
    def _vectorize_loan_info(self):
        """대출 정보 벡터화"""
        try:
            file_path = self.data_path / "loan_info.json"
            if not file_path.exists():
                logger.warning("Loan info file not found")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            metadata = []
            
            # 대출 상품 벡터화
            for product in data.get("loan_products", []):
                doc_text = self._create_loan_document(product)
                documents.append(doc_text)
                metadata.append({
                    "type": "loan_product",
                    "id": product.get("id"),
                    "bank": product.get("bank"),
                    "data": product
                })
            
            # 정부 대출 벡터화
            for loan in data.get("government_loans", []):
                doc_text = self._create_government_loan_document(loan)
                documents.append(doc_text)
                metadata.append({
                    "type": "government_loan",
                    "name": loan.get("name"),
                    "data": loan
                })
            
            if documents:
                # 별도의 벡터라이저 사용 (대출 전용)
                loan_vectorizer = TfidfVectorizer(
                    max_features=500,
                    ngram_range=(1, 2),
                    min_df=1
                )
                vectors = loan_vectorizer.fit_transform(documents)
                self.vectors["loan"] = vectors
                self.documents["loan"] = documents
                self.metadata["loan"] = metadata
                self.vectorizer_loan = loan_vectorizer
                
                logger.info(f"Vectorized {len(documents)} loan documents")
        
        except Exception as e:
            logger.error(f"Failed to vectorize loan info: {e}")
    
    def _create_subscription_document(self, item: Dict[str, Any]) -> str:
        """청약 결과를 문서로 변환"""
        parts = [
            item.get("complex_name", ""),
            item.get("location", {}).get("city", ""),
            item.get("location", {}).get("district", ""),
            item.get("location", {}).get("dong", ""),
            item.get("developer", ""),
            f"경쟁률 {item.get('competition_rates', {}).get('overall', '')}",
            f"가점 {item.get('cutoff_scores', {}).get('84㎡_1순위', '')}점"
        ]
        
        # 분석 내용 추가
        analysis = item.get("analysis", {})
        if isinstance(analysis, dict):
            parts.extend([
                analysis.get("reason", ""),
                analysis.get("recommendation", "")
            ])
        
        return " ".join(str(p) for p in parts if p)
    
    def _create_pattern_document(self, pattern: Dict[str, Any]) -> str:
        """당첨 패턴을 문서로 변환"""
        parts = [
            pattern.get("pattern_name", ""),
            json.dumps(pattern.get("characteristics", {}), ensure_ascii=False),
            f"당첨률 {pattern.get('winning_rate', '')}%",
            " ".join(pattern.get("applicable_areas", [])),
            " ".join(pattern.get("tips", []))
        ]
        
        return " ".join(str(p) for p in parts if p)
    
    def _create_regional_stat_document(self, stat: Dict[str, Any]) -> str:
        """지역 통계를 문서로 변환"""
        parts = [
            stat.get("region", ""),
            stat.get("period", ""),
            f"공급 {stat.get('stats', {}).get('total_supply', '')}",
            f"평균경쟁률 {stat.get('stats', {}).get('avg_competition', '')}",
            f"평균가점 {stat.get('stats', {}).get('avg_cutoff_score', '')}",
            " ".join(stat.get("trends", {}).get("hot_areas", []))
        ]
        
        return " ".join(str(p) for p in parts if p)
    
    def _create_loan_document(self, product: Dict[str, Any]) -> str:
        """대출 상품을 문서로 변환"""
        parts = [
            product.get("bank", ""),
            product.get("product_name", ""),
            product.get("type", ""),
            product.get("target", ""),
            f"금리 {product.get('interest_rates', {}).get('variable', {}).get('min', '')}~{product.get('interest_rates', {}).get('variable', {}).get('max', '')}%",
            f"LTV {product.get('ltv', '')}",
            f"DTI {product.get('dti', '')}",
            f"DSR {product.get('dsr', '')}",
            " ".join(product.get("special_conditions", []))
        ]
        
        return " ".join(str(p) for p in parts if p)
    
    def _create_government_loan_document(self, loan: Dict[str, Any]) -> str:
        """정부 대출을 문서로 변환"""
        parts = [
            loan.get("name", ""),
            loan.get("provider", ""),
            loan.get("type", ""),
            loan.get("target", ""),
            " ".join(loan.get("features", [])),
            f"한도 {loan.get('limit', '')}",
            f"LTV {loan.get('ltv', '')}"
        ]
        
        # 금리 정보 추가
        rates = loan.get("rates", {})
        if isinstance(rates, dict):
            for key, value in rates.items():
                parts.append(f"{key} {value}")
        
        return " ".join(str(p) for p in parts if p)
    
    def search_subscription(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        청약 관련 벡터 검색
        
        Args:
            query: 검색 쿼리
            top_k: 상위 결과 개수
            min_similarity: 최소 유사도 임계값
        """
        if "subscription" not in self.vectors:
            logger.warning("No subscription vectors available")
            return []
        
        try:
            # 쿼리 벡터화
            query_vector = self.vectorizer.transform([query])
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_vector, self.vectors["subscription"]).flatten()
            
            # 상위 k개 선택
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] >= min_similarity:
                    meta = self.metadata["subscription"][idx]
                    results.append({
                        "score": float(similarities[idx]),
                        "type": meta["type"],
                        "data": meta["data"]
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_loan(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        대출 관련 벡터 검색
        
        Args:
            query: 검색 쿼리
            top_k: 상위 결과 개수
            min_similarity: 최소 유사도 임계값
        """
        if "loan" not in self.vectors or not hasattr(self, 'vectorizer_loan'):
            logger.warning("No loan vectors available")
            return []
        
        try:
            # 쿼리 벡터화
            query_vector = self.vectorizer_loan.transform([query])
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_vector, self.vectors["loan"]).flatten()
            
            # 상위 k개 선택
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] >= min_similarity:
                    meta = self.metadata["loan"][idx]
                    results.append({
                        "score": float(similarities[idx]),
                        "type": meta["type"],
                        "data": meta["data"]
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        category: str = "subscription",
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (키워드 + 벡터)
        
        Args:
            query: 검색 쿼리
            category: 검색 카테고리 (subscription, loan)
            keyword_weight: 키워드 검색 가중치
            vector_weight: 벡터 검색 가중치
            top_k: 상위 결과 개수
        """
        results = []
        
        # 벡터 검색
        if category == "subscription":
            vector_results = self.search_subscription(query, top_k * 2)
        elif category == "loan":
            vector_results = self.search_loan(query, top_k * 2)
        else:
            vector_results = []
        
        # 키워드 매칭 점수 계산
        query_lower = query.lower()
        for result in vector_results:
            # 키워드 매칭 점수
            data_str = json.dumps(result["data"], ensure_ascii=False).lower()
            keyword_score = sum(1 for word in query_lower.split() if word in data_str) / len(query_lower.split())
            
            # 하이브리드 점수 계산
            hybrid_score = (keyword_weight * keyword_score + 
                          vector_weight * result["score"])
            
            results.append({
                "score": hybrid_score,
                "vector_score": result["score"],
                "keyword_score": keyword_score,
                "type": result["type"],
                "data": result["data"]
            })
        
        # 하이브리드 점수로 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    def get_similar_items(
        self,
        item_id: str,
        category: str = "subscription",
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        유사 아이템 검색
        
        Args:
            item_id: 기준 아이템 ID
            category: 카테고리
            top_k: 상위 결과 개수
        """
        if category not in self.metadata:
            return []
        
        # 아이템 인덱스 찾기
        item_idx = None
        for idx, meta in enumerate(self.metadata[category]):
            if meta.get("id") == item_id or meta.get("name") == item_id:
                item_idx = idx
                break
        
        if item_idx is None:
            return []
        
        try:
            # 해당 아이템의 벡터
            item_vector = self.vectors[category][item_idx:item_idx+1]
            
            # 모든 아이템과의 유사도 계산
            similarities = cosine_similarity(item_vector, self.vectors[category]).flatten()
            
            # 자기 자신 제외하고 상위 k개 선택
            similarities[item_idx] = -1  # 자기 자신 제외
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:
                    meta = self.metadata[category][idx]
                    results.append({
                        "score": float(similarities[idx]),
                        "type": meta["type"],
                        "data": meta["data"]
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Similar item search failed: {e}")
            return []
    
    def save_vectors(self, filepath: str):
        """벡터 데이터 저장"""
        data = {
            "vectors": self.vectors,
            "documents": self.documents,
            "metadata": self.metadata,
            "vectorizer": self.vectorizer
        }
        
        if hasattr(self, 'vectorizer_loan'):
            data["vectorizer_loan"] = self.vectorizer_loan
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Vectors saved to {filepath}")
    
    def load_vectors(self, filepath: str):
        """벡터 데이터 로드"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.vectors = data["vectors"]
        self.documents = data["documents"]
        self.metadata = data["metadata"]
        self.vectorizer = data["vectorizer"]
        
        if "vectorizer_loan" in data:
            self.vectorizer_loan = data["vectorizer_loan"]
        
        logger.info(f"Vectors loaded from {filepath}")


# 싱글톤 인스턴스
_vector_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    """벡터 검색 서비스 인스턴스 반환"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorSearchService()
    return _vector_service