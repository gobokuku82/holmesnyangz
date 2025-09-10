"""
Legal Tools
법률 및 규정 관련 에이전트가 사용하는 도구들
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


@tool
def explain_contract_terms(
    contract_type: str = "매매",
    is_first_time: bool = True
) -> Dict[str, Any]:
    """
    부동산 계약서 주요 조항 설명
    
    Args:
        contract_type: 계약 유형 (매매, 전세, 월세)
        is_first_time: 첫 계약 여부
    
    Returns:
        계약서 조항 설명
    """
    logger.info(f"Explaining {contract_type} contract terms")
    
    common_terms = {
        "계약금": "매매가의 10% 정도, 계약 체결 시 지급",
        "중도금": "매매가의 10-80%, 계약 후 잔금 전 지급",
        "잔금": "나머지 금액, 소유권 이전 시 지급",
        "특약사항": "계약 당사자 간 별도 합의 사항",
        "계약해제": "계약 불이행 시 해제 조건",
        "하자담보책임": "매도인의 하자 보수 책임"
    }
    
    if contract_type == "매매":
        specific_terms = {
            "소유권이전": "잔금 지급과 동시에 이전",
            "등기비용": "취득세, 등록세, 법무사 수수료 등",
            "인도시기": "잔금 지급일 또는 별도 약정일",
            "근저당설정": "대출 시 설정되는 담보권",
            "양도소득세": "매도인이 부담하는 세금"
        }
        
        important_clauses = [
            "계약금은 총 매매가의 10%를 넘지 않도록 설정하세요",
            "특약사항에 대출 불승인 시 계약 해제 조항을 넣으세요",
            "등기부등본, 건축물대장 등 서류를 반드시 확인하세요",
            "잔금일 전 현장 확인을 진행하세요"
        ]
        
    elif contract_type == "전세":
        specific_terms = {
            "전세금반환": "계약 종료 시 전액 반환",
            "전세권설정": "전세금 보호를 위한 등기",
            "우선변제권": "확정일자 받은 후 권리",
            "묵시적갱신": "계약 만료 2개월 전 통지 없으면 자동 연장",
            "전세보증보험": "전세금 반환 보장 보험"
        }
        
        important_clauses = [
            "전입신고와 확정일자를 받아 우선변제권을 확보하세요",
            "전세보증보험 가입을 고려하세요",
            "선순위 권리관계를 확인하세요",
            "계약 갱신 시기를 미리 체크하세요"
        ]
        
    else:  # 월세
        specific_terms = {
            "보증금": "계약 기간 동안 맡기는 금액",
            "월세": "매월 지급하는 임대료",
            "관리비": "공용 관리 비용",
            "계약갱신청구권": "2+2년 거주 보장",
            "임대료증액제한": "연 5% 이내 제한"
        }
        
        important_clauses = [
            "보증금과 월세 비율을 확인하세요",
            "관리비 포함 항목을 명확히 하세요",
            "전입신고로 임차권을 보호받으세요",
            "월세 연체 시 조치사항을 확인하세요"
        ]
    
    # 첫 계약자를 위한 추가 팁
    first_timer_tips = [] if not is_first_time else [
        "공인중개사를 통한 거래를 권장합니다",
        "계약 전 법무사나 전문가 검토를 받으세요",
        "급하게 서명하지 말고 충분히 검토하세요",
        "모든 약속은 특약사항에 명시하세요"
    ]
    
    return {
        "status": "success",
        "contract_type": contract_type,
        "terms": {
            "common": common_terms,
            "specific": specific_terms
        },
        "important_clauses": important_clauses,
        "first_timer_tips": first_timer_tips,
        "checklist": generate_contract_checklist(contract_type),
        "red_flags": [
            "시세보다 현저히 낮은 가격",
            "계약금을 과도하게 요구",
            "등기부등본 확인 거부",
            "급하게 계약 종용",
            "특약사항 작성 거부"
        ]
    }


@tool
def calculate_acquisition_tax(
    property_price: int,
    property_type: str = "아파트",
    is_first_home: bool = True,
    area_sqm: float = 85.0,
    location: Optional[str] = None
) -> Dict[str, Any]:
    """
    취득세 상세 계산
    
    Args:
        property_price: 부동산 가격 (원)
        property_type: 부동산 유형
        is_first_home: 생애 첫 주택 여부
        area_sqm: 전용면적 (㎡)
        location: 지역 (조정대상지역 여부 판단)
    
    Returns:
        취득세 계산 결과
    """
    logger.info(f"Calculating acquisition tax for {property_price}원")
    
    # 조정대상지역 여부 (서울, 과천, 성남 등)
    regulated_areas = ["서울", "과천", "성남", "하남", "고양", "남양주", "화성", "세종"]
    is_regulated = any(area in str(location) for area in regulated_areas) if location else False
    
    # 기본 취득세율 결정
    if property_price <= 600000000:  # 6억 이하
        if is_first_home and area_sqm <= 60:
            base_rate = 0.01  # 1% (생애첫주택 감면)
        else:
            base_rate = 0.01  # 1%
    elif property_price <= 900000000:  # 9억 이하
        if is_regulated:
            base_rate = 0.03  # 3% (조정대상지역)
        else:
            base_rate = 0.02  # 2%
    else:  # 9억 초과
        if is_regulated:
            base_rate = 0.03  # 3% (조정대상지역)
        else:
            base_rate = 0.03  # 3%
    
    # 다주택자 중과 (2주택 이상)
    # 실제로는 주택 수를 확인해야 하지만, 여기서는 첫 주택이 아니면 2주택으로 가정
    if not is_first_home and property_price > 900000000:
        if is_regulated:
            base_rate = 0.08  # 8% (조정대상지역 2주택)
        else:
            base_rate = 0.08  # 8% (2주택)
    
    # 취득세 계산
    acquisition_tax = property_price * base_rate
    
    # 지방교육세 (취득세의 10%)
    education_tax = acquisition_tax * 0.1
    
    # 농어촌특별세 (취득세율 2% 이상일 때 취득세의 20%)
    if base_rate >= 0.02:
        rural_tax = acquisition_tax * 0.2
    else:
        rural_tax = 0
    
    # 총 납부세액
    total_tax = acquisition_tax + education_tax + rural_tax
    
    # 감면 혜택 계산
    reduction = 0
    reduction_reasons = []
    
    if is_first_home:
        if property_price <= 600000000 and area_sqm <= 60:
            reduction = acquisition_tax * 0.5  # 50% 감면
            reduction_reasons.append("생애첫주택 구매 (50% 감면)")
        elif property_price <= 900000000:
            reduction_reasons.append("생애첫주택 구매 (감면 혜택 확인 필요)")
    
    # 신혼부부, 다자녀 등 추가 감면 (예시)
    # 실제로는 자격 요건 확인 필요
    
    return {
        "status": "success",
        "property_info": {
            "price": property_price,
            "type": property_type,
            "area_sqm": area_sqm,
            "location": location,
            "is_regulated_area": is_regulated,
            "is_first_home": is_first_home
        },
        "tax_calculation": {
            "base_rate": base_rate * 100,  # 퍼센트로 변환
            "acquisition_tax": int(acquisition_tax),
            "education_tax": int(education_tax),
            "rural_tax": int(rural_tax),
            "total_tax": int(total_tax),
            "reduction": int(reduction),
            "final_tax": int(total_tax - reduction)
        },
        "reduction_info": {
            "amount": int(reduction),
            "reasons": reduction_reasons,
            "additional_reductions": [
                "신혼부부: 취득세 50% 감면 (조건 충족 시)",
                "다자녀: 취득세 감면 (자녀 수에 따라)",
                "청년: 취득세 감면 (연령 및 소득 조건)"
            ]
        },
        "payment_info": {
            "due_date": "취득일로부터 60일 이내",
            "payment_method": "은행, 인터넷뱅킹, 위택스",
            "penalty": "기한 내 미납 시 20% 가산세"
        },
        "formatted": {
            "total_tax": f"{int(total_tax) // 10000}만원",
            "final_tax": f"{int(total_tax - reduction) // 10000}만원",
            "rate": f"{base_rate * 100}%"
        }
    }


@tool
def check_legal_requirements(
    transaction_type: str = "매매",
    property_type: str = "아파트",
    is_foreigner: bool = False
) -> Dict[str, Any]:
    """
    부동산 거래 법적 요건 확인
    
    Args:
        transaction_type: 거래 유형
        property_type: 부동산 유형
        is_foreigner: 외국인 여부
    
    Returns:
        법적 요건 체크리스트
    """
    logger.info(f"Checking legal requirements for {transaction_type}")
    
    # 기본 필요 서류
    basic_documents = {
        "매도인": [
            "신분증",
            "인감증명서",
            "인감도장",
            "등기권리증",
            "주민등록등본"
        ],
        "매수인": [
            "신분증",
            "인감증명서",
            "인감도장",
            "주민등록등본",
            "소득증빙서류 (대출 시)"
        ]
    }
    
    # 확인 필요 서류
    verification_documents = [
        "등기부등본 (최신)",
        "건축물대장",
        "토지대장",
        "지적도",
        "개발행위허가증 (필요시)"
    ]
    
    # 거래 유형별 특별 요건
    if transaction_type == "매매":
        special_requirements = [
            "실거래 신고 (계약일로부터 30일 이내)",
            "자금조달계획서 제출 (일정 금액 이상)",
            "양도소득세 신고 (매도인)",
            "취득세 납부 (매수인, 60일 이내)"
        ]
        
        legal_restrictions = [
            "투기과열지구: 주택담보대출 규제 강화",
            "조정대상지역: 전매제한, 대출규제",
            "토지거래허가구역: 사전 허가 필요"
        ]
        
    elif transaction_type == "전세":
        special_requirements = [
            "확정일자 받기 (전입신고 후)",
            "전입신고 (입주 후 즉시)",
            "임대차 신고 (계약일로부터 30일 이내)",
            "전세보증보험 가입 검토"
        ]
        
        legal_restrictions = [
            "임대차 3법: 계약갱신청구권, 전월세상한제",
            "전세금 반환 보증 의무화 (일부 지역)"
        ]
        
    else:  # 월세
        special_requirements = [
            "확정일자 받기",
            "전입신고",
            "임대차 신고",
            "월세 소득공제 신청 가능"
        ]
        
        legal_restrictions = [
            "임대료 증액 제한 (연 5%)",
            "계약갱신청구권 (2+2년)"
        ]
    
    # 외국인 특별 요건
    foreigner_requirements = [] if not is_foreigner else [
        "외국인 부동산 취득신고 (계약일로부터 60일 이내)",
        "외국인등록증 또는 여권",
        "부동산투자이민제 검토 (일정 금액 이상)",
        "송금증명서 (해외 자금 사용 시)"
    ]
    
    # 권리 분석 체크포인트
    rights_checkpoints = [
        "소유권 확인: 등기부등본 갑구",
        "저당권 확인: 등기부등본 을구",
        "임차권 확인: 전세권, 임차권 설정 여부",
        "가압류, 가처분 확인",
        "재개발, 재건축 여부 확인"
    ]
    
    return {
        "status": "success",
        "transaction_type": transaction_type,
        "required_documents": {
            "basic": basic_documents,
            "verification": verification_documents
        },
        "legal_requirements": {
            "special": special_requirements,
            "restrictions": legal_restrictions,
            "foreigner": foreigner_requirements
        },
        "rights_analysis": {
            "checkpoints": rights_checkpoints,
            "red_flags": [
                "다수의 근저당 설정",
                "가압류, 가처분 존재",
                "소유권 분쟁",
                "건축법 위반 건축물",
                "재개발, 재건축 예정"
            ]
        },
        "timeline": generate_transaction_timeline(transaction_type),
        "tips": [
            "모든 서류는 최신본으로 확인하세요",
            "공인중개사 자격 확인은 필수입니다",
            "계약 전 법무사 검토를 권장합니다",
            "특약사항은 명확하게 작성하세요"
        ]
    }


@tool
def provide_legal_guidelines(
    topic: str,
    user_type: str = "buyer"
) -> Dict[str, Any]:
    """
    부동산 관련 법률 가이드라인 제공
    
    Args:
        topic: 법률 주제 (임대차보호법, 재개발, 상속 등)
        user_type: 사용자 유형 (buyer, seller, tenant, landlord)
    
    Returns:
        법률 가이드라인
    """
    logger.info(f"Providing legal guidelines for {topic}")
    
    guidelines = {}
    
    if "임대차" in topic or "전세" in topic:
        guidelines["임대차보호법"] = {
            "주요내용": [
                "대항력: 주택 인도 + 전입신고",
                "우선변제권: 대항력 + 확정일자",
                "최우선변제권: 소액임차인 보호",
                "계약갱신청구권: 2+2년 거주 보장",
                "전월세전환율 제한: 기준금리 + 3.5%"
            ],
            "임차인권리": [
                "계약 갱신 요구권 (2회)",
                "묵시적 갱신",
                "임대료 증액 제한 (5%)",
                "수선 요구권"
            ],
            "주의사항": [
                "전입신고는 입주 즉시",
                "확정일자는 전입신고와 같은 날",
                "보증금 증액 시 재확정일자 필요",
                "특약사항 꼼꼼히 확인"
            ]
        }
    
    if "재개발" in topic or "재건축" in topic:
        guidelines["재개발재건축"] = {
            "절차": [
                "정비구역 지정",
                "조합 설립",
                "사업시행인가",
                "관리처분계획",
                "이주 및 철거",
                "착공 및 준공",
                "입주"
            ],
            "권리": [
                "조합원 자격",
                "분양권",
                "현금청산권",
                "매도청구권"
            ],
            "주의사항": [
                "조합원 자격 확인",
                "추가 분담금 예상",
                "사업 지연 가능성",
                "투기과열지구 규제"
            ]
        }
    
    if "상속" in topic:
        guidelines["부동산상속"] = {
            "절차": [
                "사망신고",
                "상속인 확정",
                "상속세 신고 (6개월 이내)",
                "상속등기",
                "취득세 납부"
            ],
            "상속세": [
                "공제: 배우자 5억, 자녀 5천만원",
                "세율: 10~50% 누진세",
                "분납: 최대 5년",
                "연부연납: 최대 20년"
            ],
            "주의사항": [
                "상속포기는 3개월 이내",
                "한정승인 고려",
                "공동상속인 협의 필요",
                "채무 승계 주의"
            ]
        }
    
    if "양도세" in topic or "세금" in topic:
        guidelines["양도소득세"] = {
            "세율": {
                "1년미만": "50% (단기)",
                "1년이상": "6~45% (누진)",
                "1세대1주택": "비과세 (조건 충족시)"
            },
            "비과세요건": [
                "1세대 1주택",
                "2년 이상 보유",
                "실거주 2년 (조정대상지역)",
                "9억원 이하 (고가주택 제외)"
            ],
            "중과세": [
                "다주택자 중과",
                "조정대상지역 +10~20%",
                "단기 양도 중과"
            ]
        }
    
    # 사용자 유형별 추가 조언
    user_specific_advice = {
        "buyer": [
            "계약 전 권리관계 철저히 확인",
            "대출 승인 후 계약 진행",
            "하자 확인 및 기록",
            "등기 이전까지 주의"
        ],
        "seller": [
            "양도세 사전 계산",
            "권리 하자 사전 해결",
            "정확한 정보 고지 의무",
            "계약금 반환 조건 명시"
        ],
        "tenant": [
            "전입신고 즉시 진행",
            "확정일자 필수",
            "보증보험 가입 검토",
            "계약서 보관 철저"
        ],
        "landlord": [
            "임대 신고 의무",
            "세금 신고",
            "수선 의무 이행",
            "보증금 반환 준비"
        ]
    }
    
    return {
        "status": "success",
        "topic": topic,
        "guidelines": guidelines,
        "user_type": user_type,
        "specific_advice": user_specific_advice.get(user_type, []),
        "legal_updates": [
            "2024년 임대차 3법 시행",
            "2024년 부동산 세제 개편",
            "전세사기 방지법 강화"
        ],
        "resources": [
            "법무부 법률홈닥터",
            "국토교통부 실거래가 공개시스템",
            "대한법률구조공단",
            "한국공인중개사협회"
        ]
    }


@tool
def analyze_contract_risks(
    contract_content: Optional[str] = None,
    property_price: int = 0,
    deposit: int = 0,
    special_terms: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    계약 위험 분석
    
    Args:
        contract_content: 계약서 내용
        property_price: 매매가/전세가
        deposit: 계약금/보증금
        special_terms: 특약사항
    
    Returns:
        위험 분석 결과
    """
    logger.info("Analyzing contract risks")
    
    risk_factors = []
    risk_level = "낮음"
    
    # 가격 관련 위험
    if property_price > 0:
        if deposit > property_price * 0.2:
            risk_factors.append({
                "type": "과도한 계약금",
                "level": "높음",
                "description": "계약금이 20%를 초과하면 위험합니다",
                "mitigation": "계약금을 10% 이내로 조정하세요"
            })
            risk_level = "높음"
    
    # 특약사항 분석
    risky_terms = [
        "위약금 과다",
        "일방적 해제",
        "하자 면책",
        "현상 그대로 인수"
    ]
    
    safe_terms = [
        "대출 불승인 시 계약 해제",
        "하자 발견 시 보수 요구",
        "잔금 지급 전 시설 점검",
        "등기 완료 후 잔금 지급"
    ]
    
    if special_terms:
        for term in special_terms:
            term_lower = term.lower()
            for risky in risky_terms:
                if risky in term_lower:
                    risk_factors.append({
                        "type": "위험 특약",
                        "level": "중간",
                        "description": f"'{risky}' 관련 조항 주의",
                        "mitigation": "조항 수정 또는 삭제 요구"
                    })
    
    # 일반적 위험 요소
    common_risks = [
        {
            "type": "권리관계",
            "check_items": [
                "근저당 설정 확인",
                "전세권 설정 확인",
                "가압류/가처분 확인"
            ],
            "level": "중간"
        },
        {
            "type": "시장 위험",
            "check_items": [
                "시세 대비 가격",
                "지역 개발 계획",
                "인근 공급 물량"
            ],
            "level": "낮음"
        },
        {
            "type": "법적 위험",
            "check_items": [
                "건축법 위반 여부",
                "용도 변경 가능성",
                "재개발/재건축 여부"
            ],
            "level": "중간"
        }
    ]
    
    # 위험 점수 계산 (100점 만점)
    risk_score = len(risk_factors) * 15
    risk_score = min(100, risk_score)
    
    if risk_score > 70:
        risk_level = "높음"
    elif risk_score > 40:
        risk_level = "중간"
    else:
        risk_level = "낮음"
    
    return {
        "status": "success",
        "risk_assessment": {
            "overall_level": risk_level,
            "risk_score": risk_score,
            "identified_risks": risk_factors,
            "common_risks": common_risks
        },
        "recommendations": {
            "immediate_actions": [
                "등기부등본 최신본 확인",
                "건축물대장 확인",
                "현장 실사 진행",
                "전문가 검토 의뢰"
            ] if risk_level != "낮음" else ["기본 서류 확인"],
            "protective_measures": [
                "특약사항 보완",
                "보증보험 가입",
                "에스크로 이용",
                "공증 진행"
            ]
        },
        "safe_contract_tips": safe_terms,
        "warning_signs": [
            "급하게 계약 종용",
            "서류 확인 거부",
            "현금 거래 요구",
            "특약 작성 거부",
            "시세보다 현저히 낮은 가격"
        ]
    }


