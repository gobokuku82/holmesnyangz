"""
Location Agent
위치 및 입지 분석 전문 에이전트
"""

from typing import Dict, Any, Optional, List
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from backend.agents.base_agent import BaseAgent
from backend.core.state import AgentState
from backend.tools.location_tools import LOCATION_TOOLS
from backend.config import settings

logger = logging.getLogger(__name__)


class LocationAgent(BaseAgent):
    """
    입지 분석 전문 에이전트
    - 주변 편의시설 검색
    - 교통 접근성 평가
    - 학군 정보 분석
    - 거리 계산
    - 최적 경로 찾기
    """
    
    def __init__(self):
        super().__init__(agent_id="location_agent", name="입지 분석 전문가")
        
        # LLM 초기화
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model=settings.default_model,
                temperature=0.5,
                api_key=settings.openai_api_key
            )
        elif settings.anthropic_api_key:
            self.llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.5,
                api_key=settings.anthropic_api_key
            )
        else:
            logger.warning("No LLM API key found")
            self.llm = None
        
        # 에이전트 초기화
        self.agent_executor = self._create_agent_executor() if self.llm else None
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        도구를 사용하는 에이전트 실행기 생성
        """
        # 프롬프트 템플릿
        system_prompt = """당신은 부동산 입지 분석 전문가입니다.
        
주요 역할:
1. 주변 편의시설 정보 제공
2. 교통 접근성 분석
3. 학군 정보 및 교육 환경 평가
4. 거리 및 이동 시간 계산
5. 생활 인프라 종합 평가

사용 가능한 도구:
- search_nearby_facilities: 주변 시설 검색
- calculate_distance: 거리 계산
- evaluate_accessibility: 접근성 평가
- analyze_school_district: 학군 분석
- find_transportation: 교통 경로 찾기

