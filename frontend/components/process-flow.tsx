"use client"

import { useEffect, useState } from "react"
import { CheckCircle2, XCircle, Loader2, Bot } from "lucide-react"
import { Card } from "@/components/ui/card"
import type { ProcessFlowProps, ProcessStep, AgentType } from "@/types/process"
import { AGENT_NAMES } from "@/types/process"

/**
 * Process Flow Spinner Component (Inline Chat Message Style)
 * 채팅 메시지처럼 표시되는 백엔드 처리 과정 시각화 컴포넌트
 */
export function ProcessFlow({ isVisible, state, onCancel }: ProcessFlowProps) {
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
      <div className="flex items-start gap-3 max-w-md">
        {/* Bot Icon */}
        <div className="rounded-full p-2 bg-muted text-muted-foreground flex-shrink-0">
          <Bot className="h-4 w-4" />
        </div>

        {/* Process Card */}
        <Card className="p-3 bg-card border">
          {/* 상단: 에이전트 이름 + 스피너 */}
          <div className="flex items-center gap-3 mb-3">
            {/* 작은 스피너/아이콘 */}
            <div className="flex-shrink-0">
              {isError ? (
                <XCircle className="w-6 h-6 text-red-500" />
              ) : isComplete ? (
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              ) : (
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              )}
            </div>

            {/* 에이전트 이름 + 메시지 */}
            <div className="flex-1">
              <p className="text-sm font-medium">{agentName}</p>
              <p className="text-xs text-muted-foreground">{state.message}</p>
            </div>

            {/* 경과 시간 */}
            <div className="text-xs text-muted-foreground">
              {(elapsedTime / 1000).toFixed(1)}s
            </div>
          </div>

          {/* 진행 단계 표시 (컴팩트) */}
          <div className="space-y-1.5">
            <StepIndicator
              label="계획 수립"
              isActive={state.step === "planning"}
              isComplete={isStepComplete(state.step, "planning")}
            />
            <StepIndicator
              label="정보 검색"
              isActive={state.step === "searching"}
              isComplete={isStepComplete(state.step, "searching")}
            />
            <StepIndicator
              label="데이터 분석"
              isActive={state.step === "analyzing"}
              isComplete={isStepComplete(state.step, "analyzing")}
            />
            <StepIndicator
              label="답변 생성"
              isActive={state.step === "generating"}
              isComplete={isStepComplete(state.step, "generating")}
            />
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
 * 단계별 인디케이터 컴포넌트
 */
function StepIndicator({
  label,
  isActive,
  isComplete
}: {
  label: string
  isActive: boolean
  isComplete: boolean
}) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-4 h-4 rounded-full flex items-center justify-center transition-all ${
          isComplete
            ? "bg-green-500"
            : isActive
            ? "bg-primary animate-pulse"
            : "bg-gray-300 dark:bg-gray-600"
        }`}
      >
        {isComplete ? (
          <CheckCircle2 className="w-3 h-3 text-white" />
        ) : isActive ? (
          <Loader2 className="w-3 h-3 text-white animate-spin" />
        ) : (
          <div className="w-1.5 h-1.5 bg-white rounded-full" />
        )}
      </div>
      <span
        className={`text-xs ${
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
