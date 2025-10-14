"use client"

import { useState, useEffect } from "react"
import { Clock, MessageSquare, Loader2, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

interface ConversationMemory {
  id: string
  query: string
  response_summary: string
  relevance: string
  intent_detected: string
  created_at: string
  conversation_metadata?: {
    teams_used?: string[]
    response_time?: number
    confidence?: number
  }
}

interface MemoryHistoryProps {
  isCollapsed?: boolean
  onLoadMemory: ((memory: ConversationMemory) => void) | null
}

export function MemoryHistory({ isCollapsed = false, onLoadMemory }: MemoryHistoryProps) {
  const [memories, setMemories] = useState<ConversationMemory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(true)

  const fetchMemories = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat/memory/history?limit=5")

      if (!response.ok) {
        throw new Error("Failed to fetch memory history")
      }

      const data = await response.json()
      setMemories(data.memories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
      console.error("Failed to fetch memory history:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isCollapsed) {
      fetchMemories()
    }
  }, [isCollapsed])

  // 사이드바가 접혀있으면 아이콘만 표시
  if (isCollapsed) {
    return (
      <div className="p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center p-2"
          onClick={fetchMemories}
          title="최근 대화"
        >
          <Clock className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="border-t border-sidebar-border">
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-between p-4 hover:bg-sidebar-accent"
        >
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-sidebar-foreground/70" />
            <span className="text-sm font-medium text-sidebar-foreground">최근 대화</span>
          </div>
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-sidebar-foreground/70" />
          ) : (
            <ChevronDown className="h-4 w-4 text-sidebar-foreground/70" />
          )}
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="px-4 pb-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-sidebar-foreground/50" />
            </div>
          ) : error ? (
            <div className="text-xs text-destructive py-4 text-center">
              {error}
            </div>
          ) : memories.length === 0 ? (
            <div className="text-xs text-sidebar-foreground/50 py-4 text-center">
              대화 기록이 없습니다
            </div>
          ) : (
            <ScrollArea className="h-[200px]">
              <div className="space-y-3">
                {memories.map((memory) => (
                  <div
                    key={memory.id}
                    onClick={() => {
                      if (onLoadMemory) {
                        onLoadMemory(memory)
                        console.log('[MemoryHistory] Loaded conversation:', memory.id)
                      }
                    }}
                    className="rounded-lg border border-sidebar-border bg-sidebar-accent/50 p-3 hover:bg-sidebar-accent hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
                  >
                    <div className="flex items-start gap-2">
                      <MessageSquare className="h-3 w-3 text-sidebar-primary mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-sidebar-foreground line-clamp-2">
                          {memory.query}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className="text-[10px] text-sidebar-foreground/50">
                            {new Date(memory.created_at).toLocaleString("ko-KR", {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          {memory.intent_detected && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-sidebar-primary/10 text-sidebar-primary">
                              {memory.intent_detected}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-3 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground"
            onClick={fetchMemories}
          >
            목록 갱신
          </Button>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
