"""
Finance Tools
자본 관리 에이전트가 사용하는 금융 관련 도구들
"""

from typing import Dict, Any, Optional, Tuple
from langchain_core.tools import tool
import logging
from datetime import datetime
import math

logger = logging.getLogger(__name__)


@tool
def calculate_loan_limit(
    monthly_income: int,
    existing_loans: int = 0,
    dti_limit: float = 40.0,
    ltv_limit: float = 70.0,
    property_price: Optional[int] = None
) -> Dict[str, Any]:
    """
    대출 한도 계산 (DTI, LTV, DSR 기준)
    
    Args:
        monthly_income: 월 소득 (원)
        existing_loans: 기존 대출 월 상환액 (원)
        dti_limit: DTI 한도 (%, 기본 40%)
        ltv_limit: LTV 한도 (%, 기본 70%)
        property_price: 부동산 가격 (원)
    
    Returns:
        대출 한도 정보
    """
    logger.info(f"Calculating loan limit for income: {monthly_income}")
    
    annual_income = monthly_income * 12
    
    # DTI (Debt to Income) 기준 한도
    # DTI = (연간 원리금 상환액 / 연간 소득) × 100
    max_annual_payment_dti = annual_income * (dti_limit / 100)
    max_monthly_payment_dti = max_annual_payment_dti / 12
    available_monthly_payment = max_monthly_payment_dti - existing_loans
    
    # 대출 가능 금액 계산 (원리금 균등 상환, 금리 4%, 30년 기준)
    interest_rate = 0.04 / 12  # 월 이자율
    loan_months = 30 * 12  # 30년
    
    if available_monthly_payment > 0:
        # 대출 원금 = 월상환액 × [(1+r)^n - 1] / [r × (1+r)^n]
        loan_amount_dti = available_monthly_payment * (
            ((1 + interest_rate) ** loan_months - 1) / 
            (interest_rate * (1 + interest_rate) ** loan_months)
        )
    else:
        loan_amount_dti = 0
    
    # LTV (Loan to Value) 기준 한도
    loan_amount_ltv = None
    if property_price:
        loan_amount_ltv = property_price * (ltv_limit / 100)
    
    # DSR (Debt Service Ratio) 계산
    dsr = ((existing_loans * 12) / annual_income) * 100 if annual_income > 0 else 0
    
    # 최종 대출 한도
    if loan_amount_ltv is not None:
        final_loan_limit = min(loan_amount_dti, loan_amount_ltv)
    else:
        final_loan_limit = loan_amount_dti
    
    return {
        "status": "success",
        "loan_limits": {
            "dti_based": int(loan_amount_dti),
            "ltv_based": int(loan_amount_ltv) if loan_amount_ltv else None,
            "final_limit": int(final_loan_limit)
        },
        "monthly_payment": {
            "maximum": int(max_monthly_payment_dti),
            "available": int(available_monthly_payment),
            "existing": existing_loans
        },
        "ratios": {
            "dti": round((max_annual_payment_dti / annual_income * 100), 1) if annual_income > 0 else 0,
            "dsr": round(dsr, 1),
            "ltv": ltv_limit if property_price else None
        },
        "assumptions": {
            "interest_rate": "4.0%",
            "loan_period": "30년",
            "repayment_type": "원리금균등"
        },
        "formatted": {
            "final_limit": f"{int(final_loan_limit) // 100000000}억 {(int(final_loan_limit) % 100000000) // 10000}만원" if final_loan_limit >= 100000000 else f"{int(final_loan_limit) // 10000}만원",
            "monthly_payment": f"{int(available_monthly_payment) // 10000}만원/월"
        }
    }


