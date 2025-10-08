"use client"

import { useEffect, useState } from "react"
import { CheckCircle2, XCircle, Loader2, Bot } from "lucide-react"
import { Card } from "@/components/ui/card"
import type { ProcessFlowProps, ProcessStep, AgentType } from "@/types/process"
import type { ProcessFlowStep } from "@/types/chat"
import { AGENT_NAMES } from "@/types/process"

/**
 * Process Flow Spinner Component (Inline Chat Message Style)
 * 채팅 메시지처럼 표시되는 백엔드 처리 과정 시각화 컴포넌트
 *
 * @param dynamicSteps - (Optional) 백엔드 API에서 전달된 동적 단계 리스트
 */
export function ProcessFlow({
  isVisible,
  state,
  onCancel,
  dynamicSteps
}: ProcessFlowProps & { dynamicSteps?: ProcessFlowStep[] }) {
  const [elapsedTime, setElapsedTime] = useState(0)

  // 경과 시간 계산
  useEffect(() => {
    if (!isVisible || !state.startTime) {
      setElapsedTime(0)
      return
    }

    const interval = setInterval(() => {
      setElapsedTime(Date.now() - state.startTime!)
    }, 100)

    return () => clearInterval(interval)
  }, [isVisible, state.startTime])

  if (!isVisible) return null

  const agentName = state.agentType ? AGENT_NAMES[state.agentType] : "AI 에이전트"
  const isError = state.step === "error"
  const isComplete = state.step === "complete"

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        {/* Bot Icon */}
        <div className="rounded-full p-2 bg-muted text-muted-foreground flex-shrink-0">
          <Bot className="h-4 w-4" />
        </div>

        {/* Process Card - 가로 레이아웃 */}
        <Card className="p-3 bg-card border flex-1">
          {/* 상단 헤더: 에이전트명 + 메시지 + 시간 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {/* 작은 스피너/아이콘 */}
              <div className="flex-shrink-0">
                {isError ? (
                  <XCircle className="w-5 h-5 text-red-500" />
                ) : isComplete ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : (
                  <Loader2 className="w-5 h-5 text-primary animate-spin" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium">{agentName}</p>
                <p className="text-xs text-muted-foreground">{state.message}</p>
              </div>
            </div>

            {/* 경과 시간 */}
            <div className="text-xs text-muted-foreground font-mono">
              {(elapsedTime / 1000).toFixed(1)}s
            </div>
          </div>

          {/* 진행 단계 표시 (가로 방향) */}
          <div className="flex items-center gap-1">
            {dynamicSteps ? (
              // 동적 단계 렌더링 (백엔드 API에서 전달된 데이터)
              <>
                {dynamicSteps.map((step, index) => (
                  <div key={step.step} className="contents">
                    <StepIndicator
                      label={step.label}
                      isActive={step.status === "in_progress"}
                      isComplete={step.status === "completed"}
                      progress={step.progress}
                    />
                    {index < dynamicSteps.length - 1 && (
                      <StepConnector isComplete={step.status === "completed"} />
                    )}
                  </div>
                ))}
              </>
            ) : (
              // 정적 단계 렌더링 (fallback - 기존 로직)
              <>
                <StepIndicator
                  label="계획"
                  isActive={state.step === "planning"}
                  isComplete={isStepComplete(state.step, "planning")}
                />
                <StepConnector isComplete={isStepComplete(state.step, "planning")} />

                <StepIndicator
                  label="검색"
                  isActive={state.step === "searching"}
                  isComplete={isStepComplete(state.step, "searching")}
                />
                <StepConnector isComplete={isStepComplete(state.step, "searching")} />

                <StepIndicator
                  label="분석"
                  isActive={state.step === "analyzing"}
                  isComplete={isStepComplete(state.step, "analyzing")}
                />
                <StepConnector isComplete={isStepComplete(state.step, "analyzing")} />

                <StepIndicator
                  label="생성"
                  isActive={state.step === "generating"}
                  isComplete={isStepComplete(state.step, "generating")}
                />
              </>
            )}
          </div>

          {/* 에러 메시지 */}
          {isError && state.error && (
            <div className="mt-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-2">
              <p className="text-xs text-red-700 dark:text-red-400">
                {state.error}
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

/**
 * 단계별 인디케이터 컴포넌트 (가로 버전)
 */
function StepIndicator({
  label,
  isActive,
  isComplete,
  progress
}: {
  label: string
  isActive: boolean
  isComplete: boolean
  progress?: number
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center transition-all ${
          isComplete
            ? "bg-green-500"
            : isActive
            ? "bg-primary animate-pulse"
            : "bg-gray-300 dark:bg-gray-600"
        }`}
      >
        {isComplete ? (
          <CheckCircle2 className="w-4 h-4 text-white" />
        ) : isActive ? (
          <Loader2 className="w-4 h-4 text-white animate-spin" />
        ) : (
          <div className="w-2 h-2 bg-white rounded-full" />
        )}
      </div>
      <span
        className={`text-[10px] whitespace-nowrap ${
          isActive
            ? "text-foreground font-medium"
            : isComplete
            ? "text-green-600 dark:text-green-400"
            : "text-muted-foreground"
        }`}
      >
        {label}
      </span>
    </div>
  )
}

/**
 * 단계 연결선 컴포넌트
 */
function StepConnector({ isComplete }: { isComplete: boolean }) {
  return (
    <div
      className={`h-0.5 flex-1 mx-1 transition-all ${
        isComplete ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
      }`}
    />
  )
}

/**
 * 단계 완료 여부 확인
 */
function isStepComplete(currentStep: ProcessStep, checkStep: ProcessStep): boolean {
  const stepOrder: ProcessStep[] = ["idle", "planning", "searching", "analyzing", "generating", "complete"]
  const currentIndex = stepOrder.indexOf(currentStep)
  const checkIndex = stepOrder.indexOf(checkStep)

  return currentIndex > checkIndex
}

/**
 * 에이전트별 스피너 비디오 URL
 */
function getAgentSpinner(agentType: AgentType): string | null {
  switch (agentType) {
    case "analysis":
      return "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/%E1%84%87%E1%85%AE%E1%86%AB%E1%84%89%E1%85%A5%E1%86%A8-gR4J9NBbIUQ22zBcypvWpm6Jcd01QY.mp4"
    case "verification":
      return "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/%E1%84%80%E1%85%A5%E1%86%B7%E1%84%8C%E1%85%B3%E1%86%BC-k0ckJk8Vqe4d18VfshE8AOJMkpv86u.mp4"
    case "consultation":
      return "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/%E1%84%89%E1%85%A1%E1%86%BC%E1%84%83%E1%85%A1%E1%86%B7-VSSf5Rk3Z2uFikkQfNNLJlUNkINwZ7.mp4"
    default:
      return null
  }
}
