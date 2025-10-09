/**
 * Type Definitions
 * Backend State와 동기화된 타입 정의
 */

// ExecutionStepState (Backend separated_states.py와 동일)
export interface ExecutionStepState {
  // 식별
  step_id: string;
  step_type: 'planning' | 'search' | 'document' | 'analysis' | 'synthesis' | 'generation';
  agent_type: string;

  // 작업 정보
  task: string;
  description: string;
  dependencies: string[];
  required_data: string[];

  // 상태
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped' | 'cancelled';
  progress_percentage: number;

  // 타이밍
  started_at: string | null;
  completed_at: string | null;
  execution_time_ms: number | null;

  // 결과
  result: Record<string, any> | null;
  error: string | null;
  error_details: string | null;

  // 사용자 수정
  modified_by_user: boolean;
  original_values: Record<string, any> | null;
}

// Session
export interface Session {
  session_id: string;
  created_at: string;
  expires_at: string;
}

// Chat Message (Frontend only)
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// Plan (Frontend representation)
export interface ExecutionPlan {
  execution_strategy: 'sequential' | 'parallel' | 'hybrid';
  execution_steps: ExecutionStepState[];
  estimated_total_time: number;
}

// Final Response
export interface FinalResponse {
  type: 'answer' | 'error' | 'clarification';
  content: string;
  data?: Record<string, any>;
}