@tool
def simulate_monthly_payment(
    loan_amount: int,
    interest_rate: float = 4.0,
    loan_years: int = 30,
    repayment_type: str = "원리금균등"
) -> Dict[str, Any]:
    """
    월 상환액 시뮬레이션
    
    Args:
        loan_amount: 대출 금액 (원)
        interest_rate: 연 이자율 (%)
        loan_years: 대출 기간 (년)
        repayment_type: 상환 방식 (원리금균등, 원금균등)
    
    Returns:
        월 상환액 시뮬레이션 결과
    """
    logger.info(f"Simulating monthly payment for loan: {loan_amount}")
    
    monthly_rate = interest_rate / 100 / 12
    total_months = loan_years * 12
    
    if repayment_type == "원리금균등":
        # 원리금균등: 매달 같은 금액 상환
        if monthly_rate > 0:
            monthly_payment = loan_amount * (
                (monthly_rate * (1 + monthly_rate) ** total_months) /
                ((1 + monthly_rate) ** total_months - 1)
            )
        else:
            monthly_payment = loan_amount / total_months
        
        total_payment = monthly_payment * total_months
        total_interest = total_payment - loan_amount
        
        # 첫달과 마지막달 원금/이자
        first_month_interest = loan_amount * monthly_rate
        first_month_principal = monthly_payment - first_month_interest
        last_month_principal = monthly_payment * (1 - monthly_rate)
        last_month_interest = monthly_payment - last_month_principal
        
    else:  # 원금균등
        # 원금균등: 원금은 균등, 이자는 감소
        monthly_principal = loan_amount / total_months
        
        # 첫달과 마지막달 계산
        first_month_interest = loan_amount * monthly_rate
        first_month_payment = monthly_principal + first_month_interest
        
        last_month_interest = monthly_principal * monthly_rate
        last_month_payment = monthly_principal + last_month_interest
        
        # 평균 월 상환액
        total_interest = loan_amount * monthly_rate * (total_months + 1) / 2
        total_payment = loan_amount + total_interest
        monthly_payment = first_month_payment  # 첫달 기준
    
    return {
        "status": "success",
        "loan_info": {
            "amount": loan_amount,
            "interest_rate": interest_rate,
            "period_years": loan_years,
            "period_months": total_months,
            "type": repayment_type
        },
        "monthly_payment": {
            "amount": int(monthly_payment),
            "first_month": int(first_month_payment if repayment_type == "원금균등" else monthly_payment),
            "last_month": int(last_month_payment if repayment_type == "원금균등" else monthly_payment)
        },
        "total_payment": {
            "principal": loan_amount,
            "interest": int(total_interest),
            "total": int(total_payment)
        },
        "breakdown": {
            "first_month": {
                "principal": int(monthly_principal if repayment_type == "원금균등" else first_month_principal),
                "interest": int(first_month_interest),
                "total": int(first_month_payment if repayment_type == "원금균등" else monthly_payment)
            },
            "average_monthly": {
                "payment": int(total_payment / total_months)
            }
        },
        "formatted": {
            "monthly": f"{int(monthly_payment) // 10000}만원/월",
            "total_interest": f"{int(total_interest) // 100000000}억 {(int(total_interest) % 100000000) // 10000}만원" if total_interest >= 100000000 else f"{int(total_interest) // 10000}만원",
            "total_payment": f"{int(total_payment) // 100000000}억 {(int(total_payment) % 100000000) // 10000}만원" if total_payment >= 100000000 else f"{int(total_payment) // 10000}만원"
        }
    }


