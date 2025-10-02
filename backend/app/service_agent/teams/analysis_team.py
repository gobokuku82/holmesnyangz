"""
Analysis Team Supervisor - 데이터 분석을 관리하는 서브그래프
수집된 데이터를 분석하여 인사이트와 추천사항을 생성
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.service.core.separated_states import (
    AnalysisTeamState,
    AnalysisInput,
    AnalysisMetrics,
    AnalysisInsight,
    AnalysisReport,
    SharedState
)
from app.service.core.agent_registry import AgentRegistry
from app.service.core.agent_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class AnalysisTeamSupervisor:
    """
    분석 팀 Supervisor
    AnalysisAgent를 관리하여 데이터 분석 및 보고서 생성
    """

    def __init__(self, llm_context=None):
        """
        초기화

        Args:
            llm_context: LLM 컨텍스트
        """
        self.llm_context = llm_context
        self.team_name = "analysis"

        # Agent 초기화
        self.available_agents = self._initialize_agents()

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

    def _initialize_agents(self) -> Dict[str, bool]:
        """사용 가능한 Agent 확인"""
        agent_types = ["analysis_agent"]
        available = {}

        for agent_name in agent_types:
            available[agent_name] = agent_name in AgentRegistry.list_agents(enabled_only=True)

        logger.info(f"AnalysisTeam available agents: {available}")
        return available

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
        workflow.set_entry_point("prepare")
        workflow.add_edge("prepare", "preprocess")

        # 전처리 필요 여부
        workflow.add_conditional_edges(
            "preprocess",
            self._needs_preprocessing,
            {
                "analyze": "analyze",
                "skip": "analyze"
            }
        )

        workflow.add_edge("analyze", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", "finalize")
        workflow.add_edge("finalize", END)

        self.app = workflow.compile()
        logger.info("AnalysisTeam subgraph built successfully")

    def _needs_preprocessing(self, state: AnalysisTeamState) -> str:
        """전처리 필요 여부 확인"""
        # 현재는 항상 분석으로 진행
        return "analyze"

    async def prepare_analysis_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        분석 준비 노드
        입력 데이터 확인 및 분석 타입 결정
        """
        logger.info("[AnalysisTeam] Preparing analysis")

        state["team_name"] = self.team_name
        state["status"] = "in_progress"
        state["start_time"] = datetime.now()
        state["analysis_status"] = "preparing"
        state["analysis_progress"] = 0.0

        # 분석 타입 설정
        if not state.get("analysis_type"):
            state["analysis_type"] = "comprehensive"

        # 입력 데이터 준비
        if not state.get("input_data"):
            state["input_data"] = self._prepare_input_data(state)

        # 분석 메서드 선택
        state["analysis_method"] = state.get("analysis_type", "comprehensive")

        logger.info(f"[AnalysisTeam] Analysis type: {state['analysis_type']}")
        return state

    def _prepare_input_data(self, state: AnalysisTeamState) -> List[AnalysisInput]:
        """입력 데이터 준비"""
        input_data = []
        shared_context = state.get("shared_context", {})

        # 기본 입력 데이터 생성
        input_data.append(AnalysisInput(
            data_source="context",
            data_type="query",
            raw_data={"query": shared_context.get("query", "")},
            preprocessing_required=False
        ))

        return input_data

    async def preprocess_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        데이터 전처리 노드
        필요한 경우 데이터 정제 및 변환
        """
        logger.info("[AnalysisTeam] Preprocessing data")

        state["preprocessing_status"] = "in_progress"
        state["analysis_progress"] = 0.1

        # 전처리가 필요한 데이터 처리
        preprocessed = {}
        for input_item in state.get("input_data", []):
            if input_item.get("preprocessing_required"):
                # 데이터 정제 로직
                preprocessed[input_item["data_source"]] = self._preprocess_item(input_item)
            else:
                preprocessed[input_item["data_source"]] = input_item["raw_data"]

        state["preprocessed_data"] = preprocessed
        state["preprocessing_status"] = "completed"
        state["analysis_progress"] = 0.2

        return state

    def _preprocess_item(self, input_item: AnalysisInput) -> Dict:
        """개별 데이터 전처리"""
        # 간단한 전처리 로직
        data = input_item.get("raw_data", {})

        # 숫자 추출, 정규화 등
        if input_item.get("data_type") == "numeric":
            # 숫자 데이터 정규화
            pass

        return data

    async def analyze_data_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        데이터 분석 노드
        AnalysisAgent 호출
        """
        logger.info("[AnalysisTeam] Analyzing data")

        state["analysis_status"] = "analyzing"
        state["analysis_progress"] = 0.3

        if not self.available_agents.get("analysis_agent"):
            # AnalysisAgent가 없으면 모의 분석
            state["raw_analysis"] = self._mock_analysis(state)
            state["analysis_status"] = "completed"
            state["analysis_progress"] = 0.6
            return state

        # AnalysisAgent 입력 준비
        analysis_input = {
            "analysis_type": state.get("analysis_type", "comprehensive"),
            "input_data": state.get("preprocessed_data", {}),
            "query": state.get("shared_context", {}).get("query", ""),
            "original_query": state.get("shared_context", {}).get("original_query", ""),
            "chat_session_id": state.get("shared_context", {}).get("session_id", ""),
            "shared_context": {},
            "todos": [],
            "todo_counter": 0
        }

        try:
            # AnalysisAgent 실행
            result = await AgentAdapter.execute_agent_dynamic(
                "analysis_agent",
                analysis_input,
                self.llm_context
            )

            if result.get("status") in ["completed", "success"]:
                data = result.get("collected_data", {})

                # 분석 결과 저장
                state["raw_analysis"] = data.get("analysis", {})

                # 메트릭 추출
                if "metrics" in data:
                    state["metrics"] = self._parse_metrics(data["metrics"])

                state["analysis_status"] = "completed"
                state["analysis_progress"] = 0.6
            else:
                state["analysis_status"] = "failed"
                state["error"] = result.get("error", "Analysis failed")

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            state["analysis_status"] = "failed"
            state["error"] = str(e)

        return state

    def _mock_analysis(self, state: AnalysisTeamState) -> Dict:
        """모의 분석 (테스트용)"""
        analysis_type = state.get("analysis_type", "comprehensive")

        if analysis_type == "market":
            return {
                "market_trend": "상승",
                "average_price": "5억",
                "volatility": "낮음",
                "recommendation": "투자 적기"
            }
        elif analysis_type == "risk":
            return {
                "risk_level": "중간",
                "risk_factors": ["금리 상승", "공급 과잉"],
                "mitigation": ["장기 계약", "보증 보험"]
            }
        else:
            return {
                "summary": "종합 분석 결과",
                "key_points": ["시장 안정", "규제 강화"],
                "outlook": "중립적"
            }

    def _parse_metrics(self, metrics_data: Any) -> List[AnalysisMetrics]:
        """메트릭 데이터 파싱"""
        metrics = []

        if isinstance(metrics_data, dict):
            for key, value in metrics_data.items():
                metric = AnalysisMetrics(
                    metric_name=key,
                    value=float(value) if isinstance(value, (int, float)) else 0.0,
                    unit="",
                    trend="stable",
                    comparison=None
                )
                metrics.append(metric)

        return metrics

    async def generate_insights_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        인사이트 생성 노드
        분석 결과를 바탕으로 인사이트 도출 - LLM 사용 시 더 정확함
        """
        logger.info("[AnalysisTeam] Generating insights")

        state["analysis_progress"] = 0.7

        # LLM 사용 가능 시 LLM 기반 인사이트 생성
        if self.llm_context and self.llm_context.api_key:
            try:
                insights = await self._generate_insights_with_llm(state)
            except Exception as e:
                logger.warning(f"LLM insight generation failed, using fallback: {e}")
                # Fallback: 기존 rule-based 방식
                analysis_method = self.analysis_methods.get(
                    state.get("analysis_type", "comprehensive"),
                    self._comprehensive_analysis
                )
                insights = analysis_method(state)
        else:
            # Fallback: 기존 rule-based 방식
            analysis_method = self.analysis_methods.get(
                state.get("analysis_type", "comprehensive"),
                self._comprehensive_analysis
            )
            insights = analysis_method(state)

        state["insights"] = insights
        state["analysis_progress"] = 0.8

        # 신뢰도 계산
        state["confidence_level"] = self._calculate_confidence(state)

        return state

    async def _generate_insights_with_llm(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """LLM을 사용한 인사이트 생성"""
        from openai import OpenAI

        # 분석 데이터 준비
        raw_analysis = state.get("raw_analysis", {})
        analysis_type = state.get("analysis_type", "comprehensive")
        query = state.get("shared_context", {}).get("query", "")

        system_prompt = """당신은 부동산 데이터 분석 전문가입니다.
