// API 요청/응답 타입 정의 (FastAPI Pydantic 모델과 일치)

export interface SessionStartRequest {
  user_id?: string
  metadata?: Record<string, any>
}

export interface SessionStartResponse {
  session_id: string
  message: string
  expires_at: string
}

export interface ChatRequest {
  query: string
  session_id: string
  enable_checkpointing?: boolean
  user_context?: Record<string, any>
}

export interface ChatResponse {
  session_id: string
  request_id: string
  status: string
  response: {
    answer: string
    confidence?: number
    sources?: Array<{
      law_name: string
      article: string
      relevance: number
    }>
  }
  planning_info?: {
    query_analysis?: any
    execution_steps?: any[]
    plan_status?: string
  }
  team_results?: Record<string, any>
  search_results?: any[]
  analysis_metrics?: any
  execution_time_ms?: number
  teams_executed: string[]
  error?: string
}

export interface SessionInfo {
  session_id: string
  user_id?: string
  created_at: string
  last_activity: string
  expires_at: string
  is_active: boolean
  metadata?: Record<string, any>
}

export interface DeleteSessionResponse {
  message: string
  session_id: string
}

export interface SessionStats {
  total_sessions: number
  active_sessions: number
  expired_sessions: number
}