@tool
def find_properties_by_budget(
    max_budget: int,
    down_payment: int,
    monthly_income: int,
    location: Optional[str] = None,
    property_type: str = "아파트"
) -> Dict[str, Any]:
    """
    예산에 맞는 매물 찾기
    
    Args:
        max_budget: 최대 예산 (원)
        down_payment: 자기자본/계약금 (원)
        monthly_income: 월 소득 (원)
        location: 희망 지역
        property_type: 부동산 타입
    
    Returns:
        예산에 맞는 매물 추천
    """
    logger.info(f"Finding properties within budget: {max_budget}")
    
    # 대출 가능 금액 계산
    loan_needed = max_budget - down_payment
    
    # DTI 40% 기준 월 상환 가능액
    max_monthly_payment = monthly_income * 0.4
    
    # 30년, 4% 기준 대출 가능액 역산
    interest_rate = 0.04 / 12
    loan_months = 30 * 12
    
    max_loan = max_monthly_payment * (
        ((1 + interest_rate) ** loan_months - 1) / 
        (interest_rate * (1 + interest_rate) ** loan_months)
    )
    
    # 실제 구매 가능 금액
    affordable_price = down_payment + min(loan_needed, max_loan)
    
    # 추천 매물 생성 (실제로는 DB 조회)
    recommendations = []
    
    if affordable_price >= max_budget * 0.9:  # 예산의 90% 이상 가능
        status = "적정"
        message = "예산 범위 내에서 충분한 선택지가 있습니다."
        num_properties = 5
    elif affordable_price >= max_budget * 0.7:  # 70-90%
        status = "주의"
        message = "예산을 약간 조정하거나 대출 조건을 개선하면 더 많은 선택지가 있습니다."
        num_properties = 3
    else:
        status = "부족"
        message = "예산이나 자기자본을 늘리는 것을 고려해보세요."
        num_properties = 1
    
    import random
    for i in range(num_properties):
        price = int(affordable_price * random.uniform(0.8, 1.0))
        recommendations.append({
            "id": f"REC_{i+1:03d}",
            "name": f"{location if location else '추천'} {property_type} {i+1}",
            "price": price,
            "area": random.randint(25, 35),
            "loan_needed": max(0, price - down_payment),
            "monthly_payment": int((price - down_payment) * 0.004),  # 간단 계산
            "location": location if location else "추천지역",
            "match_score": random.uniform(70, 95)
        })
    
    return {
        "status": "success",
        "budget_analysis": {
            "max_budget": max_budget,
            "down_payment": down_payment,
            "loan_needed": loan_needed,
            "max_loan_available": int(max_loan),
            "affordable_price": int(affordable_price),
            "budget_status": status
        },
        "recommendations": sorted(recommendations, key=lambda x: x["match_score"], reverse=True),
        "financial_summary": {
            "down_payment_ratio": round((down_payment / max_budget * 100), 1),
            "loan_ratio": round(((max_budget - down_payment) / max_budget * 100), 1),
            "monthly_payment_to_income": round((max_monthly_payment / monthly_income * 100), 1)
        },
        "advice": message,
        "formatted": {
            "affordable": f"{int(affordable_price) // 100000000}억 {(int(affordable_price) % 100000000) // 10000}만원" if affordable_price >= 100000000 else f"{int(affordable_price) // 10000}만원",
            "max_loan": f"{int(max_loan) // 100000000}억 {(int(max_loan) % 100000000) // 10000}만원" if max_loan >= 100000000 else f"{int(max_loan) // 10000}만원"
        }
    }


@tool
def compare_interest_rates(
    loan_amount: int,
    bank_list: Optional[list] = None
) -> Dict[str, Any]:
    """
    은행별 금리 비교
    
    Args:
        loan_amount: 대출 금액 (원)
        bank_list: 비교할 은행 목록
    
    Returns:
        은행별 금리 비교 정보
    """
    logger.info(f"Comparing interest rates for loan: {loan_amount}")
    
    # 기본 은행 목록
    if not bank_list:
        bank_list = ["KB국민", "신한", "우리", "하나", "NH농협"]
    
    import random
    
    comparisons = []
    for bank in bank_list:
        # 실제로는 각 은행 API 호출
        base_rate = random.uniform(3.5, 5.0)
        
        # 금리 유형별
        fixed_rate = base_rate
        variable_rate = base_rate - random.uniform(0.3, 0.5)
        mixed_rate = base_rate - random.uniform(0.1, 0.3)
        
        # 월 상환액 계산 (30년 기준)
        monthly_fixed = loan_amount * (fixed_rate/100/12) / (1 - (1 + fixed_rate/100/12)**(-360))
        
        comparisons.append({
            "bank": bank,
            "rates": {
                "fixed": round(fixed_rate, 2),
                "variable": round(variable_rate, 2),
                "mixed": round(mixed_rate, 2)
            },
            "monthly_payment": {
                "fixed": int(monthly_fixed),
                "variable": int(monthly_fixed * (variable_rate / fixed_rate)),
                "mixed": int(monthly_fixed * (mixed_rate / fixed_rate))
            },
            "special_conditions": random.choice([
                "우대금리 0.2% 추가 적용 가능",
                "급여이체 시 0.1% 인하",
                "청약통장 보유 시 0.15% 인하",
                "첫 주택 구매 시 0.3% 인하"
            ]),
            "ltv_limit": random.choice([60, 70, 80]),
            "processing_fee": random.randint(0, 100) * 10000
        })
    
    # 최저 금리 찾기
    best_fixed = min(comparisons, key=lambda x: x["rates"]["fixed"])
    best_variable = min(comparisons, key=lambda x: x["rates"]["variable"])
    
    return {
        "status": "success",
        "loan_amount": loan_amount,
        "comparisons": sorted(comparisons, key=lambda x: x["rates"]["fixed"]),
        "best_options": {
            "fixed_rate": {
                "bank": best_fixed["bank"],
                "rate": best_fixed["rates"]["fixed"],
                "monthly": best_fixed["monthly_payment"]["fixed"]
            },
            "variable_rate": {
                "bank": best_variable["bank"],
                "rate": best_variable["rates"]["variable"],
                "monthly": best_variable["monthly_payment"]["variable"]
            }
        },
        "summary": {
            "rate_range": {
                "min": min(c["rates"]["fixed"] for c in comparisons),
                "max": max(c["rates"]["fixed"] for c in comparisons)
            },
            "monthly_difference": max(c["monthly_payment"]["fixed"] for c in comparisons) - 
                                min(c["monthly_payment"]["fixed"] for c in comparisons)
        },
        "recommendation": f"{best_fixed['bank']}의 고정금리 {best_fixed['rates']['fixed']}%가 가장 유리합니다."
    }


