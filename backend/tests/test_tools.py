"""
Tools Tests for Real Estate Chatbot
도구 함수 테스트
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from backend.tools.price_tools import (
    search_real_estate_price,
    analyze_price_trend,
    compare_prices,
    get_market_statistics
)
from backend.tools.finance_tools import (
    calculate_loan_limit,
    simulate_monthly_payment,
    calculate_total_interest,
    analyze_affordability
)
from backend.tools.location_tools import (
    search_nearby_facilities,
    analyze_school_district,
    evaluate_accessibility,
    get_transportation_info
)
from backend.tools.legal_tools import (
    explain_contract_terms,
    check_regulations,
    calculate_acquisition_tax,
    verify_ownership
)


class TestPriceTools:
    """가격 관련 도구 테스트"""
    
    def test_search_real_estate_price(self):
        """부동산 가격 검색 테스트"""
        result = search_real_estate_price(
            location="강남구",
            property_type="아파트",
            size_sqm=84
        )
        
        assert "location" in result
        assert "property_type" in result
        assert "prices" in result
        assert result["location"] == "강남구"
    
    def test_analyze_price_trend(self):
        """가격 추세 분석 테스트"""
        result = analyze_price_trend(
            location="강남구",
            property_type="아파트",
            period_months=12
        )
        
        assert "location" in result
        assert "trend" in result
        assert "change_rate" in result
        assert result["period_months"] == 12
    
    def test_compare_prices(self):
        """가격 비교 테스트"""
        result = compare_prices(
            locations=["강남구", "서초구"],
            property_type="아파트"
        )
        
        assert "comparison" in result
        assert len(result["comparison"]) == 2
        assert "강남구" in result["comparison"]
        assert "서초구" in result["comparison"]
    
    def test_get_market_statistics(self):
        """시장 통계 조회 테스트"""
        result = get_market_statistics(
            location="강남구",
            property_type="아파트"
        )
        
        assert "average_price" in result
        assert "median_price" in result
        assert "transaction_volume" in result
        assert "supply_demand_ratio" in result


class TestFinanceTools:
    """금융 관련 도구 테스트"""
    
    def test_calculate_loan_limit(self):
        """대출 한도 계산 테스트"""
        result = calculate_loan_limit(
            annual_income=100000000,  # 1억
            existing_loans=0,
            credit_score=800
        )
        
        assert "max_loan_amount" in result
        assert "dti_limit" in result
        assert "ltv_limit" in result
        assert result["max_loan_amount"] > 0
    
    def test_simulate_monthly_payment(self):
        """월 상환액 시뮬레이션 테스트"""
        result = simulate_monthly_payment(
            loan_amount=500000000,  # 5억
            interest_rate=3.5,
            loan_years=30
        )
        
        assert "monthly_payment" in result
        assert "total_payment" in result
        assert "total_interest" in result
        assert result["monthly_payment"] > 0
        assert result["total_payment"] > result["loan_amount"]
    
    def test_calculate_total_interest(self):
        """총 이자 계산 테스트"""
        result = calculate_total_interest(
            loan_amount=300000000,  # 3억
            interest_rate=3.0,
            loan_years=20
        )
        
        assert "total_interest" in result
        assert "interest_ratio" in result
        assert result["total_interest"] > 0
    
    def test_analyze_affordability(self):
        """구매 가능성 분석 테스트"""
        result = analyze_affordability(
            property_price=1000000000,  # 10억
            available_cash=400000000,   # 4억
            annual_income=120000000,    # 1.2억
            monthly_expenses=3000000    # 300만
        )
        
        assert "affordable" in result
        assert "required_loan" in result
        assert "recommended_price_range" in result
        assert isinstance(result["affordable"], bool)


class TestLocationTools:
    """입지 관련 도구 테스트"""
    
    def test_search_nearby_facilities(self):
        """주변 시설 검색 테스트"""
        result = search_nearby_facilities(
            address="서울시 강남구 삼성동",
            radius_km=1.0
        )
        
        assert "schools" in result
        assert "hospitals" in result
        assert "marts" in result
        assert "parks" in result
        assert "subway_stations" in result
        assert isinstance(result["schools"], list)
    
    def test_analyze_school_district(self):
        """학군 분석 테스트"""
        result = analyze_school_district(
            address="서울시 강남구 대치동"
        )
        
        assert "elementary_schools" in result
        assert "middle_schools" in result
        assert "high_schools" in result
        assert "district_rating" in result
        assert result["district_rating"] in ["상", "중", "하"]
    
    def test_evaluate_accessibility(self):
        """접근성 평가 테스트"""
        result = evaluate_accessibility(
            address="서울시 강남구 역삼동"
        )
        
        assert "public_transport_score" in result
        assert "road_access_score" in result
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 10
    
    def test_get_transportation_info(self):
        """교통 정보 조회 테스트"""
        result = get_transportation_info(
            address="서울시 서초구 반포동"
        )
        
        assert "nearest_subway" in result
        assert "bus_routes" in result
        assert "major_roads" in result
        assert "commute_times" in result


class TestLegalTools:
    """법률 관련 도구 테스트"""
    
    def test_explain_contract_terms(self):
        """계약 조건 설명 테스트"""
        result = explain_contract_terms(
            contract_type="매매"
        )
        
        assert "key_terms" in result
        assert "required_documents" in result
        assert "important_clauses" in result
        assert "cautions" in result
        assert len(result["key_terms"]) > 0
    
    def test_check_regulations(self):
        """규제 확인 테스트"""
        result = check_regulations(
            location="서울시 강남구",
            property_type="아파트"
        )
        
        assert "regulations" in result
        assert "청약" in result["regulations"]
        assert "전매제한" in result["regulations"]
        assert "재건축" in result["regulations"]
    
    def test_calculate_acquisition_tax(self):
        """취득세 계산 테스트"""
        result = calculate_acquisition_tax(
            property_price=900000000,  # 9억
            is_first_time=True,
            property_count=0
        )
        
        assert "acquisition_tax" in result
        assert "education_tax" in result
        assert "total_tax" in result
        assert result["total_tax"] > 0
        
        # 첫 주택 구매자 혜택 확인
        assert "tax_benefits" in result
        if result["is_first_time"]:
            assert result["tax_benefits"]["first_time_buyer"] == True
    
    def test_verify_ownership(self):
        """소유권 확인 테스트"""
        result = verify_ownership(
            property_id="강남구-아파트-12345"
        )
        
        assert "ownership_status" in result
        assert "liens" in result
        assert "mortgages" in result
        assert "warnings" in result
        assert result["ownership_status"] in ["정상", "주의", "위험"]


class TestToolIntegration:
    """도구 통합 테스트"""
    
    def test_price_and_finance_integration(self):
        """가격과 금융 도구 통합 테스트"""
        # 1. 가격 조회
        price_result = search_real_estate_price(
            location="강남구",
            property_type="아파트",
            size_sqm=84
        )
        
        # 2. 대출 계산
        if price_result["prices"]:
            avg_price = price_result["prices"][0]["price"]
            loan_result = calculate_loan_limit(
                annual_income=100000000,
                existing_loans=0,
                credit_score=750
            )
            
            # 3. 월 상환액 계산
            if loan_result["max_loan_amount"] > 0:
                payment_result = simulate_monthly_payment(
                    loan_amount=min(loan_result["max_loan_amount"], avg_price * 0.7),
                    interest_rate=3.5,
                    loan_years=30
                )
                
                assert payment_result["monthly_payment"] > 0
    
    def test_location_and_legal_integration(self):
        """입지와 법률 도구 통합 테스트"""
        # 1. 입지 분석
        location_result = search_nearby_facilities(
            address="서울시 강남구 삼성동",
            radius_km=1.0
        )
        
        # 2. 규제 확인
        if location_result:
            regulation_result = check_regulations(
                location="강남구",
                property_type="아파트"
            )
            
            assert "regulations" in regulation_result
            
            # 3. 취득세 계산
            tax_result = calculate_acquisition_tax(
                property_price=1000000000,
                is_first_time=True,
                property_count=0
            )
            
            assert tax_result["total_tax"] > 0


class TestToolErrorHandling:
    """도구 에러 처리 테스트"""
    
    def test_invalid_location(self):
        """잘못된 위치 처리"""
        result = search_real_estate_price(
            location="",  # 빈 위치
            property_type="아파트"
        )
        
        # 에러가 아닌 빈 결과 또는 기본값 반환 확인
        assert result is not None
        assert "error" in result or "prices" in result
    
    def test_negative_loan_amount(self):
        """음수 대출금액 처리"""
        result = simulate_monthly_payment(
            loan_amount=-100000000,  # 음수
            interest_rate=3.5,
            loan_years=30
        )
        
        # 에러 처리 확인
        assert "error" in result or result["monthly_payment"] == 0
    
    def test_invalid_tax_calculation(self):
        """잘못된 세금 계산 처리"""
        result = calculate_acquisition_tax(
            property_price=0,  # 0원
            is_first_time=True,
            property_count=-1  # 음수
        )
        
        # 최소값 또는 에러 처리 확인
        assert result["total_tax"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])