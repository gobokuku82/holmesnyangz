"""
State Converters
Convert service_agent states to API responses
"""

import logging
from typing import Dict, Any, Optional, List

from app.service_agent.foundation.separated_states import MainSupervisorState
from app.api.schemas import ChatResponse

logger = logging.getLogger(__name__)


def state_to_chat_response(
    state: MainSupervisorState,
    execution_time_ms: int
) -> ChatResponse:
    """
    MainSupervisorState → ChatResponse 변환

    상세 정보 모두 포함 (Option B - 디버깅/개발용)
    추후 프로덕션 배포 시 요약 버전으로 변경 예정

    Args:
        state: Supervisor 실행 결과 state
        execution_time_ms: 총 실행 시간 (밀리초)

    Returns:
        ChatResponse: API 응답 객체
    """
    try:
        # 기본 정보 추출
        session_id = state.get("session_id", "")
        request_id = state.get("request_id", "")
        status = state.get("status", "completed")

        # 최종 응답
        final_response = state.get("final_response", {})
        if not final_response:
            # final_response가 없는 경우 기본값
            final_response = {
                "type": "error",
                "content": "응답을 생성할 수 없습니다.",
                "data": {}
            }

        # Planning 정보 추출
        planning_state = state.get("planning_state")
        planning_info = None
        if planning_state:
            planning_info = {
                "execution_steps": planning_state.get("execution_steps", []),
                "execution_strategy": planning_state.get("execution_strategy"),
                "estimated_total_time": planning_state.get("estimated_total_time"),
                "plan_validated": planning_state.get("plan_validated"),
                "intent": planning_state.get("analyzed_intent", {}).get("intent_type")
                    if planning_state.get("analyzed_intent") else None,
                "confidence": planning_state.get("intent_confidence")
            }

        # Team Results 추출
        team_results = state.get("team_results", {})

        # Search Results 추출
        search_results = None
        search_team_state = state.get("search_team_state")
        if search_team_state:
            aggregated = search_team_state.get("aggregated_results", {})
            if aggregated:
                search_results = {
                    "legal_results": search_team_state.get("legal_results", []),
                    "real_estate_results": search_team_state.get("real_estate_results", []),
                    "loan_results": search_team_state.get("loan_results", []),
                    "total_results": search_team_state.get("total_results", 0),
                    "sources_used": search_team_state.get("sources_used", [])
                }

        # Analysis Metrics 추출
        analysis_metrics = None
        analysis_team_state = state.get("analysis_team_state")
        if analysis_team_state:
            analysis_metrics = {
                "metrics": analysis_team_state.get("metrics", {}),
                "insights": analysis_team_state.get("insights", []),
                "recommendations": analysis_team_state.get("recommendations", []),
                "confidence_score": analysis_team_state.get("confidence_score", 0.0)
            }

        # 실행 단계 추출
        execution_phases = []
        current_phase = state.get("current_phase")
        if current_phase:
            execution_phases.append(current_phase)

        # 에러 정보
        error = None
        error_details = None
        if status == "error":
            error = state.get("error") or "알 수 없는 오류가 발생했습니다."
            error_log = state.get("error_log", [])
            if error_log:
                error_details = {
                    "error_log": error_log,
                    "failed_teams": state.get("failed_teams", [])
                }

        # ProcessFlow 제거 - execution_steps를 직접 사용
        process_flow_data = None

        # ChatResponse 생성
        response = ChatResponse(
            # 기본
            session_id=session_id,
            request_id=request_id,
            status=status,

            # 최종 응답
            response=final_response,

            # 상세 정보
            planning_info=planning_info,
            team_results=team_results,
            search_results=search_results,
            analysis_metrics=analysis_metrics,

            # ProcessFlow (NEW)
            process_flow=process_flow_data,

            # 메타데이터
            execution_time_ms=execution_time_ms,
            teams_executed=state.get("completed_teams", []),
            execution_phases=execution_phases,

            # Checkpoint (TODO: 실제 checkpoint_id 가져오기)
            checkpoint_id=None,

            # 에러
            error=error,
            error_details=error_details
        )

        logger.debug(f"Converted state to ChatResponse for session {session_id}")
        return response

    except Exception as e:
        logger.error(f"Error converting state to ChatResponse: {e}", exc_info=True)

        # 변환 실패 시 기본 응답
        return ChatResponse(
            session_id=state.get("session_id", "unknown"),
            request_id=state.get("request_id", "unknown"),
            status="error",
            response={
                "type": "error",
                "content": "응답 변환 중 오류가 발생했습니다.",
                "data": {}
            },
            execution_time_ms=execution_time_ms,
            teams_executed=[],
            execution_phases=[],
            error=str(e),
            error_details={"conversion_error": True}
        )


def extract_summary_response(chat_response: ChatResponse) -> Dict[str, Any]:
    """
    ChatResponse에서 요약 정보만 추출 (프로덕션용)

    추후 프로덕션 배포 시 사용할 함수
    상세 정보를 제거하고 필수 정보만 반환

    Args:
        chat_response: 전체 ChatResponse

    Returns:
        요약 응답 dict
    """
    return {
        "session_id": chat_response.session_id,
        "request_id": chat_response.request_id,
        "status": chat_response.status,
        "response": chat_response.response,
        "execution_time_ms": chat_response.execution_time_ms,
        "teams_executed": chat_response.teams_executed,
        "error": chat_response.error
    }