@tool
def calculate_taxes(
    property_price: int,
    transaction_type: str = "매매",
    is_first_home: bool = True,
    area_sqm: float = 85.0
) -> Dict[str, Any]:
    """
    세금 계산 (취득세, 재산세 등)
    
    Args:
        property_price: 부동산 가격 (원)
        transaction_type: 거래 유형 (매매, 상속, 증여)
        is_first_home: 생애 첫 주택 여부
        area_sqm: 면적 (㎡)
    
    Returns:
        세금 계산 결과
    """
    logger.info(f"Calculating taxes for property price: {property_price}")
    
    taxes = {}
    
    if transaction_type == "매매":
        # 취득세 계산
        if property_price <= 600000000:  # 6억 이하
            if is_first_home and area_sqm <= 60:
                acquisition_tax_rate = 0.01  # 1%
            else:
                acquisition_tax_rate = 0.01  # 1%
        elif property_price <= 900000000:  # 9억 이하
            acquisition_tax_rate = 0.02  # 2%
        else:  # 9억 초과
            acquisition_tax_rate = 0.03  # 3%
        
        acquisition_tax = property_price * acquisition_tax_rate
        
        # 지방교육세 (취득세의 10%)
        education_tax = acquisition_tax * 0.1
        
        # 농어촌특별세 (취득세 따라 다름)
        if acquisition_tax_rate >= 0.02:
            rural_tax = acquisition_tax * 0.2
        else:
            rural_tax = 0
        
        total_acquisition_cost = acquisition_tax + education_tax + rural_tax
        
        taxes["acquisition"] = {
            "acquisition_tax": int(acquisition_tax),
            "education_tax": int(education_tax),
            "rural_tax": int(rural_tax),
            "total": int(total_acquisition_cost),
            "rate": acquisition_tax_rate * 100
        }
    
    # 재산세 계산 (연간)
    if property_price <= 600000000:
        property_tax_rate = 0.001  # 0.1%
    elif property_price <= 1200000000:
        property_tax_rate = 0.0015  # 0.15%
    else:
        property_tax_rate = 0.002  # 0.2%
    
    annual_property_tax = property_price * property_tax_rate
    
    taxes["property"] = {
        "annual": int(annual_property_tax),
        "monthly": int(annual_property_tax / 12),
        "rate": property_tax_rate * 100
    }
    
    # 종합부동산세 (공시가격 기준, 간단 계산)
    if property_price > 1100000000:  # 11억 초과
        comprehensive_tax = (property_price - 1100000000) * 0.005
        taxes["comprehensive"] = {
            "annual": int(comprehensive_tax),
            "applicable": True
        }
    else:
        taxes["comprehensive"] = {
            "annual": 0,
            "applicable": False
        }
    
    # 총 세금
    total_taxes = taxes.get("acquisition", {}).get("total", 0) + taxes["property"]["annual"]
    
    return {
        "status": "success",
        "property_info": {
            "price": property_price,
            "transaction_type": transaction_type,
            "is_first_home": is_first_home,
            "area_sqm": area_sqm
        },
        "taxes": taxes,
        "total_first_year": total_taxes,
        "formatted": {
            "acquisition_total": f"{taxes.get('acquisition', {}).get('total', 0) // 10000}만원" if transaction_type == "매매" else "해당없음",
            "property_annual": f"{taxes['property']['annual'] // 10000}만원/년",
            "property_monthly": f"{taxes['property']['monthly'] // 10000}만원/월"
        },
        "tips": [
            "생애 첫 주택 구매 시 취득세 감면 혜택이 있습니다." if is_first_home else "추가 주택 구매 시 중과세가 적용될 수 있습니다.",
            "공시가격은 실거래가의 60-70% 수준으로 실제 세금은 더 낮을 수 있습니다.",
            "취득세는 취득일로부터 60일 이내 납부해야 합니다."
        ]
    }


