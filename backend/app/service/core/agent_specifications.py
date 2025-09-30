"""
Agent Specifications for Real Estate Chatbot
============================================

이 파일은 모든 Agent의 상세 명세를 포함합니다.
LLM이나 개발자가 각 Agent의 역할과 기능을 명확히 이해할 수 있도록 작성되었습니다.

IMPORTANT FOR LLM/AI:
- 각 Agent는 특정 도메인의 전문가입니다
- Agent 선택 시 이 명세를 참고하여 가장 적합한 Agent를 선택하세요
- 각 Agent의 capabilities와 limitations를 반드시 확인하세요

Agent Specification Document for Real Estate Chatbot System
This document defines the capabilities, inputs, outputs, and behaviors of each agent.
"""

from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(Enum):
    """Agent 구현 상태"""
    PRODUCTION = "production"       # 운영 중
    DEVELOPMENT = "development"     # 개발 중
    PLANNED = "planned"            # 계획됨
    DEPRECATED = "deprecated"      # 사용 중단 예정


class ToolSpecification(TypedDict):
    """도구 명세"""
    name: str                      # 도구 이름
    description: str               # 도구 설명
    parameters: Dict[str, Any]     # 필요한 파라미터
    output_type: str              # 출력 타입
    example_usage: str            # 사용 예시


class InputSchema(TypedDict):
    """Agent 입력 스키마"""
    required_fields: List[str]    # 필수 필드
    optional_fields: List[str]    # 선택 필드
    field_descriptions: Dict[str, str]  # 필드별 설명
    example: Dict[str, Any]       # 입력 예시


class OutputSchema(TypedDict):
    """Agent 출력 스키마"""
    success_fields: List[str]     # 성공 시 출력 필드
    error_fields: List[str]       # 실패 시 출력 필드
    field_descriptions: Dict[str, str]  # 필드별 설명
    example: Dict[str, Any]       # 출력 예시


@dataclass
class AgentSpecification:
    """
    Agent 명세서 - 각 Agent의 완전한 사양을 정의

    LLM Instructions:
    - Use this specification to understand agent capabilities
    - Select agents based on their purpose and capabilities
    - Check prerequisites before agent execution
    - Validate outputs against success_criteria
    """

    # === 기본 정보 ===
    agent_name: str                    # Agent 이름 (시스템에서 사용)
    display_name: str                  # 표시 이름 (사용자에게 보여질 이름)
    version: str                       # 버전
    status: AgentStatus                # 현재 상태

    # === 목적과 역할 ===
    purpose: str                       # Agent의 주요 목적 (한 문장)
    description: str                   # 상세 설명
    domain: str                        # 전문 도메인 (예: "검색", "분석", "추천")

    # === 기능 (Capabilities) ===
    capabilities: List[str]            # Agent가 할 수 있는 작업 목록
    limitations: List[str]             # Agent가 할 수 없는 작업 목록

    # === 입출력 스키마 ===
    input_schema: InputSchema          # 입력 데이터 구조
    output_schema: OutputSchema        # 출력 데이터 구조

    # === 사용 가능한 도구 ===
    available_tools: List[ToolSpecification] = field(default_factory=list)

    # === 실행 흐름 ===
    execution_steps: List[str] = field(default_factory=list)  # 실행 단계 설명

    # === 성공/실패 기준 ===
    success_criteria: List[str] = field(default_factory=list)  # 성공 조건
    failure_conditions: List[str] = field(default_factory=list)  # 실패 조건

    # === 사용 시나리오 ===
    use_cases: List[str] = field(default_factory=list)        # 적합한 사용 케이스
    not_suitable_for: List[str] = field(default_factory=list)  # 부적합한 케이스

    # === 전제 조건 ===
    prerequisites: List[str] = field(default_factory=list)     # 실행 전 필요 조건

    # === 성능 지표 ===
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    # 예: {"average_execution_time": "2-3초", "success_rate": "95%"}

    # === 의존성 ===
    dependencies: List[str] = field(default_factory=list)      # 다른 Agent나 서비스 의존성

    # === LLM 프롬프트 가이드 ===
    llm_guidance: str = ""  # LLM이 이 Agent를 사용할 때 참고할 가이드

    # === 예시 ===
    example_queries: List[str] = field(default_factory=list)   # 이 Agent가 처리하는 쿼리 예시


# ============================================================================
# AGENT SPECIFICATIONS REGISTRY
# ============================================================================

