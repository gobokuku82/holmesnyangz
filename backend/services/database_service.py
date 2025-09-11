"""
Database Service Layer
Mock 데이터베이스 접근 및 관리 서비스
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MockDatabaseService:
    """Mock 데이터베이스 서비스"""
    
    def __init__(self, mock_data_path: str = "database/mockup"):
        """
        Args:
            mock_data_path: Mock 데이터 디렉토리 경로
        """
        self.data_path = Path(mock_data_path)
        self.data_cache: Dict[str, Any] = {}
        self._load_all_data()
    
    def _load_all_data(self):
        """모든 Mock 데이터 로드 및 캐싱"""
        data_files = {
            "laws": "real_estate_laws.json",
            "dictionary": "real_estate_dictionary.json",
            "faq": "faq_cases.json",
            "subscription_policy": "subscription_policy.json",
            "area_info": "area_living_info.json",
            "transit": "transit_accessibility.json",
            "transactions": "transaction_history.json",
            "subscription_stats": "subscription_statistics.json",
            "loans": "loan_info.json",
            "benefits": "benefits.json"
        }
        
        for key, filename in data_files.items():
            file_path = self.data_path / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.data_cache[key] = json.load(f)
                        logger.info(f"Loaded {key} data from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load {filename}: {e}")
                    self.data_cache[key] = {}
            else:
                logger.warning(f"File not found: {file_path}")
                self.data_cache[key] = {}
    
    # === 법령 및 판례 ===
    def get_laws(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        법령 정보 조회
        
        Args:
            category: 법령 카테고리 (임대차, 거래신고, 중개 등)
        """
        laws = self.data_cache.get("laws", {}).get("laws", [])
        
        if category:
            laws = [law for law in laws if law.get("category") == category]
        
        return laws
    
    def get_recent_cases(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 판례 조회"""
        cases = self.data_cache.get("laws", {}).get("recent_cases", [])
        return cases[:limit]
    
    def get_tax_laws(self, tax_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """세금 관련 법률 조회"""
        tax_laws = self.data_cache.get("laws", {}).get("tax_laws", [])
        
        if tax_type:
            tax_laws = [tax for tax in tax_laws if tax.get("name") == tax_type]
        
        return tax_laws
    
    # === 용어 사전 ===
    def search_terms(self, keyword: str) -> List[Dict[str, Any]]:
        """
        용어 검색
        
        Args:
            keyword: 검색 키워드
        """
        terms = self.data_cache.get("dictionary", {}).get("terms", [])
        
        # 키워드가 포함된 용어 검색
        results = []
        keyword_lower = keyword.lower()
        
        for term in terms:
            if (keyword_lower in term.get("term", "").lower() or
                keyword_lower in term.get("definition", "").lower() or
                keyword_lower in term.get("category", "").lower()):
                results.append(term)
        
        return results
    
    def get_term_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 용어 조회"""
        terms = self.data_cache.get("dictionary", {}).get("terms", [])
        return [term for term in terms if term.get("category") == category]
    
    # === FAQ 및 상담 사례 ===
    def get_faq(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """FAQ 조회"""
        faqs = self.data_cache.get("faq", {}).get("faq", [])
        
        if category:
            faqs = [faq for faq in faqs if faq.get("category") == category]
        
        # 조회수 기준 정렬
        faqs.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        
        return faqs[:limit]
    
    def get_consultation_cases(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """상담 사례 조회"""
        cases = self.data_cache.get("faq", {}).get("consultation_cases", [])
        
        if category:
            cases = [case for case in cases if case.get("category") == category]
        
        return cases
    
    # === 청약 정책 ===
    def get_subscription_policies(self) -> Dict[str, Any]:
        """청약 정책 전체 조회"""
        return self.data_cache.get("subscription_policy", {})
    
    def get_special_supply_info(self, supply_type: str) -> Optional[Dict[str, Any]]:
        """
        특별공급 정보 조회
        
        Args:
            supply_type: 특별공급 유형 (신혼부부, 생애최초, 다자녀 등)
        """
        policies = self.data_cache.get("subscription_policy", {}).get("policies", [])
        
        for policy in policies:
            if policy.get("name") == "특별공급":
                types = policy.get("types", [])
                for t in types:
                    if t.get("name") == supply_type:
                        return t
        
        return None
    
    # === 지역 정보 ===
    def get_area_info(self, area_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 지역 정보 조회
        
        Args:
            area_name: 지역명 (예: 강남구, 마포구)
        """
        areas = self.data_cache.get("area_info", {}).get("areas", [])
        
        for area in areas:
            if area.get("name") == area_name:
                return area
        
        return None
    
    def get_area_schools(self, area_name: str) -> Dict[str, Any]:
        """지역별 학교 정보 조회"""
        area = self.get_area_info(area_name)
        if area:
            return area.get("schools", {})
        return {}
    
    def get_area_transportation(self, area_name: str) -> Dict[str, Any]:
        """지역별 교통 정보 조회"""
        area = self.get_area_info(area_name)
        if area:
            return area.get("transportation", {})
        return {}
    
    # === 교통 접근성 ===
    def get_transit_zone(self, station_name: str) -> Optional[Dict[str, Any]]:
        """
        역세권 정보 조회
        
        Args:
            station_name: 역 이름
        """
        zones = self.data_cache.get("transit", {}).get("transit_zones", [])
        
        for zone in zones:
            if station_name in zone.get("station", {}).get("name", ""):
                return zone
        
        return None
    
    def get_future_transit_plans(self) -> List[Dict[str, Any]]:
        """미래 교통 계획 조회"""
        return self.data_cache.get("transit", {}).get("future_plans", [])
    
    # === 실거래가 ===
    def get_recent_transactions(
        self, 
        location: Optional[str] = None,
        property_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        최근 거래 내역 조회
        
        Args:
            location: 지역명
            property_type: 부동산 유형
            transaction_type: 거래 유형 (매매, 전세, 월세)
            limit: 조회 개수
        """
        transactions = self.data_cache.get("transactions", {}).get("transactions", [])
        
        # 필터링
        filtered = []
        for trans in transactions:
            if location and location not in str(trans.get("location", {})):
                continue
            if property_type and trans.get("property", {}).get("type") != property_type:
                continue
            if transaction_type and trans.get("type") != transaction_type:
                continue
            filtered.append(trans)
        
        # 날짜순 정렬
        filtered.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return filtered[:limit]
    
    def get_market_trends(self, region: str = "seoul") -> Dict[str, Any]:
        """시장 동향 조회"""
        return self.data_cache.get("transactions", {}).get("market_trends", {}).get(region, {})
    
    def get_price_indices(self) -> Dict[str, Any]:
        """가격 지수 조회"""
        return self.data_cache.get("transactions", {}).get("price_indices", {})
    
    # === 대출 정보 ===
    def get_loan_products(
        self,
        bank: Optional[str] = None,
        loan_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        대출 상품 조회
        
        Args:
            bank: 은행명
            loan_type: 대출 유형
        """
        products = self.data_cache.get("loans", {}).get("loan_products", [])
        
        # 필터링
        if bank:
            products = [p for p in products if p.get("bank") == bank]
        if loan_type:
            products = [p for p in products if p.get("type") == loan_type]
        
        return products
    
    def get_government_loans(self) -> List[Dict[str, Any]]:
        """정부 지원 대출 조회"""
        return self.data_cache.get("loans", {}).get("government_loans", [])
    
    def get_interest_rates(self) -> Dict[str, Any]:
        """현재 금리 정보 조회"""
        return self.data_cache.get("loans", {}).get("interest_rate_trends", {})
    
    # === 혜택 정보 ===
    def get_benefits(
        self,
        category: Optional[str] = None,
        target: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        주거 지원 혜택 조회
        
        Args:
            category: 혜택 카테고리
            target: 대상 (청년, 신혼부부 등)
        """
        benefits = self.data_cache.get("benefits", {}).get("housing_benefits", [])
        
        # 필터링
        if category:
            benefits = [b for b in benefits if b.get("category") == category]
        if target:
            benefits = [b for b in benefits if target in b.get("target", "")]
        
        return benefits
    
    def get_regional_benefits(self, region: str) -> List[Dict[str, Any]]:
        """지역별 혜택 조회"""
        regional = self.data_cache.get("benefits", {}).get("regional_benefits", [])
        
        for r in regional:
            if r.get("region") == region:
                return r.get("programs", [])
        
        return []
    
    # === 청약 통계 (벡터 검색 대상) ===
    def get_subscription_statistics(
        self,
        location: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        청약 통계 조회
        
        Args:
            location: 지역
            date_from: 시작일
            date_to: 종료일
        """
        stats = self.data_cache.get("subscription_stats", {}).get("subscription_results", [])
        
        # 필터링
        filtered = []
        for stat in stats:
            if location and location not in str(stat.get("location", {})):
                continue
            
            # 날짜 필터링 (간단한 문자열 비교)
            stat_date = stat.get("date", "")
            if date_from and stat_date < date_from:
                continue
            if date_to and stat_date > date_to:
                continue
            
            filtered.append(stat)
        
        return filtered
    
    def get_winning_patterns(self) -> List[Dict[str, Any]]:
        """당첨 패턴 분석 조회"""
        return self.data_cache.get("subscription_stats", {}).get("winning_patterns", [])
    
    # === 통합 검색 ===
    def search_all(self, query: str, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        모든 데이터에서 통합 검색
        
        Args:
            query: 검색어
            limit: 카테고리별 최대 결과 수
        """
        results = {
            "laws": [],
            "terms": [],
            "faq": [],
            "areas": [],
            "transactions": [],
            "loans": [],
            "benefits": []
        }
        
        query_lower = query.lower()
        
        # 법령 검색
        laws = self.get_laws()
        for law in laws[:limit]:
            if query_lower in json.dumps(law, ensure_ascii=False).lower():
                results["laws"].append(law)
        
        # 용어 검색
        results["terms"] = self.search_terms(query)[:limit]
        
        # FAQ 검색
        faqs = self.get_faq(limit=100)
        for faq in faqs:
            if query_lower in json.dumps(faq, ensure_ascii=False).lower():
                results["faq"].append(faq)
                if len(results["faq"]) >= limit:
                    break
        
        # 지역 검색
        areas = self.data_cache.get("area_info", {}).get("areas", [])
        for area in areas:
            if query_lower in json.dumps(area, ensure_ascii=False).lower():
                results["areas"].append(area)
                if len(results["areas"]) >= limit:
                    break
        
        # 거래 검색
        results["transactions"] = self.get_recent_transactions(location=query, limit=limit)
        
        # 대출 검색
        loans = self.get_loan_products()
        for loan in loans[:limit]:
            if query_lower in json.dumps(loan, ensure_ascii=False).lower():
                results["loans"].append(loan)
        
        # 혜택 검색
        benefits = self.get_benefits()
        for benefit in benefits[:limit]:
            if query_lower in json.dumps(benefit, ensure_ascii=False).lower():
                results["benefits"].append(benefit)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보"""
        return {
            "total_laws": len(self.data_cache.get("laws", {}).get("laws", [])),
            "total_terms": len(self.data_cache.get("dictionary", {}).get("terms", [])),
            "total_faq": len(self.data_cache.get("faq", {}).get("faq", [])),
            "total_areas": len(self.data_cache.get("area_info", {}).get("areas", [])),
            "total_transactions": len(self.data_cache.get("transactions", {}).get("transactions", [])),
            "total_loans": len(self.data_cache.get("loans", {}).get("loan_products", [])),
            "total_benefits": len(self.data_cache.get("benefits", {}).get("housing_benefits", [])),
            "last_updated": datetime.now().isoformat()
        }


# 싱글톤 인스턴스
_db_service: Optional[MockDatabaseService] = None


def get_database_service() -> MockDatabaseService:
    """데이터베이스 서비스 인스턴스 반환"""
    global _db_service
    if _db_service is None:
        _db_service = MockDatabaseService()
    return _db_service