수집된 데이터를 분석하여 의미 있는 인사이트와 실행 가능한 추천사항을 제공하세요.

## 분석 타입별 가이드:

### comprehensive (종합 분석)
- 전반적인 상황 파악
- 주요 트렌드 및 패턴 식별
- 다각도 관점에서 분석
- 장단점 모두 고려

### market (시장 분석)
- 가격 트렌드 분석
- 수요/공급 상황 파악
- 시장 전망 제시
- 투자 타이밍 평가

### risk (리스크 분석)
- 잠재적 위험 요소 식별
- 위험도 수준 평가
- 완화 방안 제시
- 주의사항 안내

### comparison (비교 분석)
- 옵션 간 비교
- 장단점 대비
- 최적 선택지 추천
- 의사결정 기준 제시

## 응답 형식:
{
    "insights": [
        {
            "type": "key_finding | trend | risk | opportunity | recommendation",
            "title": "인사이트 제목 (한줄)",
            "description": "상세 설명 (2-3문장)",
            "confidence": 0.0~1.0,
            "importance": "high | medium | low",
            "supporting_evidence": ["근거1", "근거2"],
            "recommendations": ["추천사항1", "추천사항2"]
        }
    ],
    "overall_assessment": "전체적인 평가 (2-3문장)",
    "key_takeaways": ["핵심 포인트1", "핵심 포인트2", "핵심 포인트3"]
}