@tool
def calculate_investment_return(
    property_price: int,
    monthly_rent: int,
    down_payment: int,
    appreciation_rate: float = 3.0,
    years: int = 5
) -> Dict[str, Any]:
    """
    투자 수익률 계산
    
    Args:
        property_price: 부동산 가격 (원)
        monthly_rent: 월 임대료 (원)
        down_payment: 투자금 (원)
        appreciation_rate: 연간 가격 상승률 (%)
        years: 투자 기간 (년)
    
    Returns:
        투자 수익률 분석
    """
    logger.info(f"Calculating investment return for property: {property_price}")
    
    # 연간 임대 수익
    annual_rent = monthly_rent * 12
    total_rent = annual_rent * years
    
    # 미래 부동산 가치
    future_value = property_price * ((1 + appreciation_rate / 100) ** years)
    appreciation = future_value - property_price
    
    # 총 수익
    total_return = total_rent + appreciation
    
    # 수익률 계산
    roi = (total_return / down_payment) * 100 if down_payment > 0 else 0
    annual_roi = roi / years
    
    # 임대 수익률
    rental_yield = (annual_rent / property_price) * 100
    
    # 대출이 있는 경우 레버리지 효과
    loan_amount = property_price - down_payment
    if loan_amount > 0:
        # 대출 이자 (연 4% 가정)
        annual_interest = loan_amount * 0.04
        net_rental_income = annual_rent - annual_interest
        net_annual_return = net_rental_income + (appreciation / years)
        leveraged_roi = (net_annual_return / down_payment) * 100 if down_payment > 0 else 0
    else:
        leveraged_roi = annual_roi
        net_rental_income = annual_rent
    
    return {
        "status": "success",
        "investment_summary": {
            "property_price": property_price,
            "down_payment": down_payment,
            "loan_amount": loan_amount,
            "investment_period": years
        },
        "returns": {
            "rental_income": {
                "monthly": monthly_rent,
                "annual": annual_rent,
                "total": total_rent
            },
            "appreciation": {
                "rate": appreciation_rate,
                "amount": int(appreciation),
                "future_value": int(future_value)
            },
            "total_return": int(total_return)
        },
        "roi_analysis": {
            "simple_roi": round(roi, 2),
            "annual_roi": round(annual_roi, 2),
            "rental_yield": round(rental_yield, 2),
            "leveraged_roi": round(leveraged_roi, 2) if loan_amount > 0 else None
        },
        "cash_flow": {
            "monthly_rent": monthly_rent,
            "monthly_loan_payment": int(loan_amount * 0.004) if loan_amount > 0 else 0,
            "net_monthly": monthly_rent - int(loan_amount * 0.004) if loan_amount > 0 else monthly_rent,
            "net_annual": int(net_rental_income)
        },
        "formatted": {
            "total_return": f"{int(total_return) // 100000000}억 {(int(total_return) % 100000000) // 10000}만원" if total_return >= 100000000 else f"{int(total_return) // 10000}만원",
            "roi": f"{round(roi, 1)}%",
            "annual_roi": f"{round(annual_roi, 1)}%"
        },
        "investment_grade": "A" if annual_roi > 10 else "B" if annual_roi > 5 else "C"
    }


# 도구 목록
FINANCE_TOOLS = [
    calculate_loan_limit,
    simulate_monthly_payment,
    find_properties_by_budget,
    compare_interest_rates,
    calculate_taxes,
    calculate_investment_return
]