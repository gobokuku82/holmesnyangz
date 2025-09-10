"""
Location Tools
위치 및 입지 분석 에이전트가 사용하는 도구들
"""

from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool
import logging
import random
import math

logger = logging.getLogger(__name__)


@tool
def search_nearby_facilities(
    location: str,
    facility_types: Optional[List[str]] = None,
    radius_km: float = 1.0
) -> Dict[str, Any]:
    """
    주변 편의시설 검색
    
    Args:
        location: 중심 위치
        facility_types: 시설 종류 (학교, 병원, 마트, 공원 등)
        radius_km: 검색 반경 (km)
    
    Returns:
        주변 시설 정보
    """
    logger.info(f"Searching facilities near {location} within {radius_km}km")
    
    # 기본 시설 타입
    if not facility_types:
        facility_types = ["학교", "병원", "마트", "지하철역", "버스정류장", "공원", "은행"]
    
    facilities = {}
    
    for facility_type in facility_types:
        # 실제로는 지도 API 호출 (카카오맵, 네이버맵 등)
        # 더미 데이터 생성
        num_facilities = random.randint(2, 8)
        facility_list = []
        
        for i in range(num_facilities):
            distance = random.uniform(0.1, radius_km)
            
            if facility_type == "학교":
                names = ["서울초등학교", "강남중학교", "서초고등학교", "영동초등학교", "대치중학교"]
                types = ["초등학교", "중학교", "고등학교"]
            elif facility_type == "병원":
                names = ["서울대병원", "삼성서울병원", "강남성모병원", "서울아산병원", "연세의료원"]
                types = ["종합병원", "내과", "소아과", "정형외과"]
            elif facility_type == "마트":
                names = ["이마트", "홈플러스", "롯데마트", "코스트코", "하나로마트"]
                types = ["대형마트", "슈퍼마켓", "편의점"]
            elif facility_type == "지하철역":
                names = ["강남역", "삼성역", "선릉역", "역삼역", "논현역"]
                types = ["2호선", "3호선", "분당선", "신분당선"]
            elif facility_type == "공원":
                names = ["한강공원", "양재천", "선정릉공원", "도곡공원", "대모산"]
                types = ["도시공원", "근린공원", "하천", "산"]
            else:
                names = [f"{facility_type} {i+1}"]
                types = [facility_type]
            
            facility_list.append({
                "name": random.choice(names),
                "type": random.choice(types),
                "distance_km": round(distance, 2),
                "walking_time": int(distance * 15),  # 도보 시간 (분)
                "address": f"{location} 인근"
            })
        
        # 거리순 정렬
        facility_list.sort(key=lambda x: x["distance_km"])
        facilities[facility_type] = facility_list
    
    # 편의성 점수 계산
    convenience_score = calculate_convenience_score(facilities)
    
    return {
        "status": "success",
        "location": location,
        "search_radius_km": radius_km,
        "facilities": facilities,
        "summary": {
            "total_facilities": sum(len(f) for f in facilities.values()),
            "facility_types": len(facilities),
            "convenience_score": convenience_score,
            "grade": get_location_grade(convenience_score)
        },
        "highlights": generate_location_highlights(facilities)
    }


