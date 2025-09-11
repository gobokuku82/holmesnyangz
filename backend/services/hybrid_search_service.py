"""
Hybrid Search Service
하이브리드 검색 서비스 (키워드 + 벡터 + 의미 검색)
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
from backend.services.database_service import get_database_service
from backend.services.vector_search_service import get_vector_search_service

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    하이브리드 검색 서비스
    키워드 검색, 벡터 검색, 의미 기반 검색을 결합
    """
    
    def __init__(self):
        """서비스 초기화"""
        self.db_service = get_database_service()
        self.vector_service = get_vector_search_service()
        self.search_history = []
    
    def search(
        self,
        query: str,
        search_type: str = "all",
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        통합 하이브리드 검색
        
        Args:
            query: 검색 쿼리
            search_type: 검색 유형 (all, real_estate, loan, policy, area)
            filters: 필터 조건
            top_k: 상위 결과 개수
            weights: 검색 방법별 가중치
        
        Returns:
            검색 결과
        """
        # 기본 가중치
        if weights is None:
            weights = {
                "keyword": 0.3,
                "vector": 0.5,
                "semantic": 0.2
            }
        
        # 검색 시작 시간
        start_time = datetime.now()
        
        # 검색 수행
        results = {
            "query": query,
            "search_type": search_type,
            "results": [],
            "facets": {},
            "suggestions": [],
            "metadata": {}
        }
        
        try:
            if search_type == "all":
                results["results"] = self._search_all(query, filters, top_k, weights)
            elif search_type == "real_estate":
                results["results"] = self._search_real_estate(query, filters, top_k, weights)
            elif search_type == "loan":
                results["results"] = self._search_loan(query, filters, top_k, weights)
            elif search_type == "policy":
                results["results"] = self._search_policy(query, filters, top_k, weights)
            elif search_type == "area":
                results["results"] = self._search_area(query, filters, top_k, weights)
            else:
                results["results"] = self._search_all(query, filters, top_k, weights)
            
            # 패싯 생성
            results["facets"] = self._generate_facets(results["results"])
            
            # 추천 검색어 생성
            results["suggestions"] = self._generate_suggestions(query, results["results"])
            
            # 메타데이터
            results["metadata"] = {
                "total_results": len(results["results"]),
                "search_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
            
            # 검색 기록 저장
            self._save_search_history(query, search_type, results["metadata"]["total_results"])
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def _search_all(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """전체 검색"""
        all_results = []
        
        # 키워드 검색
        keyword_results = self.db_service.search_all(query, limit=top_k)
        
        # 각 카테고리별 결과 통합
        for category, items in keyword_results.items():
            for item in items:
                all_results.append({
                    "type": category,
                    "score": weights["keyword"],
                    "data": item,
                    "source": "keyword"
                })
        
        # 벡터 검색 (청약 통계)
        vector_results = self.vector_service.search_subscription(query, top_k=top_k)
        for result in vector_results:
            all_results.append({
                "type": "subscription",
                "score": result["score"] * weights["vector"],
                "data": result["data"],
                "source": "vector"
            })
        
        # 벡터 검색 (대출 정보)
        loan_vector_results = self.vector_service.search_loan(query, top_k=top_k)
        for result in loan_vector_results:
            all_results.append({
                "type": "loan",
                "score": result["score"] * weights["vector"],
                "data": result["data"],
                "source": "vector"
            })
        
        # 점수 기준 정렬 및 중복 제거
        all_results = self._deduplicate_results(all_results)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        return all_results[:top_k]
    
    def _search_real_estate(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """부동산 관련 검색"""
        results = []
        
        # 거래 내역 검색
        location = filters.get("location") if filters else None
        property_type = filters.get("property_type") if filters else None
        transaction_type = filters.get("transaction_type") if filters else None
        
        transactions = self.db_service.get_recent_transactions(
            location=location or query,
            property_type=property_type,
            transaction_type=transaction_type,
            limit=top_k
        )
        
        for trans in transactions:
            results.append({
                "type": "transaction",
                "score": weights["keyword"],
                "data": trans,
                "source": "database"
            })
        
        # 지역 정보 검색
        area_info = self.db_service.get_area_info(query)
        if area_info:
            results.append({
                "type": "area",
                "score": weights["keyword"] * 1.2,  # 정확한 매칭에 가중치
                "data": area_info,
                "source": "database"
            })
        
        # 교통 정보 검색
        transit_info = self.db_service.get_transit_zone(query)
        if transit_info:
            results.append({
                "type": "transit",
                "score": weights["keyword"],
                "data": transit_info,
                "source": "database"
            })
        
        # 시장 동향 추가
        market_trends = self.db_service.get_market_trends()
        if market_trends:
            results.append({
                "type": "market_trend",
                "score": weights["keyword"] * 0.5,
                "data": market_trends,
                "source": "database"
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _search_loan(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """대출 관련 검색"""
        results = []
        
        # 벡터 검색
        vector_results = self.vector_service.hybrid_search(
            query,
            category="loan",
            keyword_weight=weights["keyword"],
            vector_weight=weights["vector"],
            top_k=top_k
        )
        
        for result in vector_results:
            results.append({
                "type": "loan",
                "score": result["score"],
                "data": result["data"],
                "source": "hybrid"
            })
        
        # 정부 대출 검색
        gov_loans = self.db_service.get_government_loans()
        query_lower = query.lower()
        for loan in gov_loans:
            loan_str = str(loan).lower()
            if query_lower in loan_str:
                results.append({
                    "type": "government_loan",
                    "score": weights["keyword"],
                    "data": loan,
                    "source": "database"
                })
        
        # 금리 정보 추가
        if "금리" in query or "이자" in query:
            interest_rates = self.db_service.get_interest_rates()
            results.append({
                "type": "interest_rate",
                "score": weights["keyword"] * 0.8,
                "data": interest_rates,
                "source": "database"
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _search_policy(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """정책 관련 검색"""
        results = []
        
        # 청약 정책 검색
        if "청약" in query or "분양" in query:
            policies = self.db_service.get_subscription_policies()
            results.append({
                "type": "subscription_policy",
                "score": weights["keyword"],
                "data": policies,
                "source": "database"
            })
            
            # 벡터 검색으로 청약 통계 추가
            vector_results = self.vector_service.search_subscription(query, top_k=5)
            for result in vector_results:
                results.append({
                    "type": "subscription_stat",
                    "score": result["score"] * weights["vector"],
                    "data": result["data"],
                    "source": "vector"
                })
        
        # 혜택 검색
        benefits = self.db_service.get_benefits()
        query_lower = query.lower()
        for benefit in benefits:
            benefit_str = str(benefit).lower()
            if query_lower in benefit_str:
                score = weights["keyword"]
                # 특정 키워드에 가중치
                if benefit.get("target") and benefit["target"].lower() in query_lower:
                    score *= 1.5
                
                results.append({
                    "type": "benefit",
                    "score": score,
                    "data": benefit,
                    "source": "database"
                })
        
        # 법령 검색
        laws = self.db_service.get_laws()
        for law in laws[:5]:  # 상위 5개만
            law_str = str(law).lower()
            if query_lower in law_str:
                results.append({
                    "type": "law",
                    "score": weights["keyword"] * 0.7,
                    "data": law,
                    "source": "database"
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _search_area(
        self,
        query: str,
        filters: Optional[Dict[str, Any]],
        top_k: int,
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """지역 관련 검색"""
        results = []
        
        # 지역 정보 검색
        area_info = self.db_service.get_area_info(query)
        if area_info:
            results.append({
                "type": "area_info",
                "score": weights["keyword"] * 1.5,
                "data": area_info,
                "source": "database"
            })
            
            # 학군 정보
            schools = area_info.get("schools", {})
            if schools:
                results.append({
                    "type": "schools",
                    "score": weights["keyword"],
                    "data": schools,
                    "source": "database"
                })
            
            # 교통 정보
            transportation = area_info.get("transportation", {})
            if transportation:
                results.append({
                    "type": "transportation",
                    "score": weights["keyword"],
                    "data": transportation,
                    "source": "database"
                })
        
        # 역세권 정보 검색
        transit_zone = self.db_service.get_transit_zone(query)
        if transit_zone:
            results.append({
                "type": "transit_zone",
                "score": weights["keyword"],
                "data": transit_zone,
                "source": "database"
            })
        
        # 해당 지역 거래 내역
        transactions = self.db_service.get_recent_transactions(
            location=query,
            limit=5
        )
        for trans in transactions:
            results.append({
                "type": "transaction",
                "score": weights["keyword"] * 0.8,
                "data": trans,
                "source": "database"
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 결과 제거"""
        seen = set()
        unique_results = []
        
        for result in results:
            # 고유 키 생성
            data = result.get("data", {})
            if isinstance(data, dict):
                key = f"{result['type']}_{data.get('id', '')}_{data.get('name', '')}"
            else:
                key = f"{result['type']}_{str(data)[:50]}"
            
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def _generate_facets(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """패싯 생성"""
        facets = {
            "types": {},
            "sources": {},
            "categories": {}
        }
        
        for result in results:
            # 타입별 집계
            result_type = result.get("type", "unknown")
            facets["types"][result_type] = facets["types"].get(result_type, 0) + 1
            
            # 소스별 집계
            source = result.get("source", "unknown")
            facets["sources"][source] = facets["sources"].get(source, 0) + 1
            
            # 카테고리별 집계
            data = result.get("data", {})
            if isinstance(data, dict):
                category = data.get("category") or data.get("type") or result_type
                facets["categories"][category] = facets["categories"].get(category, 0) + 1
        
        return facets
    
    def _generate_suggestions(self, query: str, results: List[Dict[str, Any]]) -> List[str]:
        """추천 검색어 생성"""
        suggestions = []
        
        # 결과 기반 추천
        if results:
            # 가장 많이 나온 지역명 추출
            locations = []
            for result in results[:5]:
                data = result.get("data", {})
                if isinstance(data, dict):
                    if "location" in data:
                        loc = data["location"]
                        if isinstance(loc, dict):
                            locations.append(loc.get("district", ""))
                        elif isinstance(loc, str):
                            locations.append(loc)
            
            # 고유한 지역명 추천
            unique_locations = list(set(loc for loc in locations if loc))
            for loc in unique_locations[:3]:
                if loc not in query:
                    suggestions.append(f"{query} {loc}")
        
        # 연관 검색어 추천
        related_terms = {
            "아파트": ["매매", "전세", "시세"],
            "대출": ["금리", "한도", "DTI", "LTV"],
            "청약": ["가점", "경쟁률", "당첨"],
            "신혼부부": ["특별공급", "디딤돌대출", "생애최초"],
            "투자": ["갭투자", "재건축", "수익률"]
        }
        
        for key, values in related_terms.items():
            if key in query:
                for value in values:
                    if value not in query:
                        suggestions.append(f"{query} {value}")
                        if len(suggestions) >= 5:
                            break
        
        return suggestions[:5]
    
    def _save_search_history(self, query: str, search_type: str, result_count: int):
        """검색 기록 저장"""
        self.search_history.append({
            "query": query,
            "search_type": search_type,
            "result_count": result_count,
            "timestamp": datetime.now().isoformat()
        })
        
        # 최근 100개만 유지
        if len(self.search_history) > 100:
            self.search_history = self.search_history[-100:]
    
    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """검색 기록 조회"""
        return self.search_history[-limit:][::-1]
    
    def get_popular_searches(self, limit: int = 10) -> List[Tuple[str, int]]:
        """인기 검색어 조회"""
        from collections import Counter
        
        queries = [h["query"] for h in self.search_history]
        counter = Counter(queries)
        
        return counter.most_common(limit)


# 싱글톤 인스턴스
_hybrid_service: Optional[HybridSearchService] = None


def get_hybrid_search_service() -> HybridSearchService:
    """하이브리드 검색 서비스 인스턴스 반환"""
    global _hybrid_service
    if _hybrid_service is None:
        _hybrid_service = HybridSearchService()
    return _hybrid_service