## 인사이트 작성 가이드:
- 구체적이고 실행 가능한 내용
- 전문 용어 사용 시 간단한 설명 추가
- 숫자와 데이터로 뒷받침
- 긍정적/부정적 측면 균형있게 제시
- 사용자가 실제로 활용할 수 있는 추천사항"""

        try:
            client = OpenAI(api_key=self.llm_context.api_key)

            # 분석 데이터를 컨텍스트로 전달
            user_prompt = f"""## 사용자 질문:
{query}

## 분석 타입:
{analysis_type}

## 수집된 데이터:
{json.dumps(raw_analysis, ensure_ascii=False, indent=2)}

위 데이터를 바탕으로 의미 있는 인사이트를 생성해주세요."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"LLM Insight Generation: {len(result.get('insights', []))} insights generated")

            # LLM 응답을 AnalysisInsight 객체로 변환
            insights = []
            for insight_data in result.get("insights", []):
                insight = AnalysisInsight(
                    insight_type=insight_data.get("type", "key_finding"),
                    description=f"{insight_data.get('title', '')}: {insight_data.get('description', '')}",
                    confidence=insight_data.get("confidence", 0.7),
                    supporting_data=insight_data.get("supporting_evidence", []),
                    recommendations=insight_data.get("recommendations", [])
                )
                insights.append(insight)

            # 전체 평가와 핵심 포인트 저장
            state["llm_assessment"] = {
                "overall": result.get("overall_assessment", ""),
                "key_takeaways": result.get("key_takeaways", [])
            }

            return insights

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            raise

    def _comprehensive_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """종합 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        # 주요 발견사항
        if raw_analysis:
            insights.append(AnalysisInsight(
                insight_type="key_finding",
                description="시장 상황이 안정적입니다",
                confidence=0.8,
                supporting_data=[raw_analysis],
                recommendations=["현재 시점이 거래에 적합합니다"]
            ))

        return insights

    def _market_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """시장 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        market_trend = raw_analysis.get("market_trend", "중립")
        insights.append(AnalysisInsight(
            insight_type="market_trend",
            description=f"시장 트렌드: {market_trend}",
            confidence=0.75,
            supporting_data=[{"trend": market_trend}],
            recommendations=["시장 동향을 지속적으로 모니터링하세요"]
        ))

        return insights

    def _risk_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """리스크 분석"""
        raw_analysis = state.get("raw_analysis", {})
        insights = []

        risk_level = raw_analysis.get("risk_level", "낮음")
        risk_factors = raw_analysis.get("risk_factors", [])

        insights.append(AnalysisInsight(
            insight_type="risk_assessment",
            description=f"위험도: {risk_level}",
            confidence=0.85,
            supporting_data=[{"risk_factors": risk_factors}],
            recommendations=raw_analysis.get("mitigation", [])
        ))

        return insights

    def _comparison_analysis(self, state: AnalysisTeamState) -> List[AnalysisInsight]:
        """비교 분석"""
        insights = []

        insights.append(AnalysisInsight(
            insight_type="comparison",
            description="비교 분석 결과",
            confidence=0.7,
            supporting_data=[],
            recommendations=["더 많은 데이터가 필요합니다"]
        ))

        return insights

    def _calculate_confidence(self, state: AnalysisTeamState) -> float:
        """신뢰도 계산"""
        # 간단한 신뢰도 계산
        base_confidence = 0.5

        # 데이터 양에 따라 증가
        if state.get("input_data"):
            base_confidence += 0.1 * min(len(state["input_data"]), 3)

        # 분석 성공 여부
        if state.get("analysis_status") == "completed":
            base_confidence += 0.2

        return min(base_confidence, 1.0)

    async def create_report_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        보고서 생성 노드
        분석 결과와 인사이트를 종합하여 보고서 생성
        """
        logger.info("[AnalysisTeam] Creating report")

        state["analysis_progress"] = 0.9

        # 보고서 생성
        report = AnalysisReport(
            summary=self._generate_summary(state),
            key_findings=self._extract_key_findings(state),
            metrics=state.get("metrics", []),
            insights=state.get("insights", []),
            visualizations=[],  # 시각화는 추후 구현
            recommendations=self._compile_recommendations(state),
            generated_at=datetime.now()
        )

        state["report"] = report
        state["analysis_progress"] = 1.0

        # 데이터 품질 점수
        state["data_quality_score"] = self._calculate_data_quality(state)

        return state

    def _generate_summary(self, state: AnalysisTeamState) -> str:
        """요약 생성"""
        analysis_type = state.get("analysis_type", "종합")
        insights_count = len(state.get("insights", []))
        confidence = state.get("confidence_level", 0)

        return (f"{analysis_type} 분석을 완료했습니다. "
                f"{insights_count}개의 주요 인사이트를 도출했으며, "
                f"신뢰도는 {confidence:.0%}입니다.")

    def _extract_key_findings(self, state: AnalysisTeamState) -> List[str]:
        """주요 발견사항 추출"""
        findings = []

        for insight in state.get("insights", []):
            if insight.get("confidence", 0) > 0.7:
                findings.append(insight.get("description", ""))

        # 원시 분석에서 추가 추출
        raw_analysis = state.get("raw_analysis", {})
        if "key_points" in raw_analysis:
            findings.extend(raw_analysis["key_points"])

        return findings[:5]  # 상위 5개만

    def _compile_recommendations(self, state: AnalysisTeamState) -> List[str]:
        """추천사항 종합"""
        recommendations = []

        # 인사이트에서 추천사항 수집
        for insight in state.get("insights", []):
            recommendations.extend(insight.get("recommendations", []))

        # 중복 제거
        return list(set(recommendations))

    def _calculate_data_quality(self, state: AnalysisTeamState) -> float:
        """데이터 품질 점수 계산"""
        score = 0.5

        # 입력 데이터 존재
        if state.get("input_data"):
            score += 0.2

        # 전처리 완료
        if state.get("preprocessing_status") == "completed":
            score += 0.1

        # 분석 완료
        if state.get("analysis_status") == "completed":
            score += 0.2

        return min(score, 1.0)

    async def finalize_node(self, state: AnalysisTeamState) -> AnalysisTeamState:
        """
        최종화 노드
        상태 정리 및 완료 처리
        """
        logger.info("[AnalysisTeam] Finalizing")

        state["end_time"] = datetime.now()

        # 상태 결정
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
        """
        AnalysisTeam 실행

        Args:
            shared_state: 공유 상태
            analysis_type: 분석 타입
            input_data: 입력 데이터

        Returns:
            분석 팀 상태
        """
        # 입력 데이터 준비
        analysis_inputs = []
        if input_data:
            for source, data in input_data.items():
                analysis_inputs.append(AnalysisInput(
                    data_source=source,
                    data_type="mixed",
                    raw_data=data,
                    preprocessing_required=False
                ))

        # 초기 상태 생성
        initial_state = AnalysisTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            analysis_type=analysis_type,
            input_data=analysis_inputs,
            analysis_params={},
            preprocessing_status=None,
            preprocessed_data=None,
            analysis_status="",
            analysis_progress=0.0,
            raw_analysis=None,
            metrics=[],
            insights=[],
            report=None,
            analysis_method="",
            confidence_level=0.0,
            data_quality_score=0.0,
            start_time=None,
            end_time=None,
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


# 테스트 코드
if __name__ == "__main__":
    async def test_analysis_team():
        from app.service.core.separated_states import StateManager

        # AnalysisTeam 초기화
        analysis_team = AnalysisTeamSupervisor()

        # 테스트 케이스
        test_cases = [
            ("comprehensive", {"search_results": {"laws": ["법률1", "법률2"]}}),
            ("market", {"market_data": {"price": "5억", "trend": "상승"}}),
            ("risk", {"risk_data": {"factors": ["금리", "공급"]}})
        ]

        for analysis_type, input_data in test_cases:
            print(f"\n{'='*60}")
            print(f"Analysis Type: {analysis_type}")
            print(f"Input Data: {input_data}")
            print("-"*60)

            # 공유 상태 생성
            shared_state = StateManager.create_shared_state(
                query=f"{analysis_type} 분석해주세요",
                session_id="test_analysis"
            )

            # AnalysisTeam 실행
            result = await analysis_team.execute(
                shared_state,
                analysis_type=analysis_type,
                input_data=input_data
            )

            print(f"Status: {result['status']}")
            print(f"Progress: {result.get('analysis_progress', 0)*100:.0f}%")
            print(f"Confidence: {result.get('confidence_level', 0)*100:.0f}%")

            if result.get("report"):
                report = result["report"]
                print(f"\n[Report Summary]")
                print(report.get("summary"))
                print(f"Key Findings: {len(report.get('key_findings', []))}")
                print(f"Recommendations: {len(report.get('recommendations', []))}")

    import asyncio
    asyncio.run(test_analysis_team())