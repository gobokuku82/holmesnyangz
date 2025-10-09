/**
 * Execution Step Types
 * Backend의 ExecutionStepState와 동일한 구조
 */

export type StepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "failed"
  | "skipped"
  | "cancelled"

export interface ExecutionStep {
  // 기본 정보
  step_id: string                    // 고유 ID (예: "step_0", "step_1")
  agent_name: string                 // 담당 에이전트
  team: string                       // 담당 팀
  description: string                // 작업 설명
  priority: number                   // 우선순위
  dependencies: string[]             // 선행 작업 ID들

  // 실행 설정
  timeout: number                    // 타임아웃 (초)
  retry_count: number                // 재시도 횟수
  optional: boolean                  // 선택적 작업 여부
  input_mapping: Record<string, string>  // 입력 매핑

  // 상태 추적
  status: StepStatus
  progress_percentage: number        // 진행률 0-100

  // 타이밍
  started_at?: string                // ISO format datetime
  completed_at?: string              // ISO format datetime
  execution_time_ms?: number         // 실행 시간 (밀리초)

  // 결과
  result?: Record<string, any>       // 실행 결과 데이터
  error?: string                     // 에러 메시지
  error_details?: string             // 에러 상세 정보

  // 사용자 수정
  modified_by_user: boolean
  original_values?: Record<string, any>
}

export interface ExecutionPlan {
  intent: string
  confidence: number
  execution_steps: ExecutionStep[]
  execution_strategy: "sequential" | "parallel" | "pipeline"
  estimated_total_time: number
  keywords?: string[]
}

export interface ExecutionProgress {
  totalSteps: number
  completedSteps: number
  currentStep?: ExecutionStep
  overallProgress: number            // 0-100
  elapsedTime: number                // 밀리초
  estimatedTimeRemaining: number     // 밀리초
}
