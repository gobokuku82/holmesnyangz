"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, Target, CheckCircle2 } from "lucide-react"
import type { ExecutionPlan } from "@/types/execution"

interface ExecutionPlanPageProps {
  plan: ExecutionPlan
}

/**
 * 실행 계획 표시 페이지
 *
 * 사용자에게 어떤 작업들이 수행될 예정인지 미리 보여줌
 * - 감지된 의도
 * - 예정 작업 리스트
 * - 예상 소요 시간
 */
export function ExecutionPlanPage({ plan }: ExecutionPlanPageProps) {
  const { intent, confidence, execution_steps, estimated_total_time, keywords } = plan

  // 의도 타입에 따른 한글 이름 매핑
  const intentNameMap: Record<string, string> = {
    legal_consult: "법률 상담",
    market_inquiry: "시세 조회",
    loan_consult: "대출 상담",
    contract_creation: "계약서 작성",
    contract_review: "계약서 검토",
    comprehensive: "종합 분석",
    risk_analysis: "리스크 분석",
    unclear: "명확화 필요",
    irrelevant: "기능 외 질문"
  }

  const intentName = intentNameMap[intent] || intent

  // 팀 이름 매핑
  const teamNameMap: Record<string, string> = {
    search_team: "검색팀",
    analysis_team: "분석팀",
    document_team: "문서팀"
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-4 bg-card border flex-1">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                작업 계획이 수립되었습니다
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                다음 작업들을 순차적으로 수행합니다
              </p>
            </div>
          </div>

          {/* 의도 정보 */}
          <div className="bg-muted/50 rounded-lg p-3 mb-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">감지된 의도:</span>
                <Badge variant="secondary">{intentName}</Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                신뢰도: {(confidence * 100).toFixed(0)}%
              </div>
            </div>

            {keywords && keywords.length > 0 && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-muted-foreground">키워드:</span>
                <div className="flex gap-1 flex-wrap">
                  {keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 예정 작업 리스트 */}
          <div className="space-y-2 mb-4">
            <div className="text-sm font-medium mb-2">예정 작업:</div>
            {execution_steps.map((step, index) => (
              <div
                key={step.step_id}
                className="flex items-start gap-3 p-2 rounded-md bg-muted/30"
              >
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                  {index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{step.description}</span>
                    <Badge variant="outline" className="text-xs">
                      {teamNameMap[step.team] || step.team}
                    </Badge>
                  </div>
                  {step.dependencies.length > 0 && (
                    <div className="text-xs text-muted-foreground mt-1">
                      의존성: {step.dependencies.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 예상 소요 시간 */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground border-t pt-3">
            <Clock className="w-4 h-4" />
            <span>예상 소요 시간: 약 {estimated_total_time.toFixed(1)}초</span>
          </div>

          {/* 시작 안내 */}
          <div className="mt-3 flex items-center gap-2 text-sm text-primary">
            <CheckCircle2 className="w-4 h-4" />
            <span>곧 작업을 시작합니다...</span>
          </div>
        </Card>
      </div>
    </div>
  )
}
