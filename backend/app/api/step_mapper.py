"""
StepMapper: ExecutionStepState → ProcessFlow Step 변환
백엔드 TODO를 프론트엔드 시각화 단계로 매핑
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessFlowStep:
    """프론트엔드 ProcessFlow 단계"""
    step: str  # "planning", "searching", "analyzing", "generating"
    label: str  # "계획", "검색", "분석", "생성"
    agent: str  # 담당 agent 이름
    status: str  # "pending", "in_progress", "completed", "failed"
    progress: int  # 0-100


class StepMapper:
    """ExecutionStepState → ProcessFlow 매핑"""

    # Agent 이름 → ProcessFlow Step 매핑
    AGENT_TO_STEP = {
        # Planning agents
        "planning_agent": "planning",
        "intent_analyzer": "planning",

        # Search agents (SearchTeam)
        "search_agent": "searching",
        "search_team": "searching",  # 팀 이름도 지원
        "legal_search": "searching",
        "market_search": "searching",
        "real_estate_search": "searching",
        "loan_search": "searching",
        "regulation_search": "searching",

        # Analysis agents (AnalysisTeam)
        "analysis_agent": "analyzing",
        "analysis_team": "analyzing",  # 팀 이름도 지원
        "market_analysis": "analyzing",
        "risk_analysis": "analyzing",
        "contract_analyzer": "analyzing",
        "verification_agent": "analyzing",

        # Document agents (DocumentTeam) - 분석으로 매핑
        "document_agent": "analyzing",
        "document_team": "analyzing",  # 팀 이름도 지원
        "contract_reviewer": "analyzing",
        "document_generator": "generating",

        # Response generation
        "response_generator": "generating",
        "answer_synthesizer": "generating",
        "final_response": "generating"
    }

    # Team 이름 → ProcessFlow Step 매핑 (fallback)
    TEAM_TO_STEP = {
        "search": "searching",
        "search_team": "searching",
        "analysis": "analyzing",
        "analysis_team": "analyzing",
        "document": "analyzing",
        "document_team": "analyzing"
    }

    STEP_LABELS = {
        "planning": "계획",
        "searching": "검색",
        "analyzing": "분석",
        "generating": "생성",
        "processing": "처리 중"  # fallback
    }

    @classmethod
    def map_execution_steps(
        cls,
        execution_steps: List[Dict[str, Any]]
    ) -> List[ProcessFlowStep]:
        """
        ExecutionStepState[] → ProcessFlowStep[] 변환

        Args:
            execution_steps: PlanningState의 execution_steps

        Returns:
            ProcessFlow용 단계 리스트 (중복 제거, 순서 정렬)
        """
        flow_steps_map = {}  # step → ProcessFlowStep

        for exec_step in execution_steps:
            agent_name = exec_step.get("agent_name", "")
            team_name = exec_step.get("team", "")

            # 1. Agent 이름으로 매핑
            process_step = cls.AGENT_TO_STEP.get(agent_name)

            # 2. Fallback: Team 이름으로 매핑
            if not process_step:
                process_step = cls.TEAM_TO_STEP.get(team_name)

            # 3. Fallback: "processing"
            if not process_step:
                process_step = "processing"
                logger.warning(
                    f"No mapping found for agent='{agent_name}', team='{team_name}'. "
                    f"Using 'processing' as fallback."
                )

            # 중복 제거: 같은 step은 하나만 유지 (가장 진행도가 높은 것)
            if process_step in flow_steps_map:
                existing_step = flow_steps_map[process_step]
                # 현재 step이 더 진행되었으면 업데이트
                if cls._is_more_advanced(
                    exec_step.get("status", "pending"),
                    existing_step.status
                ):
                    flow_steps_map[process_step] = cls._create_flow_step(
                        process_step, agent_name, exec_step
                    )
            else:
                flow_steps_map[process_step] = cls._create_flow_step(
                    process_step, agent_name, exec_step
                )

        # 단계 순서 정렬
        step_order = ["planning", "searching", "analyzing", "generating", "processing"]
        sorted_steps = []
        for step_name in step_order:
            if step_name in flow_steps_map:
                sorted_steps.append(flow_steps_map[step_name])

        logger.info(f"Mapped {len(execution_steps)} execution steps to {len(sorted_steps)} process flow steps")
        return sorted_steps

    @classmethod
    def _create_flow_step(
        cls,
        process_step: str,
        agent_name: str,
        exec_step: Dict[str, Any]
    ) -> ProcessFlowStep:
        """ProcessFlowStep 생성"""
        return ProcessFlowStep(
            step=process_step,
            label=cls.STEP_LABELS.get(process_step, process_step),
            agent=agent_name,
            status=exec_step.get("status", "pending"),
            progress=exec_step.get("progress_percentage", 0)
        )

    @staticmethod
    def _is_more_advanced(status1: str, status2: str) -> bool:
        """status1이 status2보다 더 진행된 상태인지 확인"""
        priority = {
            "pending": 0,
            "in_progress": 1,
            "completed": 2,
            "failed": 2,  # failed도 진행된 것으로 간주
            "skipped": 2,
            "cancelled": 2
        }
        return priority.get(status1, 0) > priority.get(status2, 0)

    @classmethod
    def get_current_step(
        cls,
        execution_steps: List[Dict[str, Any]]
    ) -> str:
        """
        현재 실행 중인 단계 반환

        Returns:
            "planning", "searching", "analyzing", "generating" 중 하나
        """
        flow_steps = cls.map_execution_steps(execution_steps)

        # in_progress 상태인 step 찾기
        for step in flow_steps:
            if step.status == "in_progress":
                return step.step

        # in_progress가 없으면 마지막 completed step 반환
        for step in reversed(flow_steps):
            if step.status == "completed":
                return step.step

        # 아무것도 없으면 첫 번째 step
        return flow_steps[0].step if flow_steps else "planning"
