"""
Data API Routes
Mock 데이터베이스 검색 및 조회 API
"""

from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services import (
    get_database_service,
    get_vector_search_service,
    get_hybrid_search_service
)

# 라우터 생성
router = APIRouter(prefix="/api/v1/data", tags=["data"])

# === Request/Response Models ===

class SearchRequest(BaseModel):
    """검색 요청 모델"""
    query: str = Field(..., description="검색 쿼리")
    search_type: str = Field("all", description="검색 유형")
    filters: Optional[Dict[str, Any]] = Field(None, description="필터 조건")
    top_k: int = Field(10, description="결과 개수", ge=1, le=100)
    weights: Optional[Dict[str, float]] = Field(None, description="가중치")

class SearchResponse(BaseModel):
    """검색 응답 모델"""
    query: str
    search_type: str
    results: List[Dict[str, Any]]
    facets: Dict[str, Dict[str, int]]
    suggestions: List[str]
    metadata: Dict[str, Any]

class VectorSearchRequest(BaseModel):
    """벡터 검색 요청"""
    query: str
    category: str = Field("subscription", description="검색 카테고리")
    top_k: int = Field(5, ge=1, le=50)
    min_similarity: float = Field(0.1, ge=0, le=1)

# === 통합 검색 ===

@router.post("/search", response_model=SearchResponse)
async def search_data(request: SearchRequest) -> SearchResponse:
    """
    통합 데이터 검색
    
    - 키워드 검색
    - 벡터 검색
    - 하이브리드 검색
    """
    try:
        service = get_hybrid_search_service()
        
        result = service.search(
            query=request.query,
            search_type=request.search_type,
            filters=request.filters,
            top_k=request.top_k,
            weights=request.weights
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.post("/vector-search")
async def vector_search(request: VectorSearchRequest) -> Dict[str, Any]:
    """
    벡터 기반 검색
    
    청약 통계 및 대출 정보 검색
    """
    try:
        service = get_vector_search_service()
        
        if request.category == "subscription":
            results = service.search_subscription(
                query=request.query,
                top_k=request.top_k,
                min_similarity=request.min_similarity
            )
        elif request.category == "loan":
            results = service.search_loan(
                query=request.query,
                top_k=request.top_k,
                min_similarity=request.min_similarity
            )
        else:
            results = []
        
        return {
            "query": request.query,
            "category": request.category,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )

# === 법령 및 판례 ===

@router.get("/laws")
async def get_laws(
    category: Optional[str] = Query(None, description="법령 카테고리")
) -> Dict[str, Any]:
    """부동산 관련 법령 조회"""
    try:
        service = get_database_service()
        laws = service.get_laws(category)
        
        return {
            "category": category,
            "laws": laws,
            "count": len(laws)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/cases")
async def get_recent_cases(
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """최근 판례 조회"""
    try:
        service = get_database_service()
        cases = service.get_recent_cases(limit)
        
        return {
            "cases": cases,
            "count": len(cases)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 용어 사전 ===

@router.get("/dictionary")
async def search_dictionary(
    keyword: str = Query(..., description="검색 키워드")
) -> Dict[str, Any]:
    """부동산 용어 검색"""
    try:
        service = get_database_service()
        terms = service.search_terms(keyword)
        
        return {
            "keyword": keyword,
            "terms": terms,
            "count": len(terms)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === FAQ ===

@router.get("/faq")
async def get_faq(
    category: Optional[str] = Query(None, description="FAQ 카테고리"),
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """FAQ 조회"""
    try:
        service = get_database_service()
        faqs = service.get_faq(category, limit)
        
        return {
            "category": category,
            "faqs": faqs,
            "count": len(faqs)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/consultation-cases")
async def get_consultation_cases(
    category: Optional[str] = Query(None, description="상담 카테고리")
) -> Dict[str, Any]:
    """상담 사례 조회"""
    try:
        service = get_database_service()
        cases = service.get_consultation_cases(category)
        
        return {
            "category": category,
            "cases": cases,
            "count": len(cases)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 청약 정책 ===

@router.get("/subscription")
async def get_subscription_policies() -> Dict[str, Any]:
    """청약 정책 조회"""
    try:
        service = get_database_service()
        policies = service.get_subscription_policies()
        
        return {
            "policies": policies,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/subscription/special-supply/{supply_type}")
async def get_special_supply(supply_type: str) -> Dict[str, Any]:
    """특별공급 정보 조회"""
    try:
        service = get_database_service()
        info = service.get_special_supply_info(supply_type)
        
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Special supply type '{supply_type}' not found"
            )
        
        return {
            "supply_type": supply_type,
            "info": info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 지역 정보 ===

@router.get("/area-info/{area_name}")
async def get_area_information(area_name: str) -> Dict[str, Any]:
    """특정 지역 정보 조회"""
    try:
        service = get_database_service()
        area_info = service.get_area_info(area_name)
        
        if not area_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Area '{area_name}' not found"
            )
        
        return {
            "area_name": area_name,
            "info": area_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/area-info/{area_name}/schools")
async def get_area_schools(area_name: str) -> Dict[str, Any]:
    """지역별 학교 정보 조회"""
    try:
        service = get_database_service()
        schools = service.get_area_schools(area_name)
        
        if not schools:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"School information for '{area_name}' not found"
            )
        
        return {
            "area_name": area_name,
            "schools": schools
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 교통 정보 ===

@router.get("/transit/{station_name}")
async def get_transit_info(station_name: str) -> Dict[str, Any]:
    """역세권 정보 조회"""
    try:
        service = get_database_service()
        transit_info = service.get_transit_zone(station_name)
        
        if not transit_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transit information for '{station_name}' not found"
            )
        
        return {
            "station_name": station_name,
            "info": transit_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/transit/plans/future")
async def get_future_transit_plans() -> Dict[str, Any]:
    """미래 교통 계획 조회"""
    try:
        service = get_database_service()
        plans = service.get_future_transit_plans()
        
        return {
            "plans": plans,
            "count": len(plans)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 실거래가 ===

@router.get("/transactions")
async def get_transactions(
    location: Optional[str] = Query(None, description="지역명"),
    property_type: Optional[str] = Query(None, description="부동산 유형"),
    transaction_type: Optional[str] = Query(None, description="거래 유형"),
    limit: int = Query(10, ge=1, le=100)
) -> Dict[str, Any]:
    """실거래가 조회"""
    try:
        service = get_database_service()
        transactions = service.get_recent_transactions(
            location=location,
            property_type=property_type,
            transaction_type=transaction_type,
            limit=limit
        )
        
        return {
            "filters": {
                "location": location,
                "property_type": property_type,
                "transaction_type": transaction_type
            },
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/market-trends/{region}")
async def get_market_trends(
    region: str = "seoul"
) -> Dict[str, Any]:
    """시장 동향 조회"""
    try:
        service = get_database_service()
        trends = service.get_market_trends(region)
        
        if not trends:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market trends for '{region}' not found"
            )
        
        return {
            "region": region,
            "trends": trends
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 대출 정보 ===

@router.get("/loans")
async def get_loans(
    bank: Optional[str] = Query(None, description="은행명"),
    loan_type: Optional[str] = Query(None, description="대출 유형")
) -> Dict[str, Any]:
    """대출 상품 조회"""
    try:
        service = get_database_service()
        loans = service.get_loan_products(bank, loan_type)
        
        return {
            "filters": {
                "bank": bank,
                "loan_type": loan_type
            },
            "loans": loans,
            "count": len(loans)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/loans/government")
async def get_government_loans() -> Dict[str, Any]:
    """정부 지원 대출 조회"""
    try:
        service = get_database_service()
        loans = service.get_government_loans()
        
        return {
            "loans": loans,
            "count": len(loans)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/loans/interest-rates")
async def get_interest_rates() -> Dict[str, Any]:
    """현재 금리 정보 조회"""
    try:
        service = get_database_service()
        rates = service.get_interest_rates()
        
        return {
            "rates": rates,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 혜택 정보 ===

@router.get("/benefits")
async def get_benefits(
    category: Optional[str] = Query(None, description="혜택 카테고리"),
    target: Optional[str] = Query(None, description="대상")
) -> Dict[str, Any]:
    """주거 지원 혜택 조회"""
    try:
        service = get_database_service()
        benefits = service.get_benefits(category, target)
        
        return {
            "filters": {
                "category": category,
                "target": target
            },
            "benefits": benefits,
            "count": len(benefits)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/benefits/regional/{region}")
async def get_regional_benefits(region: str) -> Dict[str, Any]:
    """지역별 혜택 조회"""
    try:
        service = get_database_service()
        benefits = service.get_regional_benefits(region)
        
        if not benefits:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Regional benefits for '{region}' not found"
            )
        
        return {
            "region": region,
            "benefits": benefits,
            "count": len(benefits)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 청약 통계 ===

@router.get("/subscription-stats")
async def get_subscription_statistics(
    location: Optional[str] = Query(None, description="지역"),
    date_from: Optional[str] = Query(None, description="시작일"),
    date_to: Optional[str] = Query(None, description="종료일")
) -> Dict[str, Any]:
    """청약 통계 조회"""
    try:
        service = get_database_service()
        stats = service.get_subscription_statistics(
            location=location,
            date_from=date_from,
            date_to=date_to
        )
        
        return {
            "filters": {
                "location": location,
                "date_from": date_from,
                "date_to": date_to
            },
            "statistics": stats,
            "count": len(stats)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/subscription-stats/winning-patterns")
async def get_winning_patterns() -> Dict[str, Any]:
    """당첨 패턴 분석 조회"""
    try:
        service = get_database_service()
        patterns = service.get_winning_patterns()
        
        return {
            "patterns": patterns,
            "count": len(patterns)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === 데이터베이스 통계 ===

@router.get("/statistics")
async def get_database_statistics() -> Dict[str, Any]:
    """데이터베이스 통계 정보"""
    try:
        service = get_database_service()
        stats = service.get_statistics()
        
        return {
            "statistics": stats,
            "status": "healthy"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )