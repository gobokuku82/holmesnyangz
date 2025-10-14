/**
 * Chat Session Types for GPT-style Multi-Chat System
 *
 * 채팅 세션 관리를 위한 TypeScript 타입 정의
 */

import type { Message } from '@/components/chat-interface'

/**
 * 채팅 세션 (완전한 데이터)
 *
 * PostgreSQL chat_sessions 테이블과 매핑
 */
export interface ChatSession {
  session_id: string
  user_id: number
  title: string
  last_message: string | null
  message_count: number
  created_at: string  // ISO 8601 format
  updated_at: string  // ISO 8601 format
  is_active: boolean
  metadata?: Record<string, any>
}

/**
 * 세션 목록 아이템 (간소화된 정보)
 *
 * 사이드바에 표시할 요약 정보
 */
export interface SessionListItem {
  session_id: string
  title: string
  last_message: string | null
  message_count: number
  updated_at: string
  is_active: boolean
}

/**
 * 세션 생성 요청
 */
export interface CreateSessionRequest {
  title?: string
  metadata?: Record<string, any>
}

/**
 * 세션 생성 응답
 */
export interface CreateSessionResponse {
  success: boolean
  session: ChatSession
  timestamp: string
}

/**
 * 세션 목록 응답
 */
export interface SessionsResponse {
  user_id: number
  count: number
  sessions: SessionListItem[]
  timestamp: string
}

/**
 * 세션 메시지 응답
 */
export interface SessionMessagesResponse {
  session_id: string
  session_info: ChatSession
  message_count: number
  messages: ConversationMemory[]
  timestamp: string
}

/**
 * 대화 기록 (ConversationMemory)
 *
 * PostgreSQL conversation_memories 테이블과 매핑
 */
export interface ConversationMemory {
  id: string
  query: string
  response_summary: string
  relevance: string
  intent_detected: string | null
  entities_mentioned: Record<string, any> | null
  created_at: string
  conversation_metadata: Record<string, any> | null
}

/**
 * 세션 업데이트 요청
 */
export interface UpdateSessionRequest {
  title?: string
}

/**
 * 세션 삭제 응답
 */
export interface DeleteSessionResponse {
  success: boolean
  session_id: string
  deleted: 'soft' | 'hard'
  timestamp: string
}