@tool
def calculate_distance(
    from_location: str,
    to_location: str,
    transport_mode: str = "driving"
) -> Dict[str, Any]:
    """
    두 위치 간 거리 및 이동 시간 계산
    
    Args:
        from_location: 출발지
        to_location: 도착지
        transport_mode: 이동 수단 (driving, transit, walking)
    
    Returns:
        거리 및 이동 시간 정보
    """
    logger.info(f"Calculating distance from {from_location} to {to_location}")
    
    # 실제로는 지도 API 호출
    # 더미 데이터 생성
    base_distance = random.uniform(1, 30)  # km
    
    if transport_mode == "walking":
        speed = 4  # km/h
        time_minutes = int(base_distance / speed * 60)
        cost = 0
    elif transport_mode == "transit":
        speed = 25  # km/h (평균)
        time_minutes = int(base_distance / speed * 60) + random.randint(5, 15)  # 대기시간
        cost = 1250 if base_distance < 10 else 1450  # 교통카드 요금
    else:  # driving
        speed = 30  # km/h (시내 평균)
        time_minutes = int(base_distance / speed * 60)
        cost = int(base_distance * 150)  # 유류비 추정
    
    # 교통 혼잡도
    congestion = random.choice(["원활", "보통", "혼잡"])
    if congestion == "혼잡":
        time_minutes = int(time_minutes * 1.3)
    elif congestion == "보통":
        time_minutes = int(time_minutes * 1.1)
    
    return {
        "status": "success",
        "route": {
            "from": from_location,
            "to": to_location,
            "distance_km": round(base_distance, 2),
            "transport_mode": transport_mode
        },
        "time": {
            "minutes": time_minutes,
            "formatted": f"{time_minutes // 60}시간 {time_minutes % 60}분" if time_minutes >= 60 else f"{time_minutes}분"
        },
        "cost": {
            "amount": cost,
            "formatted": f"{cost:,}원" if cost > 0 else "무료"
        },
        "traffic": {
            "congestion_level": congestion,
            "best_time": "오전 10시-11시" if transport_mode == "driving" else "해당없음"
        },
        "alternatives": generate_route_alternatives(from_location, to_location, base_distance)
    }


