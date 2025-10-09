"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { ProgressBar } from "@/components/ui/progress-bar"
import { StepItem } from "@/components/step-item"
import { Settings, Clock } from "lucide-react"
import type { ExecutionStep } from "@/types/execution"

interface ExecutionProgressPageProps {
  steps: ExecutionStep[]
  estimatedTime: number      // 초
  startTime?: number          // timestamp
}

/**
 * 작업 실행 중 페이지 (TODO 스타일)
 *
 * execution_steps 기반 실시간 진행 상황 표시
 * - 개별 작업 진행 상황 (StepItem)
 * - 전체 진행률
 * - 경과 시간 / 예상 시간
 */
export function ExecutionProgressPage({
  steps,
  estimatedTime,
  startTime
}: ExecutionProgressPageProps) {
  const [elapsedTime, setElapsedTime] = useState(0)

  // 경과 시간 계산
  useEffect(() => {
    if (!startTime) {
      setElapsedTime(0)
      return
    }

    const interval = setInterval(() => {
      setElapsedTime(Date.now() - startTime)
    }, 100)

    return () => clearInterval(interval)
  }, [startTime])

  // 진행 상황 계산
  const totalSteps = steps.length
  const completedSteps = steps.filter(s => s.status === "completed").length
  const failedSteps = steps.filter(s => s.status === "failed").length
  const currentStep = steps.find(s => s.status === "in_progress")

  // 전체 진행률 (0-100)
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  // 예상 남은 시간
  const estimatedTimeMs = estimatedTime * 1000
  const remainingTime = Math.max(estimatedTimeMs - elapsedTime, 0)

  // 시간 포맷팅
  const formatTime = (ms: number) => {
    const seconds = ms / 1000
    if (seconds < 60) return `${seconds.toFixed(1)}초`
    const minutes = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${minutes}분 ${secs}초`
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-4 bg-card border flex-1">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Settings className="w-5 h-5 text-primary animate-spin-slow" />
                작업 실행 중
                <span className="text-sm font-normal text-muted-foreground">
                  ({completedSteps}/{totalSteps} 완료)
                </span>
              </h3>
              {currentStep && (
                <p className="text-sm text-muted-foreground mt-1">
                  현재: {currentStep.description}
                </p>
              )}
            </div>
          </div>

          {/* 전체 진행률 */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">전체 진행률</span>
              <span className="text-sm text-muted-foreground">
                {overallProgress.toFixed(0)}%
              </span>
            </div>
            <ProgressBar
              value={overallProgress}
              size="md"
              variant={failedSteps > 0 ? "warning" : "default"}
            />
          </div>

          {/* 작업 리스트 */}
          <div className="space-y-2 mb-4">
            <div className="text-sm font-medium mb-2">진행 상황:</div>
            {steps.map((step, index) => (
              <StepItem
                key={step.step_id}
                step={step}
                index={index}
              />
            ))}
          </div>

          {/* 타이머 */}
          <div className="border-t pt-3 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span>경과 시간</span>
              </div>
              <span className="font-mono">{formatTime(elapsedTime)}</span>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">예상 시간</span>
              <span className="font-mono">{formatTime(estimatedTimeMs)}</span>
            </div>

            {elapsedTime < estimatedTimeMs && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">남은 시간</span>
                <span className="font-mono text-primary">
                  약 {formatTime(remainingTime)}
                </span>
              </div>
            )}

            {elapsedTime > estimatedTimeMs && (
              <div className="text-xs text-yellow-600 dark:text-yellow-400">
                ⚠️ 예상 시간을 초과했습니다
              </div>
            )}
          </div>

          {/* 실패한 작업이 있을 경우 */}
          {failedSteps > 0 && (
            <div className="mt-3 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-xs text-red-700 dark:text-red-400">
                ⚠️ {failedSteps}개의 작업이 실패했습니다. 일부 정보가 누락될 수 있습니다.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