AGENT_SPECIFICATIONS: Dict[str, AgentSpecification] = {

    # ====================
    # SearchAgent
    # ====================
    "search_agent": AgentSpecification(
        agent_name="search_agent",
        display_name="검색 에이전트",
        version="1.0.0",
        status=AgentStatus.PRODUCTION,

        # 목적과 역할
        purpose="부동산 관련 데이터를 검색하고 수집하는 전문 Agent",
        description="""
        다양한 부동산 데이터 소스에서 정보를 검색하고 수집합니다.
        법률, 규정, 대출, 매물 정보 등 여러 도구를 활용하여 종합적인 데이터를 제공합니다.
        수집된 데이터를 구조화하여 다른 Agent나 사용자에게 전달합니다.
        """,
        domain="데이터 검색 및 수집",

        # 기능
        capabilities=[
            "부동산 매물 정보 검색",
            "시세 정보 조회",
            "법률 및 규정 검색",
            "대출 상품 정보 수집",
            "여러 데이터 소스 병렬 검색",
            "검색 결과 구조화 및 요약"
        ],
        limitations=[
            "데이터 분석이나 인사이트 도출 불가",
            "추천 로직 수행 불가",
            "복잡한 계산이나 예측 불가"
        ],

        # 입출력 스키마
        input_schema={
            "required_fields": ["original_query", "collection_keywords"],
            "optional_fields": ["shared_context", "chat_session_id", "search_filters"],
            "field_descriptions": {
                "original_query": "사용자의 원본 질의",
                "collection_keywords": "검색할 키워드 리스트",
                "shared_context": "이전 단계에서 전달된 컨텍스트",
                "chat_session_id": "채팅 세션 ID",
                "search_filters": "검색 필터 (지역, 가격대 등)"
            },
            "example": {
                "original_query": "강남구 아파트 매매 시세와 대출 정보",
                "collection_keywords": ["강남구", "아파트", "매매", "시세", "대출"],
                "chat_session_id": "session_123"
            }
        },

        output_schema={
            "success_fields": ["status", "collected_data", "data_summary", "next_action"],
            "error_fields": ["status", "error", "error_details"],
            "field_descriptions": {
                "status": "실행 상태 (success/error)",
                "collected_data": "수집된 데이터 딕셔너리",
                "data_summary": "데이터 요약 텍스트",
                "next_action": "다음 액션 제안",
                "error": "에러 메시지",
                "error_details": "상세 에러 정보"
            },
            "example": {
                "status": "success",
                "collected_data": {
                    "real_estate_search": [{"title": "강남구 아파트", "price": "15억"}],
                    "loan_search": [{"product": "주택담보대출", "rate": "3.5%"}]
                },
                "data_summary": "강남구 아파트 5개, 대출상품 3개 검색됨",
                "next_action": "return_to_supervisor"
            }
        },

        # 사용 가능한 도구
        available_tools=[
            {
                "name": "legal_search",
                "description": "부동산 법률 정보 검색",
                "parameters": {"query": "str", "filters": "dict"},
                "output_type": "list[dict]",
                "example_usage": "legal_search(query='부동산 계약서', filters={'category': '매매'})"
            },
            {
                "name": "regulation_search",
                "description": "부동산 규정 및 정책 검색",
                "parameters": {"query": "str", "region": "str"},
                "output_type": "list[dict]",
                "example_usage": "regulation_search(query='재건축 규제', region='강남구')"
            },
            {
                "name": "loan_search",
                "description": "부동산 대출 상품 검색",
                "parameters": {"query": "str", "loan_type": "str"},
                "output_type": "list[dict]",
                "example_usage": "loan_search(query='주택담보대출', loan_type='변동금리')"
            },
            {
                "name": "real_estate_search",
                "description": "부동산 매물 및 시세 검색",
                "parameters": {"query": "str", "region": "str", "property_type": "str"},
                "output_type": "list[dict]",
                "example_usage": "real_estate_search(query='아파트', region='강남구', property_type='매매')"
            }
        ],

        # 실행 흐름
        execution_steps=[
            "1. 입력된 키워드 분석",
            "2. 적절한 검색 도구 선택",
            "3. 검색 계획 수립 (LLM 활용)",
            "4. 선택된 도구들 병렬 실행",
            "5. 검색 결과 수집 및 정리",
            "6. 데이터 품질 평가",
            "7. 다음 액션 결정 (supervisor 복귀 or 다른 agent 호출)"
        ],

        # 성공/실패 기준
        success_criteria=[
            "최소 1개 이상의 관련 데이터 수집",
            "데이터 품질 점수 0.5 이상",
            "에러 없이 모든 단계 완료"
        ],
        failure_conditions=[
            "모든 도구 실행 실패",
            "타임아웃 (30초 초과)",
            "필수 입력 필드 누락"
        ],

        # 사용 시나리오
        use_cases=[
            "부동산 매물 정보가 필요한 경우",
            "시세 조회가 필요한 경우",
            "법률/규정 정보 검색이 필요한 경우",
            "대출 정보 수집이 필요한 경우",
            "여러 종류의 정보를 동시에 수집해야 하는 경우"
        ],
        not_suitable_for=[
            "복잡한 데이터 분석이 필요한 경우",
            "투자 추천이 필요한 경우",
            "미래 가격 예측이 필요한 경우"
        ],

        # 전제 조건
        prerequisites=[
            "검색 키워드가 명확해야 함",
            "LLM API 연결 가능",
            "검색 도구들이 정상 작동"
        ],

        # 성능 지표
        performance_metrics={
            "average_execution_time": "3-5초",
            "success_rate": "92%",
            "max_parallel_tools": 4,
            "timeout": "30초"
        },

        # 의존성
        dependencies=[
            "OpenAI API",
            "Tool Registry (legal, regulation, loan, real_estate)",
            "LangGraph Framework"
        ],

        # LLM 가이드
        llm_guidance="""
        SearchAgent 사용 시 주의사항:
        1. 명확한 키워드를 제공해야 합니다
        2. 여러 도구를 동시에 사용할 수 있습니다
        3. 단순 검색만 가능하며, 분석은 다른 Agent를 사용하세요
        4. 검색 결과는 항상 구조화된 형태로 반환됩니다
        """,

        # 예시 쿼리
        example_queries=[
            "강남구 아파트 매매 시세",
            "전세 대출 조건",
            "부동산 계약서 작성 방법",
            "재건축 규제 정보"
        ]
    ),

    # ====================
    # AnalysisAgent
    # ====================
    "analysis_agent": AgentSpecification(
        agent_name="analysis_agent",
        display_name="분석 에이전트",
        version="1.0.0",
        status=AgentStatus.PRODUCTION,

        purpose="수집된 부동산 데이터를 분석하여 인사이트를 도출하는 전문 Agent",
        description="""
        SearchAgent가 수집한 데이터나 직접 입력된 데이터를 분석하여 시장 트렌드, 투자 가치, 리스크 등을 평가합니다.
        다양한 분석 도구를 활용하여 데이터 기반의 객관적인 인사이트를 제공합니다.
        LLM을 활용하여 분석 결과를 종합하고 실행 가능한 추천사항을 도출합니다.
        """,
        domain="데이터 분석 및 인사이트 도출",

        # 기능
        capabilities=[
            "시장 현황 분석 (가격, 거래량, 수급)",
            "가격 트렌드 및 패턴 분석",
            "지역별/단지별 비교 분석",
            "투자 가치 평가 (ROI, 수익률)",
            "리스크 요인 식별 및 평가",
            "데이터 기반 추천사항 제공",
            "분석 결과 시각화 데이터 준비"
        ],
        limitations=[
            "미래 가격 정확한 예측 불가",
            "법적 구속력 있는 조언 제공 불가",
            "개인 맞춤 투자 전략 수립 불가",
            "실시간 시장 데이터 접근 불가"
        ],

        # 입출력 스키마
        input_schema={
            "required_fields": ["original_query", "analysis_type", "input_data"],
            "optional_fields": ["shared_context", "chat_session_id", "analysis_parameters"],
            "field_descriptions": {
                "original_query": "사용자의 원본 분석 요청",
                "analysis_type": "분석 유형 (market, trend, comparative, investment, comprehensive)",
                "input_data": "분석할 데이터 (SearchAgent 결과 또는 직접 입력)",
                "shared_context": "이전 Agent로부터 전달된 컨텍스트",
                "chat_session_id": "채팅 세션 ID",
                "analysis_parameters": "분석 파라미터 (깊이, 초점 영역 등)"
            },
            "example": {
                "original_query": "강남구 아파트 시장 분석해줘",
                "analysis_type": "comprehensive",
                "input_data": {
                    "real_estate_search": [
                        {"title": "래미안 강남", "price": "25억", "region": "강남구"}
                    ]
                },
                "chat_session_id": "session_123"
            }
        },

        output_schema={
            "success_fields": ["status", "final_report", "key_metrics", "next_action"],
            "error_fields": ["status", "error", "error_details"],
            "field_descriptions": {
                "status": "실행 상태 (completed/error)",
                "final_report": "종합 분석 보고서",
                "key_metrics": "핵심 지표 요약",
                "next_action": "다음 액션 (return_to_supervisor/direct_output)",
                "error": "에러 메시지",
                "error_details": "상세 에러 정보"
            },
            "example": {
                "status": "completed",
                "final_report": {
                    "summary": "강남구 아파트 시장은 안정적인 상승세",
                    "key_findings": {
                        "insights": ["평균 가격 25억원", "거래량 증가 추세"],
                        "recommendations": ["중장기 투자 적합"],
                        "risks": ["금리 인상 리스크"],
                        "opportunities": ["재건축 기회"]
                    },
                    "detailed_analysis": {},
                    "confidence": {"overall": 0.85}
                },
                "key_metrics": {
                    "average_price": "25억",
                    "price_change": "+5.2%",
                    "market_heat_index": 72.5
                },
                "next_action": "return_to_supervisor"
            }
        },

        # 사용 가능한 도구
        available_tools=[
            {
                "name": "market_analyzer",
                "description": "시장 현황 분석 (가격, 거래량, 수급)",
                "parameters": {"data": "dict", "params": "dict"},
                "output_type": "dict",
                "example_usage": "market_analyzer.analyze(data, params)"
            },
            {
                "name": "trend_analyzer",
                "description": "가격 및 거래 트렌드 분석",
                "parameters": {"data": "dict", "period": "str"},
                "output_type": "dict",
                "example_usage": "trend_analyzer.analyze(data, {'period': '3months'})"
            },
            {
                "name": "comparative_analyzer",
                "description": "지역/단지별 비교 분석",
                "parameters": {"data": "dict", "comparison_type": "str"},
                "output_type": "dict",
                "example_usage": "comparative_analyzer.analyze(data, params)"
            },
            {
                "name": "investment_evaluator",
                "description": "투자 가치 평가",
                "parameters": {"data": "dict", "investment_params": "dict"},
                "output_type": "dict",
                "example_usage": "investment_evaluator.analyze(data, params)"
            },
            {
                "name": "risk_assessor",
                "description": "리스크 요인 평가",
                "parameters": {"data": "dict", "risk_params": "dict"},
                "output_type": "dict",
                "example_usage": "risk_assessor.analyze(data, params)"
            }
        ],

        # 실행 흐름
        execution_steps=[
            "1. 분석 요청 이해 및 데이터 확인",
            "2. 데이터 전처리 및 검증",
            "3. LLM을 통한 분석 계획 수립",
            "4. 선택된 분석 도구 실행",
            "5. 분석 결과 종합 및 인사이트 도출",
            "6. 최종 보고서 생성",
            "7. 라우팅 결정 (supervisor 복귀 또는 직접 출력)"
        ],

        # 성공/실패 기준
        success_criteria=[
            "최소 1개 이상의 분석 완료",
            "인사이트 도출 성공",
            "최종 보고서 생성 완료"
        ],
        failure_conditions=[
            "입력 데이터 부족",
            "모든 분석 도구 실행 실패",
            "타임아웃 (30초 초과)"
        ],

        # 사용 시나리오
        use_cases=[
            "시장 트렌드 분석이 필요한 경우",
            "투자 가치 평가가 필요한 경우",
            "지역간 비교 분석이 필요한 경우",
            "리스크 평가가 필요한 경우",
            "SearchAgent 수집 데이터의 심층 분석이 필요한 경우"
        ],
        not_suitable_for=[
            "단순 정보 조회만 필요한 경우",
            "실시간 데이터가 필요한 경우",
            "법률 자문이 필요한 경우",
            "개인 맞춤 투자 전략이 필요한 경우"
        ],

        # 전제 조건
        prerequisites=[
            "분석할 데이터가 준비되어 있어야 함",
            "LLM API 연결 가능",
            "분석 도구들이 정상 작동"
        ],

        # 성능 지표
        performance_metrics={
            "average_execution_time": "5-10초",
            "success_rate": "88%",
            "max_parallel_tools": 5,
            "timeout": "30초"
        },

        # 의존성
        dependencies=[
            "OpenAI API",
            "Analysis Tools (market, trend, comparative, investment, risk)",
            "LangGraph Framework"
        ],

        # LLM 가이드
        llm_guidance="""
        AnalysisAgent 사용 시 주의사항:
        1. SearchAgent에서 수집된 데이터를 우선적으로 활용
        2. analysis_type에 따라 적절한 분석 도구 선택
        3. 여러 분석 도구를 조합하여 종합적인 인사이트 도출
        4. 데이터가 부족한 경우 SearchAgent 재실행 제안
        5. 분석 결과는 항상 구조화된 보고서 형태로 제공
        """,

        # 예시 쿼리
        example_queries=[
            "강남구 아파트 시장 트렌드 분석해줘",
            "이 지역 투자 가치 평가해줘",
            "서초구와 강남구 아파트 비교 분석",
            "부동산 투자 리스크 평가해줘",
            "수집된 데이터로 종합 분석 보고서 만들어줘"
        ]
    ),

    # ====================
    # RecommendationAgent (예시 - 구현 예정)
    # ====================
    "recommendation_agent": AgentSpecification(
        agent_name="recommendation_agent",
        display_name="추천 에이전트",
        version="0.1.0",
        status=AgentStatus.PLANNED,

        purpose="사용자 요구사항에 맞는 부동산 추천을 제공하는 전문 Agent",
        description="""
        [구현 예정]
        사용자의 조건과 선호도를 분석하여 최적의 부동산을 추천합니다.
        """,
        domain="추천 시스템",

        capabilities=[
            # TODO: 채워주세요
        ],
        limitations=[
            # TODO: 채워주세요
        ],

        input_schema={
            "required_fields": [],  # TODO
            "optional_fields": [],  # TODO
            "field_descriptions": {},  # TODO
            "example": {}  # TODO
        },

        output_schema={
            "success_fields": [],  # TODO
            "error_fields": [],  # TODO
            "field_descriptions": {},  # TODO
            "example": {}  # TODO
        }
    )
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent_specification(agent_name: str) -> Optional[AgentSpecification]:
    """
    Agent 명세 조회

    Args:
        agent_name: Agent 이름

    Returns:
        AgentSpecification or None
    """
    return AGENT_SPECIFICATIONS.get(agent_name)


def list_available_agents() -> List[str]:
    """
    사용 가능한 Agent 목록 반환

    Returns:
        Agent 이름 리스트
    """
    return [
        name for name, spec in AGENT_SPECIFICATIONS.items()
        if spec.status == AgentStatus.PRODUCTION
    ]


def list_all_agents() -> Dict[str, str]:
    """
    모든 Agent와 상태 반환

    Returns:
        {agent_name: status} 딕셔너리
    """
    return {
        name: spec.status.value
        for name, spec in AGENT_SPECIFICATIONS.items()
    }


def get_agents_by_domain(domain: str) -> List[str]:
    """
    특정 도메인의 Agent 목록 반환

    Args:
        domain: 도메인 이름

    Returns:
        Agent 이름 리스트
    """
    return [
        name for name, spec in AGENT_SPECIFICATIONS.items()
        if spec.domain == domain and spec.status == AgentStatus.PRODUCTION
    ]


def get_agent_capabilities(agent_name: str) -> List[str]:
    """
    Agent의 기능 목록 반환

    Args:
        agent_name: Agent 이름

    Returns:
        기능 리스트
    """
    spec = get_agent_specification(agent_name)
    return spec.capabilities if spec else []


# ============================================================================
# LLM INSTRUCTIONS
# ============================================================================

LLM_INSTRUCTIONS = """
## Agent 선택 가이드 (LLM용)

이 명세서를 사용하여 적절한 Agent를 선택하세요:

1. **사용자 의도 파악**
   - 사용자가 원하는 것이 무엇인지 명확히 파악
   - 필요한 작업 유형 확인 (검색, 분석, 추천 등)

2. **Agent 매칭**
   - 각 Agent의 purpose와 capabilities 확인
   - use_cases와 사용자 요구사항 비교
   - limitations 확인하여 부적합한 Agent 제외

3. **실행 계획 수립**
   - 필요한 Agent들의 조합 결정
   - 실행 순서 결정 (순차/병렬)
   - 각 Agent의 prerequisites 확인

4. **입력 데이터 준비**
   - 각 Agent의 input_schema 확인
   - required_fields 모두 준비
   - 데이터 형식 검증

5. **성공 기준 설정**
   - 각 Agent의 success_criteria 확인
   - 전체 작업의 성공 기준 정의

## 사용 예시

```python
# Agent 명세 조회
spec = get_agent_specification("search_agent")

# 사용 가능 여부 확인
if spec and spec.status == AgentStatus.PRODUCTION:
    # Agent 실행 준비
    input_data = {
        "original_query": "강남구 아파트",
        "collection_keywords": ["강남구", "아파트"]
    }
    # Agent 실행...
```
"""


if __name__ == "__main__":
    # 명세서 테스트
    print("=== Available Agents ===")
    for agent in list_available_agents():
        spec = get_agent_specification(agent)
        print(f"- {spec.display_name}: {spec.purpose}")

    print("\n=== All Agents Status ===")
    for agent, status in list_all_agents().items():
        print(f"- {agent}: {status}")