응답 시 주의사항:
- 구체적인 거리와 시간 정보 제공
- 도보, 대중교통, 자가용 기준 구분
- 생활 편의성 종합 평가
- 가족 구성에 따른 맞춤 조언
- 장단점 균형있게 제시"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 도구 사용 에이전트 생성
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=LOCATION_TOOLS,
            prompt=prompt
        )
        
        # 에이전트 실행기 생성
        return AgentExecutor(
            agent=agent,
            tools=LOCATION_TOOLS,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """
        위치 관련 질의 처리
        
        Args:
            state: Current state
            
        Returns:
            Updated state with location information
        """
        query = state.get("query", "")
        entities = state.get("entities", {})
        parameters = state.get("agent_parameters", {}).get("location_params", {})
        
        logger.info(f"Processing location query: {query}")
        
        # 위치 정보 추출
        location = self._extract_location(entities, parameters)
        facility_types = self._extract_facility_types(query, parameters)
        
        # 도구를 직접 사용하거나 LLM 에이전트 사용
        if self.agent_executor and query:
            result = self._process_with_llm(query, location, facility_types)
        else:
            result = self._process_with_tools(location, facility_types, entities)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(result)
        
        return {
            "location_result": result,
            "confidence": confidence,
            "current_step": "location_analysis_complete"
        }
    
    def _extract_location(self, entities: Dict, parameters: Dict) -> Optional[str]:
        """
        위치 정보 추출
        """
        # 엔티티에서 위치 추출
        if entities.get("location"):
            locations = entities["location"]
            if isinstance(locations, list) and locations:
                return locations[0]
            elif isinstance(locations, str):
                return locations
        
        # 파라미터에서 위치 추출
        if parameters.get("target_location"):
            locations = parameters["target_location"]
            if isinstance(locations, list) and locations:
                return locations[0]
            elif isinstance(locations, str):
                return locations
        
        return None
    
    def _extract_facility_types(self, query: str, parameters: Dict) -> List[str]:
        """
        시설 타입 추출
        """
        facility_types = []
        query_lower = query.lower()
        
        # 키워드 매핑
        keyword_map = {
            "학교": ["학교", "초등", "중학", "고등", "학군"],
            "병원": ["병원", "의료", "의원", "응급"],
            "마트": ["마트", "슈퍼", "시장", "쇼핑"],
            "지하철역": ["지하철", "역", "전철", "메트로"],
            "버스정류장": ["버스", "정류장"],
            "공원": ["공원", "녹지", "산책", "운동"],
            "은행": ["은행", "금융"],
            "카페": ["카페", "커피", "스타벅스"],
            "편의점": ["편의점", "GS25", "CU", "세븐일레븐"]
        }
        
        for facility_type, keywords in keyword_map.items():
            if any(keyword in query_lower for keyword in keywords):
                facility_types.append(facility_type)
        
        # 파라미터에서 추가
        if parameters.get("facility_types"):
            facility_types.extend(parameters["facility_types"])
        
        # 기본값
        if not facility_types:
            facility_types = ["학교", "병원", "마트", "지하철역", "버스정류장"]
        
        return list(set(facility_types))  # 중복 제거
    
    def _process_with_llm(self, query: str, location: str, facility_types: List[str]) -> Dict[str, Any]:
        """
        LLM 에이전트를 사용한 처리
        """
        try:
            # 컨텍스트 포함 쿼리 생성
            context_parts = []
            if location:
                context_parts.append(f"위치: {location}")
            if facility_types:
                context_parts.append(f"관심 시설: {', '.join(facility_types)}")
            
            enhanced_query = f"""
사용자 질의: {query}

위치 정보:
{chr(10).join(context_parts) if context_parts else '위치 정보 없음'}

위 정보를 바탕으로 입지 분석과 생활 편의성을 평가해주세요.
"""
            
            # 에이전트 실행
            response = self.agent_executor.invoke({
                "input": enhanced_query
            })
            
            # 결과 파싱
            if isinstance(response, dict):
                output = response.get("output", "")
                intermediate_steps = response.get("intermediate_steps", [])
                
                # 도구 사용 결과 수집
                tool_results = []
                for step in intermediate_steps:
                    if len(step) >= 2:
                        action = step[0]
                        observation = step[1]
                        tool_results.append({
                            "tool": action.tool if hasattr(action, 'tool') else "unknown",
                            "input": action.tool_input if hasattr(action, 'tool_input') else {},
                            "output": observation
                        })
                
                return {
                    "status": "success",
                    "response": output,
                    "tool_results": tool_results,
                    "location_context": {
                        "location": location,
                        "facility_types": facility_types
                    }
                }
            else:
                return {
                    "status": "success",
                    "response": str(response),
                    "location_context": {
                        "location": location,
                        "facility_types": facility_types
                    }
                }
                
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            # 폴백: 도구 직접 사용
            return self._process_with_tools(location, facility_types, {})
    
    def _process_with_tools(self, location: str, facility_types: List[str], entities: Dict) -> Dict[str, Any]:
        """
        도구를 직접 사용한 처리
        """
        from backend.tools.location_tools import (
            search_nearby_facilities,
            evaluate_accessibility,
            analyze_school_district
        )
        
        results = {}
        response_parts = []
        
        try:
            if not location:
                return {
                    "status": "error",
                    "message": "위치 정보가 필요합니다. 지역명을 알려주세요."
                }
            
            # 1. 주변 시설 검색
            facilities = search_nearby_facilities.invoke({
                "location": location,
                "facility_types": facility_types,
                "radius_km": 1.0
            })
            results["facilities"] = facilities
            
            if facilities.get("status") == "success":
                response_parts.append(f"### {location} 주변 시설 정보\n")
                
                summary = facilities.get("summary", {})
                response_parts.append(
                    f"- 편의성 점수: {summary.get('convenience_score', 0)}/100점 "
                    f"(등급: {summary.get('grade', 'N/A')})\n"
                    f"- 검색된 시설: {summary.get('total_facilities', 0)}개\n"
                )
                
                # 주요 시설 정보
                for facility_type, facility_list in facilities.get("facilities", {}).items():
                    if facility_list:
                        nearest = facility_list[0]
                        response_parts.append(
                            f"\n**{facility_type}**\n"
                            f"- 가장 가까운 곳: {nearest['name']} "
                            f"({nearest['distance_km']}km, 도보 {nearest['walking_time']}분)\n"
                        )
            
            # 2. 접근성 평가
            accessibility = evaluate_accessibility.invoke({
                "location": location
            })
            results["accessibility"] = accessibility
            
            if accessibility.get("status") == "success":
                response_parts.append("\n### 교통 접근성\n")
                
                public = accessibility.get("public_transport", {})
                response_parts.append(
                    f"- 지하철역: {public.get('subway_stations', {}).get('count', 0)}개 "
                    f"(최단거리: {public.get('subway_stations', {}).get('nearest_distance', 'N/A')})\n"
                    f"- 버스 노선: {public.get('bus', {}).get('routes', 0)}개\n"
                )
                
                overall = accessibility.get("overall", {})
                response_parts.append(
                    f"- 종합 점수: {overall.get('score', 0)}/100점 "
                    f"({overall.get('grade', 'N/A')})\n"
                    f"- {overall.get('summary', '')}\n"
                )
            
            # 3. 학군 정보 (학교 관련 키워드가 있는 경우)
            if "학교" in facility_types or "학군" in ' '.join(facility_types):
                school_info = analyze_school_district.invoke({
                    "location": location
                })
                results["school_district"] = school_info
                
                if school_info.get("status") == "success":
                    response_parts.append("\n### 학군 정보\n")
                    
                    summary = school_info.get("summary", {})
                    response_parts.append(
                        f"- 학군 등급: {summary.get('school_district_grade', 'N/A')}\n"
                        f"- 평균 평점: {summary.get('average_rating', 0)}/5.0\n"
                        f"- 학원가 밀집도: {summary.get('academy_density', 'N/A')}\n"
                    )
                    
                    # 인사이트 추가
                    insights = school_info.get("insights", [])
                    if insights:
                        for insight in insights[:2]:
                            response_parts.append(f"- 💡 {insight}\n")
            
            # 하이라이트 추가
            if facilities.get("highlights"):
                response_parts.append("\n### 주요 특징\n")
                for highlight in facilities["highlights"]:
                    response_parts.append(f"✓ {highlight}\n")
            
            return {
                "status": "success",
                "response": "\n".join(response_parts),
                "detailed_results": results,
                "location_context": {
                    "location": location,
                    "facility_types": facility_types
                }
            }
            
        except Exception as e:
            logger.error(f"Tool processing error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": "입지 정보를 분석하는 중 오류가 발생했습니다."
            }
    
    def _calculate_confidence(self, result: Dict) -> float:
        """
        결과의 신뢰도 계산
        """
        if result.get("status") != "success":
            return 0.0
        
        confidence = 0.5  # 기본 신뢰도
        
        # 상세 결과가 있으면 신뢰도 증가
        if result.get("detailed_results"):
            results = result["detailed_results"]
            if results.get("facilities"):
                confidence += 0.15
            if results.get("accessibility"):
                confidence += 0.15
            if results.get("school_district"):
                confidence += 0.1
        
        # 도구 사용 결과가 있으면 신뢰도 증가
        if result.get("tool_results"):
            confidence += 0.05 * min(len(result["tool_results"]), 3)
        
        # 위치 정보가 명확하면 신뢰도 증가
        context = result.get("location_context", {})
        if context.get("location"):
            confidence += 0.1
        
        return min(confidence, 0.95)