# 헬퍼 함수들
def generate_contract_checklist(contract_type: str) -> List[str]:
    """계약 체크리스트 생성"""
    checklist = [
        "신분증 확인",
        "등기부등본 확인",
        "인감증명서 확인",
        "계약서 내용 검토",
        "특약사항 작성"
    ]
    
    if contract_type == "매매":
        checklist.extend([
            "매매가 및 지급 일정 확인",
            "취득세 계산",
            "대출 승인 확인",
            "소유권 이전 일정"
        ])
    elif contract_type == "전세":
        checklist.extend([
            "전세금 및 인상률 확인",
            "전세보증보험 가입 가능 여부",
            "확정일자 받기",
            "전입신고 일정"
        ])
    
    return checklist


def generate_transaction_timeline(transaction_type: str) -> List[Dict[str, str]]:
    """거래 타임라인 생성"""
    if transaction_type == "매매":
        timeline = [
            {"step": "계약", "timeline": "D-Day", "action": "계약금 지급 (10%)"},
            {"step": "중도금", "timeline": "D+30일", "action": "중도금 지급 (필요시)"},
            {"step": "잔금", "timeline": "D+60일", "action": "잔금 지급 및 소유권 이전"},
            {"step": "취득세", "timeline": "D+120일 이내", "action": "취득세 납부"},
            {"step": "실거래신고", "timeline": "D+30일 이내", "action": "실거래 신고"}
        ]
    elif transaction_type == "전세":
        timeline = [
            {"step": "계약", "timeline": "D-Day", "action": "계약금 지급 (5-10%)"},
            {"step": "잔금", "timeline": "입주일", "action": "잔금 지급"},
            {"step": "전입신고", "timeline": "입주 즉시", "action": "주민센터 전입신고"},
            {"step": "확정일자", "timeline": "전입신고 당일", "action": "확정일자 받기"},
            {"step": "임대차신고", "timeline": "D+30일 이내", "action": "임대차 신고"}
        ]
    else:
        timeline = [
            {"step": "계약", "timeline": "D-Day", "action": "보증금 일부 지급"},
            {"step": "입주", "timeline": "약정일", "action": "잔여 보증금 및 첫 월세"},
            {"step": "전입신고", "timeline": "입주 즉시", "action": "전입신고 및 확정일자"}
        ]
    
    return timeline


# 도구 목록
LEGAL_TOOLS = [
    explain_contract_terms,
    calculate_acquisition_tax,
    check_legal_requirements,
    provide_legal_guidelines,
    analyze_contract_risks
]