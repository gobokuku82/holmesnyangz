"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Bot, User, Maximize2 } from "lucide-react"
import type { PageType } from "@/app/page"
import { useSession } from "@/hooks/use-session"
import { chatAPI } from "@/lib/api"
import type { ChatResponse } from "@/types/chat"
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
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  const exampleQuestions = [
    "계약서를 분석해주세요",
    "이 매물이 허위매물인지 확인해주세요",
    "전세사기 위험도를 평가해주세요",
    "강남구 아파트 추천해주세요",
    "정부 지원 정책을 알려주세요",
  ]

  useEffect(() => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    }
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !sessionId) return

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

    const startTime = Date.now()

    // 프로세스 시작
    setProcessState({
      step: "planning",
      agentType,
      message: STEP_MESSAGES.planning,
      startTime
    })

    try {
      // 실제 API 호출
      const response = await chatAPI.sendMessage({
        query: content,
        session_id: sessionId,
        enable_checkpointing: true,
      })

      // ⚡ IRRELEVANT/UNCLEAR는 새 페이지 표시 안함 (즉시 응답)
      const isGuidanceResponse = response.response.type === "guidance"

      if (!isGuidanceResponse && response.planning_info) {
        // Page 1: 실행 계획 표시
        if (response.planning_info.execution_steps && response.planning_info.execution_steps.length > 0) {
          const planMessage: Message = {
            id: `execution-plan-${Date.now()}`,
            type: "execution-plan",
            content: "",
            timestamp: new Date(),
            executionPlan: {
              intent: response.planning_info.intent || "unknown",
              confidence: response.planning_info.confidence || 0,
              execution_steps: response.planning_info.execution_steps,
              execution_strategy: response.planning_info.execution_strategy || "sequential",
              estimated_total_time: response.planning_info.estimated_total_time || 5
            }
          }
          setMessages((prev) => [...prev, planMessage])

          // 짧은 딜레이 후 Page 2로 전환
          setTimeout(() => {
            // Page 2: 작업 실행 중 표시
            const progressMessage: Message = {
              id: `execution-progress-${Date.now()}`,
              type: "execution-progress",
              content: "",
              timestamp: new Date(),
              executionSteps: response.planning_info!.execution_steps,
              executionPlan: {
                intent: response.planning_info!.intent || "unknown",
                confidence: response.planning_info!.confidence || 0,
                execution_steps: response.planning_info!.execution_steps!,
                execution_strategy: response.planning_info!.execution_strategy || "sequential",
                estimated_total_time: response.planning_info!.estimated_total_time || 5
              }
            }

            // 계획 메시지 제거하고 진행 중 메시지 추가
            setMessages((prev) =>
              prev.filter(m => m.type !== "execution-plan").concat(progressMessage)
            )
          }, 800) // 계획 표시 800ms
        }
      }

      // Agent 타입 감지 (응답 기반)
      const responseAgentType = detectAgentTypeFromResponse(response)

      // ⚡ IRRELEVANT/UNCLEAR는 딜레이 없이 즉시 완료 (성능 최적화)
      const completionDelay = isGuidanceResponse ? 100 : 500

      // 완료 상태로 변경
      setTimeout(() => {
        setProcessState({
          step: "complete",
          agentType: agentType,
          message: STEP_MESSAGES.complete
        })

        // Execution Progress 메시지 제거
        setMessages((prev) => prev.filter(m =>
          m.type !== "execution-plan" && m.type !== "execution-progress"
        ))
      }, completionDelay)

      // 봇 응답 추가
      // IRRELEVANT/UNCLEAR 응답은 message 필드 사용, 일반 응답은 answer 필드 사용
      const responseContent = response.response.type === "guidance"
        ? response.response.message
        : response.response.answer || response.response.message || "응답을 받지 못했습니다.";

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: responseContent,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, botMessage])

      // Agent 팝업 표시 (필요시)
      if (responseAgentType && response.teams_executed.length > 0) {
        const agentPopup: Message = {
          id: (Date.now() + 2).toString(),
          type: "agent-popup",
          content: getAgentResponseFromAPI(responseAgentType, response),
          timestamp: new Date(),
          agentType: responseAgentType,
        }
        setMessages((prev) => [...prev, agentPopup])
      }

      // ⚡ IRRELEVANT/UNCLEAR는 빠르게 idle 복귀 (성능 최적화)
      const idleDelay = isGuidanceResponse ? 300 : 1500

      setTimeout(() => {
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
      }, idleDelay)

    } catch (error) {
      // 에러 상태로 변경
      setProcessState({
        step: "error",
        agentType: agentType,
        message: "오류가 발생했습니다",
        error: error instanceof Error ? error.message : "알 수 없는 오류"
      })

      // Execution Plan/Progress 메시지 제거
      setMessages((prev) => prev.filter(m =>
        m.type !== "execution-plan" && m.type !== "execution-progress"
      ))

      // 세션 만료 처리 (401 또는 404)
      if (error instanceof Error && (error.message.includes("401") || error.message.includes("404") || error.message.includes("session"))) {
        console.warn("⚠️ Session expired during message send, resetting session...")
        await resetSession()

        const retryMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: "bot",
          content: "세션이 만료되어 새로 고침합니다. 잠시 후 다시 시도해주세요.",
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, retryMessage])
      } else {
        // 일반 에러 메시지 표시
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: "bot",
          content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMessage])
      }

      // 3초 후 idle로 복귀
      setTimeout(() => {
        setProcessState({
          step: "idle",
          agentType: null,
          message: ""
        })
      }, 3000)
    }
  }

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

  const detectAgentTypeFromResponse = (response: ChatResponse): PageType | null => {
    const teams = response.teams_executed

    if (teams.includes("analysis_team")) return "analysis"
    if (teams.includes("search_team")) return "verification"
    if (teams.includes("document_team")) return "consultation"

    return null
  }

  const getAgentResponseFromAPI = (agentType: PageType, response: ChatResponse): string => {
    const executionTime = response.execution_time_ms || 0
    const teamCount = response.teams_executed.length

    switch (agentType) {
      case "analysis":
        return `분석 에이전트가 ${teamCount}개 팀을 사용하여 ${executionTime}ms 동안 처리했습니다.`
      case "verification":
        return `검증 에이전트가 처리를 완료했습니다. ${response.search_results?.length || 0}개의 결과를 찾았습니다.`
      case "consultation":
        return `상담 에이전트가 처리를 완료했습니다. 처리 시간: ${executionTime}ms`
      default:
        return `처리가 완료되었습니다.`
    }
  }

  const getAgentColors = (agentType: PageType) => {
    switch (agentType) {
      case "analysis":
        return {
          bg: "bg-blue-50 border-blue-200",
          icon: "bg-blue-500 text-white",
          button: "border-blue-300 hover:bg-blue-50",
        }
      case "verification":
        return {
          bg: "bg-red-50 border-red-200",
          icon: "bg-red-500 text-white",
          button: "border-red-300 hover:bg-red-50",
        }
      case "consultation":
        return {
          bg: "bg-green-50 border-green-200",
          icon: "bg-green-500 text-white",
          button: "border-green-300 hover:bg-green-50",
        }
      default:
        return {
          bg: "bg-accent/10 border-accent",
          icon: "bg-accent text-accent-foreground",
          button: "border-accent hover:bg-accent/10",
        }
    }
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
        <div className="text-center">
          <p className="text-sm text-destructive mb-4">{sessionError}</p>
          <Button onClick={resetSession}>다시 시도</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-background relative">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h2 className="text-xl font-semibold text-foreground">부동산 챗봇</h2>
        <p className="text-sm text-muted-foreground">AI 에이전트와 대화하며 부동산 관련 도움을 받으세요</p>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id}>
              {/* Execution Plan 메시지 타입 처리 */}
              {message.type === "execution-plan" && message.executionPlan ? (
                <ExecutionPlanPage plan={message.executionPlan} />
              ) : message.type === "execution-progress" && message.executionSteps && message.executionPlan ? (
                <ExecutionProgressPage
                  steps={message.executionSteps}
                  estimatedTime={message.executionPlan.estimated_total_time}
                  startTime={processState.startTime}
                />
              ) : message.type === "agent-popup" ? (
                <Card
                  className={`max-w-md p-4 ${message.agentType ? getAgentColors(message.agentType).bg : "bg-accent/10 border-accent"}`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`rounded-full p-2 ${message.agentType ? getAgentColors(message.agentType).icon : "bg-accent text-accent-foreground"}`}
                    >
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-foreground">{message.content}</p>
                      <div className="mt-3 flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => message.agentType && handleMaximize(message.agentType)}
                          className={`text-xs ${message.agentType ? getAgentColors(message.agentType).button : ""}`}
                        >
                          <Maximize2 className="h-3 w-3 mr-1" />
                          에이전트 사용하기
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ) : (
                <div className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`flex items-start gap-3 max-w-md ${message.type === "user" ? "flex-row-reverse" : ""}`}>
                    <div
                      className={`rounded-full p-2 ${
                        message.type === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {message.type === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </div>
                    <Card className={`p-3 ${message.type === "user" ? "bg-primary text-primary-foreground" : "bg-card"}`}>
                      <p className="text-sm">{message.content}</p>
                      <p className="text-xs opacity-70 mt-1">
                        {message.timestamp.toLocaleTimeString("ko-KR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
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
