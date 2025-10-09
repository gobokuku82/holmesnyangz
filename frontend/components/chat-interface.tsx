"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Bot, User, Maximize2 } from "lucide-react"
import type { PageType } from "@/app/page"
import { useSession } from "@/hooks/use-session"
import { ChatWSClient, createWSClient, type WSMessage } from "@/lib/ws"
import type { ExecutionStepState } from "@/lib/types"
import { ExecutionPlanPage } from "@/components/execution-plan-page"
import { ExecutionProgressPage } from "@/components/execution-progress-page"
import type { ProcessState, AgentType } from "@/types/process"
import type { ExecutionPlan, ExecutionStep } from "@/types/execution"
import { STEP_MESSAGES } from "@/types/process"

interface Message {
  id: string
  type: "user" | "bot" | "agent-popup" | "execution-plan" | "execution-progress"
  content: string
  timestamp: Date
  agentType?: PageType
  isProcessing?: boolean
  executionPlan?: ExecutionPlan
  executionSteps?: ExecutionStep[]
}

interface ChatInterfaceProps {
  onSplitView: (agentType: PageType) => void
}

export function ChatInterface({ onSplitView }: ChatInterfaceProps) {
  const { sessionId, isLoading: sessionLoading, error: sessionError, resetSession } = useSession()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content: "안녕하세요! 도와줘 홈즈냥즈입니다. 안전한 부동산 거래를 위해 어떤 도움이 필요하신가요?",
      timestamp: new Date(),
    },
  ])
  const [inputValue, setInputValue] = useState("")
  const [processState, setProcessState] = useState<ProcessState>({
    step: "idle",
    agentType: null,
    message: ""
  })
  const [todos, setTodos] = useState<ExecutionStepState[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const wsClientRef = useRef<ChatWSClient | null>(null)

  const exampleQuestions = [
    "계약서를 분석해주세요",
    "이 매물이 허위매물인지 확인해주세요",
    "전세사기 위험도를 평가해주세요",
    "강남구 아파트 추천해주세요",
    "정부 지원 정책을 알려주세요",
  ]

  // WebSocket 초기화
  useEffect(() => {
    if (!sessionId) return

    const wsClient = createWSClient({
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
      sessionId,
      onMessage: handleWSMessage,
      onConnected: () => {
        console.log('[ChatInterface] WebSocket connected')
        setWsConnected(true)
      },
      onDisconnected: () => {
        console.log('[ChatInterface] WebSocket disconnected')
        setWsConnected(false)
      },
      onError: (error) => {
        console.error('[ChatInterface] WebSocket error:', error)
      }
    })

    wsClient.connect()
    wsClientRef.current = wsClient

    return () => {
      wsClient.disconnect()
      wsClientRef.current = null
    }
  }, [sessionId])

  // 스크롤 자동 이동
  useEffect(() => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [messages])

  // WebSocket 메시지 핸들러
  const handleWSMessage = (message: WSMessage) => {
    console.log('[ChatInterface] Received WS message:', message.type)

    switch (message.type) {
      case 'connected':
        // 연결 확인 - 아무것도 하지 않음
        break

      case 'plan_ready':
        // 실행 계획 수신
        if (message.plan && message.todos) {
          const planMessage: Message = {
            id: `execution-plan-${Date.now()}`,
            type: "execution-plan",
            content: "",
            timestamp: new Date(),
            executionPlan: {
              intent: message.plan.intent || "unknown",
              confidence: message.plan.confidence || 0,
              execution_steps: message.todos,
              execution_strategy: message.plan.execution_strategy || "sequential",
              estimated_total_time: message.plan.estimated_total_time || 5
            }
          }
          setMessages((prev) => [...prev, planMessage])
          setTodos(message.todos)
        }
        break

      case 'todo_created':
      case 'todo_updated':
        // TODO 리스트 업데이트
        if (message.todos) {
          setTodos(message.todos)
        } else if (message.todo) {
          setTodos((prev) =>
            prev.map((t) => (t.step_id === message.todo.step_id ? message.todo : t))
          )
        }
        break

      case 'step_start':
        setProcessState({
          step: "executing",
          agentType: message.agent as AgentType,
          message: `${message.task} 실행 중...`
        })
        break

      case 'step_progress':
        // Progress 업데이트 (TODO 리스트에 반영됨)
        break

      case 'step_complete':
        // Step 완료
        break

      case 'final_response':
        // 최종 응답 수신
        setProcessState({
          step: "complete",
          agentType: null,
          message: STEP_MESSAGES.complete
        })

        // Execution Progress 메시지 제거
        setMessages((prev) => prev.filter(m =>
          m.type !== "execution-plan" && m.type !== "execution-progress"
        ))

        // 봇 응답 추가
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: "bot",
          content: message.response?.content || message.response?.answer || "응답을 받지 못했습니다.",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, botMessage])
        setTodos([])
        break

      case 'error':
        console.error('[ChatInterface] Error from server:', message.error)
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
        setMessages((prev) => [...prev, {
          id: Date.now().toString(),
          type: "bot",
          content: `오류가 발생했습니다: ${message.error}`,
          timestamp: new Date()
        }])
        break
    }
  }

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !sessionId || !wsClientRef.current) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputValue("")

    // Detect agent type for loading animation
    const agentType = detectAgentType(content) as AgentType | null

    // 프로세스 시작
    setProcessState({
      step: "planning",
      agentType,
      message: STEP_MESSAGES.planning,
      startTime: Date.now()
    })

    // WebSocket으로 쿼리 전송
    wsClientRef.current.send({
      type: "query",
      query: content,
      enable_checkpointing: true
    })

    // 나머지 처리는 handleWSMessage에서 실시간으로 처리됨
  }

  // Helper: Agent 타입 감지 (클라이언트 측 추론)
  const detectAgentType = (content: string): PageType | null => {
    const analysisKeywords = ["계약서", "분석", "등기부등본", "건축물대장"]
    const verificationKeywords = ["허위매물", "전세사기", "위험도", "검증", "신용도"]
    const consultationKeywords = ["추천", "매물", "정책", "지원", "상담", "절차"]

    if (analysisKeywords.some((keyword) => content.includes(keyword))) {
      return "analysis"
    }
    if (verificationKeywords.some((keyword) => content.includes(keyword))) {
      return "verification"
    }
    if (consultationKeywords.some((keyword) => content.includes(keyword))) {
      return "consultation"
    }

    return null
  }

  const handleExampleClick = (question: string) => {
    handleSendMessage(question)
  }

  const handleMaximize = (agentType: PageType) => {
    onSplitView(agentType)
  }

  // 세션 로딩 중
  if (sessionLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-muted-foreground">세션을 초기화하는 중...</p>
        </div>
      </div>
    )
  }

  // 세션 에러
  if (sessionError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-destructive">
          <p className="font-semibold mb-2">세션 생성 실패</p>
          <p className="text-sm">{sessionError}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-background">
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.map((message) => (
            <div key={message.id} className="space-y-2">
              {message.type === "execution-plan" && message.executionPlan && (
                <ExecutionPlanPage plan={message.executionPlan} />
              )}
              {message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
                <ExecutionProgressPage
                  steps={message.executionSteps}
                  plan={message.executionPlan}
                  processState={processState}
                />
              )}
              {(message.type === "user" || message.type === "bot") && (
                <div className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-2 max-w-[80%] ${message.type === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.type === "user" ? "bg-primary" : "bg-secondary"}`}>
                      {message.type === "user" ? <User className="h-4 w-4 text-primary-foreground" /> : <Bot className="h-4 w-4" />}
                    </div>
                    <Card className={`p-3 ${message.type === "user" ? "bg-primary text-primary-foreground" : ""}`}>
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </Card>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Example Questions */}
      <div className="border-t border-border p-4">
        <p className="text-sm text-muted-foreground mb-3">예시 질문:</p>
        <div className="flex flex-wrap gap-2 mb-4">
          {exampleQuestions.map((question, index) => (
            <Button
              key={index}
              variant="outline"
              size="sm"
              onClick={() => handleExampleClick(question)}
              className="text-xs"
              disabled={processState.step !== "idle"}
            >
              {question}
            </Button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="메시지를 입력하세요..."
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage(inputValue)}
            disabled={processState.step !== "idle"}
            className="flex-1"
          />
          <Button
            onClick={() => handleSendMessage(inputValue)}
            disabled={processState.step !== "idle" || !inputValue.trim()}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
// DEPRECATED CODE REMOVED - WebSocket으로 완전 전환됨
