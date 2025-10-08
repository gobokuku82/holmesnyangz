import { useState, useEffect } from "react"
import { chatAPI } from "@/lib/api"
import type { SessionStartResponse } from "@/types/chat"

const SESSION_STORAGE_KEY = "holmes_session_id"

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 세션 초기화
  useEffect(() => {
    initSession()
  }, [])

  const initSession = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // 1. sessionStorage에서 기존 세션 확인
      const storedSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY)

      if (storedSessionId) {
        // 2. 세션 유효성 검증
        try {
          await chatAPI.getSessionInfo(storedSessionId)
          setSessionId(storedSessionId)
          setIsLoading(false)
          return
        } catch {
          // 만료된 세션 - 삭제하고 새로 생성
          sessionStorage.removeItem(SESSION_STORAGE_KEY)
        }
      }

      // 3. 새 세션 생성
      const response = await chatAPI.startSession({
        metadata: {
          device: "web_browser",
          user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
        },
      })

      setSessionId(response.session_id)
      sessionStorage.setItem(SESSION_STORAGE_KEY, response.session_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to initialize session")
    } finally {
      setIsLoading(false)
    }
  }

  // 세션 재생성
  const resetSession = async () => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    await initSession()
  }

  return {
    sessionId,
    isLoading,
    error,
    resetSession,
  }
}
