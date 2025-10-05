"""
Analysis Executor - 데이터 분석 실행 Agent
수집된 데이터를 분석하여 인사이트와 추천사항을 생성
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service_agent.foundation.separated_states import (
    AnalysisTeamState,
    AnalysisInput,
    AnalysisMetrics,
    AnalysisInsight,
    AnalysisReport,
    SharedState
)
from app.service_agent.llm_manager import LLMService

logger = logging.getLogger(__name__)


class AnalysisExecutor:
    """
    분석 실행 Agent
    데이터 분석 및 보고서 생성 작업을 실행
    """

    def __init__(self, llm_context=None):
        """초기화"""
        self.llm_context = llm_context
        self.llm_service = LLMService(llm_context=llm_context) if llm_context else None
        self.team_name = "analysis"

        # 분석 메서드 매핑
        self.analysis_methods = {
            "comprehensive": self._comprehensive_analysis,
            "market": self._market_analysis,
            "risk": self._risk_analysis,
            "comparison": self._comparison_analysis
        }

        # 서브그래프 구성
        self.app = None
        self._build_subgraph()

    def _build_subgraph(self):
        """서브그래프 구성"""
        workflow = StateGraph(AnalysisTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_analysis_node)
        workflow.add_node("preprocess", self.preprocess_data_node)
        workflow.add_node("analyze", self.analyze_data_node)
        workflow.add_node("generate_insights", self.generate_insights_node)
        workflow.add_node("create_report", self.create_report_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 구성
        workflow.add_edge(START, "prepare")
        workflow.add_edge("prepare", "preprocess")
        workflow.add_edge("preprocess", "analyze")
        workflow.add_edge("analyze", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("AnalysisTeam subgraph built successfully")

    async def prepare_analysis_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """분석 준비 노드"""
        logger.info("[AnalysisTeam] Preparing analysis")

        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()
        state["analysis_status"] = "preparing"
        state["analysis_progress"] = {"current": "prepare", "percent": 0.0}

        if not state.get("analysis_type"):
            state["analysis_type"] = "comprehensive"

        logger.info(f"[AnalysisTeam] Analysis type: {state['analysis_type']}")
        return state

    async def preprocess_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """데이터 전처리 노드"""
        logger.info("[AnalysisTeam] Preprocessing data")

        state["preprocessing_status"] = "in_progress"
        state["analysis_progress"] = {"current": "preprocess", "percent": 0.1}

        # 입력 데이터를 그대로 전달
        preprocessed = {}
        for input_item in state.get("input_data", []):
            preprocessed[input_item["data_source"]] = input_item.get("data", input_item.get("raw_data", {}))

        state["preprocessed_data"] = preprocessed
        state["preprocessing_status"] = "completed"
        state["analysis_progress"] = {"current": "preprocess", "percent": 0.2}

        return state

    async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        실제 데이터 분석 노드
        analysis_tools를 사용하여 실제 분석 수행
        """
        logger.info("[AnalysisTeam] Analyzing data with analysis_tools")

        state["analysis_status"] = "analyzing"
        state["analysis_progress"] = {"current": "analyze", "percent": 0.3}

        try:
            from app.service_agent.tools.analysis_tools import (
                MarketAnalyzer, TrendAnalyzer, RiskAssessor
            )

            preprocessed_data = state.get("preprocessed_data", {})
            query = state.get("shared_context", {}).get("query", "")

            results = {}

            # 1. 시장 분석
            market_analyzer = MarketAnalyzer()
            results["market"] = await market_analyzer.execute(preprocessed_data)
            logger.info("[AnalysisTools] Market analysis completed")

            # 2. 트렌드 분석
            trend_analyzer = TrendAnalyzer()
            results["trend"] = await trend_analyzer.execute(preprocessed_data)
            logger.info("[AnalysisTools] Trend analysis completed")

            # 3. 리스크 평가
            risk_assessor = RiskAssessor()
            results["risk"] = await risk_assessor.execute(preprocessed_data)
            logger.info("[AnalysisTools] Risk assessment completed")

            # 4. 맞춤 분석 (전세금 인상률 등)
            results["custom"] = self._perform_custom_analysis(query, preprocessed_data)
            if results["custom"]["type"] != "general":
                logger.info(f"[CustomAnalysis] {results['custom']['type']} performed")

            # 결과 저장
            state["raw_analysis"] = results
            state["analysis_status"] = "completed"
            state["analysis_progress"] = {"current": "analyze", "percent": 0.6}

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            state["analysis_status"] = "failed"
            state["error"] = str(e)

        return state

    def _perform_custom_analysis(self, query: str, data: Dict) -> Dict:
        """쿼리 기반 맞춤 분석"""

        # 전세금 인상 관련 쿼리 감지
        if "전세금" in query and any(x in query for x in ["올", "인상", "올려"]):
            return self._analyze_rent_increase(query, data)

        return {"type": "general"}

    def _analyze_rent_increase(self, query: str, data: Dict) -> Dict:
        """전세금 인상률 계산"""

        # 쿼리에서 금액 추출 (예: "3억을 10억으로")
        amounts = re.findall(r'(\d+)억', query)

        if len(amounts) >= 2:
            old_amount = float(amounts[0])
            new_amount = float(amounts[1])
            increase_rate = ((new_amount - old_amount) / old_amount) * 100

            return {
                "type": "rent_increase_analysis",
                "old_amount": f"{old_amount}억",
                "new_amount": f"{new_amount}억",
                "increase_amount": f"{new_amount - old_amount}억",
                "increase_rate": f"{increase_rate:.1f}%",
                "legal_limit": "5%",
                "is_legal": increase_rate <= 5,
                "assessment": f"요청된 인상률 {increase_rate:.1f}%는 법정 한도 5%를 {'초과' if increase_rate > 5 else '준수'}합니다.",
                "recommendation": "법정 한도를 초과하는 인상은 거부할 수 있습니다." if increase_rate > 5 else "법정 범위 내 인상입니다."
            }

        return {"type": "rent_increase_analysis", "status": "insufficient_data"}

    async def generate_insights_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """인사이트 생성 노드"""
        logger.info("[AnalysisTeam] Generating insights")

        state["analysis_progress"] = {"current": "insights", "percent": 0.7}

        # LLM 사용 가능 시 LLM 기반 인사이트 생성
        if self.llm_context and self.llm_context.api_key:
            try:
                insights = await self._generate_insights_with_llm(state)
            except Exception as e:
                logger.warning(f"LLM insight generation failed, using fallback: {e}")
                analysis_method = self.analysis_methods.get(
                    state.get("analysis_type", "comprehensive"),
                    self._comprehensive_analysis
                )
                insights = analysis_method(state)
        else:
            analysis_method = self.analysis_methods.get(
                state.get("analysis_type", "comprehensive"),
                self._comprehensive_analysis
            )
            insights = analysis_method(state)

        state["insights"] = insights
        state["analysis_progress"] = {"current": "insights", "percent": 0.8}
        state["confidence_score"] = self._calculate_confidence(state)

        return state

    async def _generate_insights_with_llm(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """LLM을 사용한 인사이트 생성"""
        raw_analysis = state.get("raw_analysis", {})
        analysis_type = state.get("analysis_type", "comprehensive")
        query = state.get("shared_context", {}).get("query", "")

        try:
            result = await self.llm_service.complete_json_async(
                prompt_name="insight_generation",
                variables={
                    "query": query,
                    "analysis_type": analysis_type,
                    "raw_analysis": json.dumps(raw_analysis, ensure_ascii=False, indent=2)
                },
                temperature=0.3
            )

            logger.info(f"LLM Insight Generation: {len(result.get('insights', []))} insights generated")

            insights = []
            for insight_data in result.get("insights", []):
                insight = AnalysisInsight(
                    insight_type=insight_data.get("type", "key_finding"),
                    content=f"{insight_data.get('title', '')}: {insight_data.get('description', '')}",
                    confidence=insight_data.get("confidence", 0.7),
                    supporting_data=insight_data.get("supporting_evidence", {})
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            raise

    def _comprehensive_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """종합 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        # custom 분석 결과 확인
        if "custom" in raw_analysis and raw_analysis["custom"]["type"] == "rent_increase_analysis":
            custom = raw_analysis["custom"]
            insights.append(AnalysisInsight(
                insight_type="rent_increase",
                content=custom.get("assessment", ""),
                confidence=0.95,
                supporting_data=custom
            ))

        # 시장 분석 결과
        if "market" in raw_analysis and raw_analysis["market"].get("status") == "success":
            market = raw_analysis["market"]
            insights.append(AnalysisInsight(
                insight_type="market_condition",
                content=f"시장 상황: {market.get('market_conditions', {}).get('overall', 'N/A')}",
                confidence=0.8,
                supporting_data=market.get("metrics", {})
            ))

        return insights

    def _market_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """시장 분석"""
        return self._comprehensive_analysis(state)

    def _risk_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """리스크 분석"""
        return self._comprehensive_analysis(state)

    def _comparison_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """비교 분석"""
        return self._comprehensive_analysis(state)

    def _calculate_confidence(self, state: AnalysisTeamState) -> float:
        """신뢰도 계산"""
        base_confidence = 0.5

        if state.get("input_data"):
            base_confidence += 0.1 * min(len(state["input_data"]), 3)

        if state.get("analysis_status") == "completed":
            base_confidence += 0.2

        return min(base_confidence, 1.0)

    async def create_report_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """보고서 생성 노드"""
        logger.info("[AnalysisTeam] Creating report")

        state["analysis_progress"] = {"current": "report", "percent": 0.9}

        report = AnalysisReport(
            title=f"{state.get('analysis_type', '종합')} 분석 보고서",
            summary=self._generate_summary(state),
            key_findings=self._extract_key_findings(state),
            metrics=state.get("metrics", {}),
            insights=state.get("insights", []),
            visualizations=[],
            recommendations=self._compile_recommendations(state),
            generated_at=datetime.now()
        )

        state["report"] = report
        state["analysis_progress"] = {"current": "report", "percent": 1.0}

        return state

    def _generate_summary(self, state: AnalysisTeamState) -> str:
        """요약 생성"""
        analysis_type = state.get("analysis_type", "종합")
        insights_count = len(state.get("insights", []))
        confidence = state.get("confidence_score", 0)

        return (f"{analysis_type} 분석을 완료했습니다. "
                f"{insights_count}개의 주요 인사이트를 도출했으며, "
                f"신뢰도는 {confidence:.0%}입니다.")

    def _extract_key_findings(self, state: AnalysisTeamState) -> List[str]:
        """주요 발견사항 추출"""
        findings = []

        for insight in state.get("insights", []):
            if insight.get("confidence", 0) > 0.7:
                findings.append(insight.get("content", ""))

        return findings[:5]

    def _compile_recommendations(self, state: AnalysisTeamState) -> List[str]:
        """추천사항 종합"""
        recommendations = []

        # raw_analysis에서 추천사항 추출
        raw_analysis = state.get("raw_analysis", {})
        if "custom" in raw_analysis and "recommendation" in raw_analysis["custom"]:
            recommendations.append(raw_analysis["custom"]["recommendation"])

        return list(set(recommendations))

    async def finalize_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """최종화 노드"""
        logger.info("[AnalysisTeam] Finalizing")

        state["end_time"] = datetime.now()

        # Calculate analysis time
        if state["start_time"] and state["end_time"]:
            state["analysis_time"] = (state["end_time"] - state["start_time"]).total_seconds()

        if state.get("error"):
            state["status"] = "failed"
        elif state.get("report"):
            state["status"] = "completed"
        else:
            state["status"] = "partial"

        logger.info(f"[AnalysisTeam] Completed with status: {state['status']}")
        return state

    async def execute(
        self,
        shared_state: SharedState,
        analysis_type: str = "comprehensive",
        input_data: Optional[Dict] = None
    ) -> AnalysisTeamState:
        """AnalysisTeam 실행"""
        # 입력 데이터 준비
        analysis_inputs = []
        if input_data:
            for source, data in input_data.items():
                analysis_inputs.append(AnalysisInput(
                    data_source=source,
                    data=data,
                    metadata={}
                ))

        # 초기 상태 생성
        initial_state = AnalysisTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            analysis_type=analysis_type,
            input_data=analysis_inputs,
            raw_analysis={},
            metrics={},
            insights=[],
            report={},
            visualization_data=None,
            recommendations=[],
            confidence_score=0.0,
            analysis_progress={"current": "init", "percent": 0.0},
            start_time=None,
            end_time=None,
            analysis_time=None,
            error=None
        )

        # 서브그래프 실행
        try:
            final_state = await self.app.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"AnalysisTeam execution failed: {e}")
            initial_state["status"] = "failed"
            initial_state["error"] = str(e)
            return initial_state