@tool
def evaluate_accessibility(
    location: str,
    key_destinations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    교통 접근성 종합 평가
    
    Args:
        location: 평가할 위치
        key_destinations: 주요 목적지 리스트
    
    Returns:
        접근성 평가 결과
    """
    logger.info(f"Evaluating accessibility for {location}")
    
    # 기본 주요 목적지
    if not key_destinations:
        key_destinations = ["강남역", "서울역", "김포공항", "강남업무지구"]
    
    # 대중교통 접근성
    subway_stations = random.randint(1, 4)
    bus_stops = random.randint(3, 10)
    bus_routes = random.randint(5, 20)
    
    # 도로 접근성
    major_roads = random.randint(1, 3)
    highway_access = random.uniform(1, 10)  # km
    
    # 주요 목적지까지 시간
    destination_times = {}
    for dest in key_destinations:
        destination_times[dest] = {
            "transit": random.randint(15, 60),
            "driving": random.randint(10, 50)
        }
    
    # 접근성 점수 계산 (100점 만점)
    transit_score = min(100, (subway_stations * 20 + bus_stops * 3 + bus_routes * 2))
    road_score = min(100, (100 - highway_access * 5 + major_roads * 10))
    overall_score = (transit_score + road_score) / 2
    
    return {
        "status": "success",
        "location": location,
        "public_transport": {
            "subway_stations": {
                "count": subway_stations,
                "nearest_distance": f"{random.uniform(0.2, 1.5):.1f}km",
                "lines": generate_subway_lines(subway_stations)
            },
            "bus": {
                "stops": bus_stops,
                "routes": bus_routes,
                "nearest_stop": f"{random.randint(50, 500)}m"
            },
            "score": transit_score
        },
        "road_access": {
            "major_roads": major_roads,
            "highway_access": f"{highway_access:.1f}km",
            "parking": random.choice(["충분", "보통", "부족"]),
            "score": road_score
        },
        "key_destinations": destination_times,
        "overall": {
            "score": round(overall_score, 1),
            "grade": get_accessibility_grade(overall_score),
            "summary": generate_accessibility_summary(overall_score, transit_score, road_score)
        }
    }


@tool
def analyze_school_district(
    location: str,
    school_level: Optional[str] = None
) -> Dict[str, Any]:
    """
    학군 정보 분석
    
    Args:
        location: 위치
        school_level: 학교 레벨 (초등, 중등, 고등)
    
    Returns:
        학군 분석 정보
    """
    logger.info(f"Analyzing school district for {location}")
    
    # 학군 정보 생성
    schools = {
        "elementary": [],
        "middle": [],
        "high": []
    }
    
    # 초등학교
    for i in range(random.randint(2, 4)):
        schools["elementary"].append({
            "name": f"{location} 제{i+1}초등학교",
            "distance_km": round(random.uniform(0.3, 1.5), 2),
            "students": random.randint(300, 800),
            "teachers": random.randint(20, 50),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "special_programs": random.sample(
                ["영재학급", "방과후학교", "돌봄교실", "오케스트라", "코딩교육"],
                k=random.randint(2, 4)
            )
        })
    
    # 중학교
    for i in range(random.randint(1, 3)):
        schools["middle"].append({
            "name": f"{location} 제{i+1}중학교",
            "distance_km": round(random.uniform(0.5, 2.0), 2),
            "students": random.randint(400, 1000),
            "teachers": random.randint(30, 70),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "academic_performance": random.choice(["상위 10%", "상위 20%", "평균", "평균 이상"])
        })
    
    # 고등학교
    for i in range(random.randint(1, 3)):
        school_types = ["일반고", "자사고", "특목고", "특성화고"]
        schools["high"].append({
            "name": f"{location} {'제' + str(i+1) if i > 0 else ''}고등학교",
            "type": random.choice(school_types),
            "distance_km": round(random.uniform(1.0, 3.0), 2),
            "students": random.randint(600, 1500),
            "university_admission_rate": random.randint(60, 95),
            "rating": round(random.uniform(3.5, 5.0), 1)
        })
    
    # 학군 평가
    avg_rating = sum(
        s["rating"] for level in schools.values() for s in level
    ) / sum(len(level) for level in schools.values())
    
    # 학원가 정보
    academy_density = random.choice(["매우 높음", "높음", "보통", "낮음"])
    
    return {
        "status": "success",
        "location": location,
        "schools": schools if not school_level else {school_level: schools.get(school_level, [])},
        "summary": {
            "total_schools": sum(len(level) for level in schools.values()),
            "average_rating": round(avg_rating, 1),
            "school_district_grade": get_school_grade(avg_rating),
            "academy_density": academy_density
        },
        "education_environment": {
            "libraries": random.randint(1, 5),
            "study_cafes": random.randint(5, 20),
            "bookstores": random.randint(1, 10),
            "cultural_centers": random.randint(1, 3)
        },
        "insights": generate_school_insights(avg_rating, academy_density)
    }


@tool
def find_transportation(
    location: str,
    destination: str,
    departure_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    최적 교통 경로 찾기
    
    Args:
        location: 출발지
        destination: 도착지
        departure_time: 출발 시간
    
    Returns:
        교통 경로 옵션
    """
    logger.info(f"Finding transportation from {location} to {destination}")
    
    routes = []
    
    # 대중교통 경로
    routes.append({
        "mode": "대중교통",
        "duration_minutes": random.randint(20, 60),
        "cost": 1450,
        "transfers": random.randint(0, 2),
        "steps": [
            f"{location} → 도보 {random.randint(3, 10)}분",
            f"지하철 {random.choice(['2', '3', '7', '9'])}호선 {random.randint(5, 15)}정거장",
            f"환승 → {random.choice(['버스', '지하철'])}",
            f"도보 {random.randint(3, 10)}분 → {destination}"
        ],
        "convenience": random.choice(["매우 편리", "편리", "보통"])
    })
    
    # 자가용 경로
    routes.append({
        "mode": "자가용",
        "duration_minutes": random.randint(15, 45),
        "cost": random.randint(2000, 8000),  # 유류비 + 통행료
        "distance_km": random.uniform(5, 25),
        "steps": [
            f"{location} 출발",
            f"주요 도로 경유",
            f"{destination} 도착"
        ],
        "parking": random.choice(["주차 가능", "주차 어려움"]),
        "traffic_condition": random.choice(["원활", "보통", "혼잡"])
    })
    
    # 택시 경로
    taxi_distance = random.uniform(5, 20)
    taxi_cost = 3800 + int(taxi_distance * 1000)  # 기본요금 + 거리요금
    
    routes.append({
        "mode": "택시",
        "duration_minutes": random.randint(10, 35),
        "cost": taxi_cost,
        "distance_km": taxi_distance,
        "availability": random.choice(["즉시 가능", "5분 대기", "10분 대기"])
    })
    
    # 최적 경로 선택
    best_route = min(routes, key=lambda x: x["duration_minutes"])
    
    return {
        "status": "success",
        "from": location,
        "to": destination,
        "departure_time": departure_time or "현재",
        "routes": routes,
        "recommendation": {
            "best_route": best_route,
            "reason": f"가장 빠른 이동 시간 ({best_route['duration_minutes']}분)"
        },
        "real_time_info": {
            "current_traffic": random.choice(["원활", "보통", "혼잡"]),
            "weather": random.choice(["맑음", "흐림", "비"]),
            "special_events": random.choice([None, "주변 행사로 인한 교통 통제"])
        }
    }


# 헬퍼 함수들
def calculate_convenience_score(facilities: Dict) -> float:
    """편의성 점수 계산"""
    score = 0
    weights = {
        "지하철역": 25,
        "버스정류장": 15,
        "학교": 20,
        "병원": 15,
        "마트": 15,
        "공원": 10
    }
    
    for facility_type, facility_list in facilities.items():
        if facility_type in weights:
            # 가까운 시설일수록 높은 점수
            for facility in facility_list[:3]:  # 상위 3개만
                if facility["distance_km"] < 0.5:
                    score += weights[facility_type]
                elif facility["distance_km"] < 1.0:
                    score += weights[facility_type] * 0.7
                else:
                    score += weights[facility_type] * 0.4
    
    return min(100, score)


def get_location_grade(score: float) -> str:
    """위치 등급 반환"""
    if score >= 90:
        return "S"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


def get_accessibility_grade(score: float) -> str:
    """접근성 등급 반환"""
    if score >= 90:
        return "최우수"
    elif score >= 75:
        return "우수"
    elif score >= 60:
        return "양호"
    elif score >= 45:
        return "보통"
    else:
        return "미흡"


def get_school_grade(rating: float) -> str:
    """학군 등급 반환"""
    if rating >= 4.5:
        return "최우수"
    elif rating >= 4.0:
        return "우수"
    elif rating >= 3.5:
        return "양호"
    else:
        return "보통"


def generate_location_highlights(facilities: Dict) -> List[str]:
    """위치 하이라이트 생성"""
    highlights = []
    
    if "지하철역" in facilities and facilities["지하철역"]:
        nearest = facilities["지하철역"][0]
        highlights.append(f"지하철역 도보 {nearest['walking_time']}분")
    
    if "학교" in facilities and len(facilities["학교"]) >= 3:
        highlights.append("우수한 교육 환경")
    
    if "공원" in facilities and facilities["공원"]:
        highlights.append("녹지 공간 인접")
    
    return highlights


def generate_subway_lines(station_count: int) -> List[str]:
    """지하철 노선 생성"""
    all_lines = ["1호선", "2호선", "3호선", "4호선", "5호선", "6호선", "7호선", "8호선", "9호선", "분당선", "신분당선"]
    return random.sample(all_lines, min(station_count, len(all_lines)))


def generate_route_alternatives(from_loc: str, to_loc: str, distance: float) -> List[Dict]:
    """대체 경로 생성"""
    alternatives = []
    
    # 빠른 경로
    alternatives.append({
        "type": "최단시간",
        "time_minutes": int(distance * 2),
        "note": "유료도로 이용"
    })
    
    # 최단거리
    alternatives.append({
        "type": "최단거리",
        "time_minutes": int(distance * 2.5),
        "note": "일반도로 이용"
    })
    
    return alternatives


def generate_accessibility_summary(overall: float, transit: float, road: float) -> str:
    """접근성 요약 생성"""
    if overall >= 80:
        return "교통 접근성이 매우 우수한 지역입니다."
    elif overall >= 60:
        if transit > road:
            return "대중교통이 잘 발달된 지역입니다."
        else:
            return "자가용 이용이 편리한 지역입니다."
    else:
        return "교통 접근성 개선이 필요한 지역입니다."


def generate_school_insights(rating: float, academy_density: str) -> List[str]:
    """학군 인사이트 생성"""
    insights = []
    
    if rating >= 4.5:
        insights.append("최상위권 학군으로 교육 환경이 매우 우수합니다.")
    elif rating >= 4.0:
        insights.append("우수한 학군으로 안정적인 교육 환경입니다.")
    
    if academy_density in ["매우 높음", "높음"]:
        insights.append("학원가가 발달하여 사교육 접근성이 좋습니다.")
    
    insights.append("학령기 자녀가 있는 가정에 적합한 지역입니다.")
    
    return insights


# 도구 목록
LOCATION_TOOLS = [
    search_nearby_facilities,
    calculate_distance,
    evaluate_accessibility,
    analyze_school_district,
    find_transportation
]