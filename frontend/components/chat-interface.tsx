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

interface Message {
  id: string
  type: "user" | "bot" | "agent-popup"
  content: string
  timestamp: Date
  agentType?: PageType
  isProcessing?: boolean
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
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingAgent, setProcessingAgent] = useState<PageType | null>(null)
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
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
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
    setIsProcessing(true)

    // Detect agent type for loading animation
    const agentType = detectAgentType(content)
    setProcessingAgent(agentType)

    try {
      // 실제 API 호출
      const response = await chatAPI.sendMessage({
        query: content,
        session_id: sessionId,
        enable_checkpointing: true,
      })

      // Agent 타입 감지 (응답 기반)
      const responseAgentType = detectAgentTypeFromResponse(response)

      // 봇 응답 추가
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: response.response.answer,
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
    } catch (error) {
      // 에러 메시지 표시
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsProcessing(false)
      setProcessingAgent(null)
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

  const getAgentSpinner = (agentType: PageType) => {
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
      {isProcessing && (
        <div className="absolute inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 shadow-lg flex flex-col items-center gap-4">
            {processingAgent && getAgentSpinner(processingAgent) ? (
              <video autoPlay loop muted className="w-48 h-48 object-cover rounded-lg">
                <source src={getAgentSpinner(processingAgent)!} type="video/mp4" />
              </video>
            ) : (
              <div className="w-24 h-24 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            )}
            <p className="text-sm text-muted-foreground text-center">
              {processingAgent === "analysis" && "분석 에이전트가 처리 중입니다..."}
              {processingAgent === "verification" && "검증 에이전트가 처리 중입니다..."}
              {processingAgent === "consultation" && "상담 에이전트가 처리 중입니다..."}
              {!processingAgent && "에이전트가 처리 중입니다..."}
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="border-b border-border p-4">
        <h2 className="text-xl font-semibold text-foreground">부동산 챗봇</h2>
        <p className="text-sm text-muted-foreground">AI 에이전트와 대화하며 부동산 관련 도움을 받으세요</p>
      </div>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
              {message.type === "agent-popup" ? (
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
              disabled={isProcessing}
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
            disabled={isProcessing}
            className="flex-1"
          />
          <Button
            onClick={() => handleSendMessage(inputValue)}
            disabled={isProcessing || !inputValue.trim()}
            size="icon"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
