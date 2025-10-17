/**
 * useChatSessions Hook
 *
 * Chat History & State Endpoints
 * - 세션 CRUD 작업
 * - 현재 활성 세션 추적
 * - API 연동
 */

import { useState, useEffect, useCallback } from 'react'
import type {
  ChatSessionResponse,
  SessionListItem,
  CreateSessionRequest,
  UpdateSessionRequest,
  DeleteSessionResponse
} from '@/types/session'

const API_BASE_URL = 'http://localhost:8000/api/v1/chat'

export function useChatSessions() {
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * 세션 목록 조회
   */
  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`${API_BASE_URL}/sessions?limit=50`)

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.statusText}`)
      }

      // 백엔드는 ChatSessionResponse[] 배열을 직접 반환
      const data: ChatSessionResponse[] = await response.json()

      // ✅ 빈 세션 필터링 (message_count === 0인 세션 제외)
      const filteredSessions = data.filter(session => session.message_count > 0)
      setSessions(filteredSessions)

      // 첫 로드 시 가장 최근 세션을 현재 세션으로 설정
      if (!currentSessionId && filteredSessions.length > 0) {
        setCurrentSessionId(filteredSessions[0].id)
      }

      console.log(`[useChatSessions] Loaded ${filteredSessions.length} sessions (${data.length - filteredSessions.length} empty sessions filtered)`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      console.error('[useChatSessions] Failed to fetch sessions:', err)
    } finally {
      setLoading(false)
    }
  }, [currentSessionId])

  /**
   * 새 세션 생성
   */
  const createSession = useCallback(async (request?: CreateSessionRequest): Promise<string | null> => {
    try {
      setError(null)

      const response = await fetch(`${API_BASE_URL}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: request?.title || '새 대화',
          metadata: request?.metadata || {}
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`)
      }

      // 백엔드는 ChatSessionResponse 객체를 직접 반환
      const newSession: ChatSessionResponse = await response.json()

      // 새 세션을 목록 맨 앞에 추가
      setSessions(prev => [newSession, ...prev])
      setCurrentSessionId(newSession.id)

      console.log(`[useChatSessions] Created new session: ${newSession.id}`)
      return newSession.id
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      console.error('[useChatSessions] Failed to create session:', err)
      return null
    }
  }, [])

  /**
   * 세션 전환
   */
  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    console.log(`[useChatSessions] Switched to session: ${sessionId}`)
  }, [])

  /**
   * 세션 제목 업데이트
   */
  const updateSessionTitle = useCallback(async (sessionId: string, title: string): Promise<boolean> => {
    try {
      setError(null)

      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title })
      })

      if (!response.ok) {
        throw new Error(`Failed to update session title: ${response.statusText}`)
      }

      // 로컬 상태 업데이트 (id 필드 사용)
      setSessions(prev => prev.map(s =>
        s.id === sessionId ? { ...s, title } : s
      ))

      console.log(`[useChatSessions] Updated session ${sessionId} title: ${title}`)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      console.error('[useChatSessions] Failed to update session title:', err)
      return false
    }
  }, [])

  /**
   * 세션 삭제
   */
  const deleteSession = useCallback(async (sessionId: string, hardDelete: boolean = false): Promise<boolean> => {
    try {
      setError(null)

      const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}?hard_delete=${hardDelete}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error(`Failed to delete session: ${response.statusText}`)
      }

      const data: DeleteSessionResponse = await response.json()

      // 로컬 상태 업데이트 (id 필드 사용)
      setSessions(prev => prev.filter(s => s.id !== sessionId))

      // 현재 세션이 삭제되면 다른 세션으로 전환
      if (currentSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId)
        if (remainingSessions.length > 0) {
          setCurrentSessionId(remainingSessions[0].id)
        } else {
          setCurrentSessionId(null)
        }
      }

      console.log(`[useChatSessions] Deleted session: ${sessionId} at ${data.deleted_at}`)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      console.error('[useChatSessions] Failed to delete session:', err)
      return false
    }
  }, [currentSessionId, sessions])

  /**
   * 초기 로드
   */
  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  return {
    // 상태
    sessions,
    currentSessionId,
    loading,
    error,

    // 메서드
    createSession,
    switchSession,
    updateSessionTitle,
    deleteSession,
    refreshSessions: fetchSessions
  }
}
