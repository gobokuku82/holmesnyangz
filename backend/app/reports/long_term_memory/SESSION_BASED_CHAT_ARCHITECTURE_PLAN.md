# Session-Based Chat Architecture Implementation Plan

## 📋 문서 정보

- **작성일**: 2025-10-14
- **버전**: 1.0
- **목적**: 세션 기반 채팅 아키텍처 구현 계획
- **작성자**: Claude Code

---

## 🔍 현재 시스템 문제 분석

### 1. 근본적인 문제점

#### 1.1 세션 개념 부재 ❌

**현재 구조**:
```typescript
// ChatInterface.tsx
const [messages, setMessages] = useState<Message[]>([...]) // 단일 배열
const STORAGE_KEY = 'chat-messages' // 모든 대화가 하나의 키에 저장
```

**문제점**:
- ❌ 모든 대화가 하나의 배열에 섞임
- ❌ Memory 클릭 시 기존 대화 끝에 추가됨 (덮어쓰기 아님)
- ❌ 새 대화를 시작할 방법이 없음
- ❌ 대화 기록 관리 불가 (삭제, 전환 등)
- ❌ WebSocket sessionId와 UI가 연동 안됨

**증상**:
- 같은 질문이 여러 번 중복 표시
- Memory History 클릭 시 현재 대화에 계속 추가
- 브라우저 새로고침 시 모든 대화가 하나로 표시

#### 1.2 Memory History 용도 혼동 ❌

**현재 구조**:
```typescript
// memory-history.tsx
onClick={() => onLoadMemory(memory)} // 현재 대화에 추가
```

**문제점**:
- ❌ Memory History는 PostgreSQL 저장된 과거 대화 조회용
- ❌ 현재는 클릭 시 현재 채팅창에 추가되어 혼란
- ❌ Memory와 현재 세션의 구분이 없음

**올바른 동작**:
- ✅ Memory 클릭 → 별도 뷰어에서 보기 (읽기 전용)
- ✅ 또는 → 새 세션으로 가져오기 (명시적 액션)

#### 1.3 localStorage 구조 문제 ❌

**현재 구조**:
```typescript
localStorage.setItem('chat-messages', JSON.stringify(messages))
// 모든 세션이 하나의 키에 섞여 저장
```

**문제점**:
- ❌ 세션 구분 불가
- ❌ 세션별 관리 불가 (삭제, 제목 변경 등)
- ❌ 데이터 구조 확장 불가

---

## 🎯 새로운 아키텍처 설계

### 1. 세션 기반 채팅 시스템

#### 1.1 핵심 개념

```
┌─────────────────────────────────────────────────────────────┐
│                     Session-Based Chat                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Session 1 (민간임대주택 상담)                              │
│  ├─ Message 1: "민간임대주택에서의 수리 의무는?"            │
│  ├─ Message 2: "민간임대주택에서의 수리 의무는..."         │
│  └─ Message 3: "추가로 질문있습니다"                        │
│                                                             │
│  Session 2 (관리비 납부 문의)                               │
│  ├─ Message 1: "관리비의 부과 대상과 납부 의무자는?"        │
│  └─ Message 2: "관리비의 부과 대상은..."                    │
│                                                             │
│  Session 3 (전세 계약 질문)                                 │
│  └─ Message 1: "전세 계약 시 주의사항은?"                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**특징**:
- 각 세션은 독립적인 대화 스레드
- 세션 간 전환 가능
- 세션별 제목, 생성일, 수정일 관리
- 세션별 localStorage 저장

#### 1.2 데이터 구조 정의

```typescript
// types/session.ts

/**
 * 채팅 세션
 * 하나의 대화 스레드를 나타냄
 */
interface ChatSession {
  sessionId: string              // UUID (WebSocket sessionId와 동일)
  title: string                  // 세션 제목 (첫 질문에서 추출 또는 수동 설정)
  messages: Message[]            // 이 세션의 메시지 목록
  createdAt: string             // ISO 8601 형식
  updatedAt: string             // ISO 8601 형식
  isReadOnly?: boolean          // 읽기 전용 여부 (Memory에서 가져온 경우)
  metadata?: {
    source?: 'new' | 'memory'   // 세션 출처
    memoryId?: string           // Memory에서 가져온 경우 원본 ID
    messageCount?: number       // 메시지 개수
  }
}

/**
 * 세션 목록 메타데이터
 * localStorage에 저장되는 세션 목록
 */
interface SessionList {
  sessions: Array<{
    sessionId: string
    title: string
    lastMessage: string         // 마지막 메시지 미리보기
    updatedAt: string
  }>
  currentSessionId: string | null
}
```

#### 1.3 localStorage 구조

```typescript
// localStorage 키 구조
{
  // 세션 목록 (가볍게)
  "chat-session-list": {
    sessions: [
      { sessionId: "session-123", title: "민간임대주택 상담", lastMessage: "감사합니다", updatedAt: "2025-10-14T16:49:15" },
      { sessionId: "session-456", title: "관리비 납부 문의", lastMessage: "추가 질문이...", updatedAt: "2025-10-14T15:30:00" }
    ],
    currentSessionId: "session-123"
  },

  // 세션별 상세 데이터 (무거움)
  "chat-session-123": {
    sessionId: "session-123",
    title: "민간임대주택 상담",
    messages: [ /* Message[] */ ],
    createdAt: "2025-10-14T16:48:00",
    updatedAt: "2025-10-14T16:49:15"
  },

  "chat-session-456": {
    sessionId: "session-456",
    title: "관리비 납부 문의",
    messages: [ /* Message[] */ ],
    createdAt: "2025-10-14T15:30:00",
    updatedAt: "2025-10-14T15:35:00"
  }
}
```

**장점**:
- ✅ 세션 목록은 가볍게 (빠른 로딩)
- ✅ 세션 상세는 필요할 때만 로드 (지연 로딩)
- ✅ 세션별 독립 관리 가능
- ✅ 용량 관리 용이 (오래된 세션 삭제)

---

## 🏗️ 구현 계획

### Phase 1: 세션 관리 시스템 구축 (핵심)

#### 1.1 타입 정의

**파일**: `frontend/types/session.ts` (신규 생성)

```typescript
/**
 * 채팅 세션 타입 정의
 */

import type { Message } from '@/components/chat-interface'

export interface ChatSession {
  sessionId: string
  title: string
  messages: Message[]
  createdAt: string
  updatedAt: string
  isReadOnly?: boolean
  metadata?: {
    source?: 'new' | 'memory'
    memoryId?: string
    messageCount?: number
  }
}

export interface SessionListItem {
  sessionId: string
  title: string
  lastMessage: string
  updatedAt: string
}

export interface SessionList {
  sessions: SessionListItem[]
  currentSessionId: string | null
}
```

#### 1.2 세션 관리 Hook

**파일**: `frontend/hooks/use-chat-sessions.ts` (신규 생성)

**기능**:
```typescript
export function useChatSessions() {
  // State
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  // 세션 생성
  const createSession = (title?: string): string => {
    const sessionId = `session-${uuid()}`
    const newSession: SessionListItem = {
      sessionId,
      title: title || "새 대화",
      lastMessage: "",
      updatedAt: new Date().toISOString()
    }

    // 세션 목록에 추가
    setSessions(prev => [newSession, ...prev])

    // 빈 세션 상세 저장
    const fullSession: ChatSession = {
      sessionId,
      title: title || "새 대화",
      messages: [welcomeMessage],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    saveSessionToStorage(fullSession)

    // 현재 세션으로 설정
    setCurrentSessionId(sessionId)

    return sessionId
  }

  // 세션 전환
  const switchSession = (sessionId: string) => {
    setCurrentSessionId(sessionId)
  }

  // 세션 삭제
  const deleteSession = (sessionId: string) => {
    setSessions(prev => prev.filter(s => s.sessionId !== sessionId))
    removeSessionFromStorage(sessionId)

    // 현재 세션이 삭제되면 다른 세션으로 전환
    if (currentSessionId === sessionId) {
      const remaining = sessions.filter(s => s.sessionId !== sessionId)
      setCurrentSessionId(remaining[0]?.sessionId || null)
    }
  }

  // 세션 제목 업데이트
  const updateSessionTitle = (sessionId: string, title: string) => {
    setSessions(prev => prev.map(s =>
      s.sessionId === sessionId ? { ...s, title } : s
    ))

    // 상세 데이터도 업데이트
    const fullSession = loadSessionFromStorage(sessionId)
    if (fullSession) {
      fullSession.title = title
      saveSessionToStorage(fullSession)
    }
  }

  // localStorage 동기화
  useEffect(() => {
    const sessionList: SessionList = {
      sessions,
      currentSessionId
    }
    localStorage.setItem('chat-session-list', JSON.stringify(sessionList))
  }, [sessions, currentSessionId])

  // 초기 로드
  useEffect(() => {
    const saved = localStorage.getItem('chat-session-list')
    if (saved) {
      const { sessions: savedSessions, currentSessionId: savedCurrent } = JSON.parse(saved)
      setSessions(savedSessions)
      setCurrentSessionId(savedCurrent)
    } else {
      // 첫 실행: 기본 세션 생성
      createSession()
    }
  }, [])

  return {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    deleteSession,
    updateSessionTitle
  }
}
```

**Helper Functions**:
```typescript
// utils/session-storage.ts
export function saveSessionToStorage(session: ChatSession) {
  const key = `chat-session-${session.sessionId}`
  localStorage.setItem(key, JSON.stringify(session))
}

export function loadSessionFromStorage(sessionId: string): ChatSession | null {
  const key = `chat-session-${sessionId}`
  const saved = localStorage.getItem(key)
  if (saved) {
    const session = JSON.parse(saved)
    // Date 객체 복원
    session.messages = session.messages.map(m => ({
      ...m,
      timestamp: new Date(m.timestamp)
    }))
    return session
  }
  return null
}

export function removeSessionFromStorage(sessionId: string) {
  const key = `chat-session-${sessionId}`
  localStorage.removeItem(key)
}

export function generateSessionTitle(firstMessage: string): string {
  // 첫 메시지에서 제목 추출 (최대 30자)
  return firstMessage.length > 30
    ? firstMessage.slice(0, 30) + '...'
    : firstMessage
}
```

#### 1.3 ChatInterface 리팩토링

**파일**: `frontend/components/chat-interface.tsx` (수정)

**변경 사항**:
```typescript
interface ChatInterfaceProps {
  sessionId: string  // 세션 ID를 prop으로 받음
  onSplitView: (agentType: PageType) => void
  onRegisterMemoryLoader?: (loader: (memory: ConversationMemory) => void) => void
  onSessionTitleUpdate?: (sessionId: string, title: string) => void  // 제목 업데이트 콜백
}

export function ChatInterface({
  sessionId,
  onSplitView,
  onRegisterMemoryLoader,
  onSessionTitleUpdate
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])

  // 세션 변경 시 메시지 로드
  useEffect(() => {
    const session = loadSessionFromStorage(sessionId)
    if (session) {
      setMessages(session.messages)
      console.log(`[ChatInterface] Loaded session ${sessionId} with ${session.messages.length} messages`)
    } else {
      // 새 세션: 환영 메시지만
      setMessages([welcomeMessage])
    }
  }, [sessionId])

  // 메시지 변경 시 세션에 저장
  useEffect(() => {
    if (messages.length === 0) return

    const session = loadSessionFromStorage(sessionId)
    if (session) {
      session.messages = messages
      session.updatedAt = new Date().toISOString()
      saveSessionToStorage(session)

      // 첫 메시지로 제목 자동 생성
      if (messages.length === 2 && session.title === "새 대화") {
        const firstUserMessage = messages.find(m => m.type === 'user')
        if (firstUserMessage) {
          const newTitle = generateSessionTitle(firstUserMessage.content)
          session.title = newTitle
          saveSessionToStorage(session)
          onSessionTitleUpdate?.(sessionId, newTitle)
        }
      }
    }
  }, [messages, sessionId])

  // 기존 코드 유지...
}
```

**제거할 코드**:
```typescript
// ❌ 제거: 단일 localStorage 저장
useEffect(() => {
  localStorage.setItem('chat-messages', JSON.stringify(messages))
}, [messages])

// ❌ 제거: 단일 localStorage 복원
useEffect(() => {
  const saved = localStorage.getItem('chat-messages')
  if (saved) {
    setMessages(JSON.parse(saved))
  }
}, [])
```

---

### Phase 2: UI 개선 - Sidebar 리팩토링

#### 2.1 새 채팅 버튼

**파일**: `frontend/components/sidebar.tsx` (수정)

**위치**: 헤더 바로 아래

```typescript
{/* 새 채팅 버튼 */}
<div className="p-4">
  <Button
    variant="default"
    className="w-full"
    onClick={onCreateNewSession}
  >
    <Plus className="h-4 w-4 mr-2" />
    새 채팅
  </Button>
</div>
```

#### 2.2 세션 목록 컴포넌트

**파일**: `frontend/components/session-list.tsx` (신규 생성)

**기능**:
```typescript
interface SessionListProps {
  sessions: SessionListItem[]
  currentSessionId: string | null
  onSessionClick: (sessionId: string) => void
  onSessionDelete: (sessionId: string) => void
  onSessionRename: (sessionId: string, newTitle: string) => void
}

export function SessionList({
  sessions,
  currentSessionId,
  onSessionClick,
  onSessionDelete,
  onSessionRename
}: SessionListProps) {
  return (
    <div className="space-y-1">
      {sessions.map((session) => (
        <div
          key={session.sessionId}
          className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
            session.sessionId === currentSessionId
              ? 'bg-sidebar-primary text-sidebar-primary-foreground'
              : 'hover:bg-sidebar-accent'
          }`}
          onClick={() => onSessionClick(session.sessionId)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {session.title}
              </p>
              <p className="text-xs opacity-70 truncate">
                {session.lastMessage}
              </p>
              <p className="text-xs opacity-50 mt-1">
                {formatDistanceToNow(new Date(session.updatedAt), { locale: ko })}
              </p>
            </div>

            {/* 액션 버튼 (hover 시 표시) */}
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => {
                  e.stopPropagation()
                  // 이름 변경 다이얼로그
                }}
              >
                <Pencil className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-destructive"
                onClick={(e) => {
                  e.stopPropagation()
                  onSessionDelete(session.sessionId)
                }}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
```

**특징**:
- 현재 세션 하이라이트
- hover 시 수정/삭제 버튼 표시
- 마지막 메시지 미리보기
- 상대 시간 표시 ("5분 전", "2시간 전")

#### 2.3 Sidebar 레이아웃

**새로운 구조**:
```
┌─────────────────────────┐
│ 🏠 도와줘 홈즈냥즈       │ ← Header
│ [접기/펴기 버튼]         │
├─────────────────────────┤
│ [+ 새 채팅]             │ ← NEW! 새 세션 버튼
├─────────────────────────┤
│ 📝 내 채팅               │ ← NEW! 세션 목록
│ ┌─────────────────────┐ │
│ │ 민간임대주택 상담 ✓  │ │   (현재 세션)
│ │ 5분 전              │ │
│ ├─────────────────────┤ │
│ │ 관리비 납부 문의     │ │
│ │ 2시간 전            │ │
│ ├─────────────────────┤ │
│ │ 전세 계약 질문       │ │
│ │ 어제                │ │
│ └─────────────────────┘ │
├─────────────────────────┤
│ 📱 메인 챗봇            │ ← Navigation
│ 🗺️ 지도 검색           │
│ ...                     │
├─────────────────────────┤
│ 빠른 실행               │ ← Quick Actions
├─────────────────────────┤
│ 🕐 과거 대화 기록        │ ← Memory History
│    (PostgreSQL)         │   (별도 뷰어)
├─────────────────────────┤
│ AI 파트너               │ ← Footer
└─────────────────────────┘
```

---

### Phase 3: Memory History 재설계

#### 3.1 Option A: 모달 뷰어 (권장 ⭐)

**파일**: `frontend/components/memory-viewer-modal.tsx` (신규 생성)

**기능**:
```typescript
interface MemoryViewerModalProps {
  memory: ConversationMemory | null
  onClose: () => void
  onCreateSession?: (memory: ConversationMemory) => void
}

export function MemoryViewerModal({
  memory,
  onClose,
  onCreateSession
}: MemoryViewerModalProps) {
  if (!memory) return null

  return (
    <Dialog open={!!memory} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{memory.query}</DialogTitle>
          <DialogDescription>
            {new Date(memory.created_at).toLocaleString('ko-KR')}
            {' · '}
            {memory.intent_detected}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 사용자 질문 */}
          <div className="flex gap-3">
            <User className="h-5 w-5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium mb-1">질문</p>
              <p className="text-sm">{memory.query}</p>
            </div>
          </div>

          {/* 봇 응답 */}
          <div className="flex gap-3">
            <Bot className="h-5 w-5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium mb-1">응답</p>
              <p className="text-sm whitespace-pre-wrap">
                {memory.response_summary}
              </p>
            </div>
          </div>

          {/* 메타데이터 */}
          {memory.conversation_metadata && (
            <div className="text-xs text-muted-foreground space-y-1">
              {memory.conversation_metadata.teams_used && (
                <p>사용된 팀: {memory.conversation_metadata.teams_used.join(', ')}</p>
              )}
              {memory.conversation_metadata.response_time && (
                <p>응답 시간: {memory.conversation_metadata.response_time}ms</p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            닫기
          </Button>
          <Button
            onClick={() => {
              onCreateSession?.(memory)
              onClose()
            }}
          >
            이 대화로 새 채팅 시작
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**사용**:
```typescript
// memory-history.tsx
const [selectedMemory, setSelectedMemory] = useState<ConversationMemory | null>(null)

<div onClick={() => setSelectedMemory(memory)}>
  {/* Memory 항목 */}
</div>

<MemoryViewerModal
  memory={selectedMemory}
  onClose={() => setSelectedMemory(null)}
  onCreateSession={createSessionFromMemory}
/>
```

#### 3.2 Memory → 새 세션 변환

**파일**: `frontend/app/page.tsx` (수정)

```typescript
const createSessionFromMemory = (memory: ConversationMemory) => {
  const sessionId = `memory-${memory.id}`

  // 새 세션 생성
  const newSession: ChatSession = {
    sessionId,
    title: memory.query,
    messages: [
      {
        id: `memory-user-${memory.id}`,
        type: 'user',
        content: memory.query,
        timestamp: new Date(memory.created_at)
      },
      {
        id: `memory-bot-${memory.id}`,
        type: 'bot',
        content: memory.response_summary,
        timestamp: new Date(memory.created_at)
      }
    ],
    createdAt: memory.created_at,
    updatedAt: memory.created_at,
    isReadOnly: true,  // 읽기 전용 표시
    metadata: {
      source: 'memory',
      memoryId: memory.id
    }
  }

  // 세션 저장 및 전환
  saveSessionToStorage(newSession)

  // 세션 목록에 추가
  const sessionItem: SessionListItem = {
    sessionId,
    title: newSession.title,
    lastMessage: memory.response_summary.slice(0, 50),
    updatedAt: newSession.updatedAt
  }

  // useChatSessions를 통해 추가
  addSessionToList(sessionItem)
  switchSession(sessionId)
}
```

---

### Phase 4: page.tsx 통합

**파일**: `frontend/app/page.tsx` (수정)

```typescript
export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageType>("chat")

  // 세션 관리
  const {
    sessions,
    currentSessionId,
    createSession,
    switchSession,
    deleteSession,
    updateSessionTitle
  } = useChatSessions()

  // Memory 뷰어
  const [selectedMemory, setSelectedMemory] = useState<ConversationMemory | null>(null)

  const handleCreateNewSession = () => {
    const newSessionId = createSession()
    console.log('[HomePage] Created new session:', newSessionId)
  }

  const handleSwitchSession = (sessionId: string) => {
    switchSession(sessionId)
    setCurrentPage('chat') // 채팅 페이지로 이동
  }

  const handleCreateSessionFromMemory = (memory: ConversationMemory) => {
    const sessionId = createSessionFromMemory(memory)
    switchSession(sessionId)
    setCurrentPage('chat')
  }

  const renderMainContent = () => {
    switch (currentPage) {
      case "chat":
        return currentSessionId ? (
          <ChatInterface
            sessionId={currentSessionId}
            onSplitView={handleSplitView}
            onSessionTitleUpdate={updateSessionTitle}
          />
        ) : (
          <div>세션을 선택하거나 새 채팅을 시작하세요</div>
        )

      // ... 다른 페이지
    }
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onCreateNewSession={handleCreateNewSession}
        onSwitchSession={handleSwitchSession}
        onDeleteSession={deleteSession}
        onViewMemory={setSelectedMemory}
      />

      {/* Main Content */}
      <div className="flex-1">
        {renderMainContent()}
      </div>

      {/* Memory Viewer Modal */}
      <MemoryViewerModal
        memory={selectedMemory}
        onClose={() => setSelectedMemory(null)}
        onCreateSession={handleCreateSessionFromMemory}
      />
    </div>
  )
}
```

---

## 📊 데이터 흐름도

### 1. 새 채팅 시작

```
User Click [+ 새 채팅]
    ↓
useChatSessions.createSession()
    ↓
1. 새 sessionId 생성 (UUID)
2. SessionList에 추가
3. localStorage에 빈 세션 저장
4. currentSessionId 업데이트
    ↓
ChatInterface re-render (새 sessionId)
    ↓
빈 세션 로드 (환영 메시지만)
```

### 2. 메시지 전송

```
User 입력 → Send
    ↓
ChatInterface.handleSend()
    ↓
1. User 메시지 추가
2. WebSocket으로 전송
3. Bot 응답 수신
4. Bot 메시지 추가
    ↓
useEffect(messages) 트리거
    ↓
1. localStorage 세션 업데이트
2. 첫 메시지면 제목 자동 생성
3. SessionList 업데이트 (lastMessage, updatedAt)
```

### 3. 세션 전환

```
User Click 세션 항목
    ↓
useChatSessions.switchSession(sessionId)
    ↓
currentSessionId 업데이트
    ↓
ChatInterface useEffect(sessionId) 트리거
    ↓
1. localStorage에서 세션 로드
2. messages 상태 업데이트
3. 화면에 메시지 표시
```

### 4. Memory → 새 세션

```
User Click Memory 항목
    ↓
MemoryViewerModal 열림
    ↓
User Click [이 대화로 새 채팅 시작]
    ↓
createSessionFromMemory(memory)
    ↓
1. Memory 데이터로 새 세션 생성
2. isReadOnly: true 설정
3. localStorage 저장
4. SessionList에 추가
5. 해당 세션으로 전환
    ↓
ChatInterface에 Memory 대화 표시
```

---

## 🗂️ 파일 변경 요약

### 신규 생성 (6개)

```
frontend/
├── types/
│   └── session.ts                   # ✨ ChatSession, SessionList 타입
├── hooks/
│   └── use-chat-sessions.ts         # ✨ 세션 관리 Hook
├── utils/
│   └── session-storage.ts           # ✨ localStorage 헬퍼
├── components/
│   ├── session-list.tsx             # ✨ 세션 목록 컴포넌트
│   ├── memory-viewer-modal.tsx      # ✨ Memory 뷰어 모달
│   └── session-title-dialog.tsx     # ✨ 세션 제목 변경 다이얼로그
```

### 수정 (4개)

```
frontend/
├── app/
│   └── page.tsx                     # 🔧 useChatSessions 통합, Memory 뷰어
├── components/
│   ├── chat-interface.tsx           # 🔧 sessionId prop, 세션별 저장
│   ├── sidebar.tsx                  # 🔧 SessionList 추가, "새 채팅" 버튼
│   └── memory-history.tsx           # 🔧 모달 열기로 변경
```

### 제거/마이그레이션

```typescript
// localStorage 마이그레이션 필요
'chat-messages' (기존) → 'chat-session-*' (새)
```

---

## ⚠️ 주의사항 및 제약

### 1. localStorage 용량 관리

**문제**:
- localStorage 제한: 5-10MB
- 세션이 많아지면 용량 초과 가능

**해결책**:
```typescript
// 자동 정리: 30일 이상 된 세션 삭제
const cleanupOldSessions = () => {
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  sessions.forEach(session => {
    if (new Date(session.updatedAt) < thirtyDaysAgo) {
      deleteSession(session.sessionId)
    }
  })
}

// 세션 개수 제한: 최대 50개
const MAX_SESSIONS = 50
if (sessions.length > MAX_SESSIONS) {
  // 가장 오래된 세션 삭제
  const oldestSession = sessions.sort((a, b) =>
    new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
  )[0]
  deleteSession(oldestSession.sessionId)
}
```

### 2. WebSocket sessionId 연동

**현재**:
```typescript
// WebSocket은 별도 sessionId 사용
const { sessionId } = useSession() // HTTP 세션
```

**개선 필요**:
```typescript
// ChatInterface가 받은 sessionId를 WebSocket에도 사용
wsClient.connect(sessionId)
```

**문제점**:
- WebSocket sessionId는 서버에서 생성
- UI sessionId는 클라이언트에서 생성
- 둘을 동기화해야 함

**해결책 (선택)**:
1. **Option A**: UI sessionId를 서버에 전달하여 사용
2. **Option B**: 서버 sessionId를 UI에서 사용 (현재 방식)

### 3. 기존 데이터 마이그레이션

```typescript
// frontend/utils/migrate-storage.ts
export function migrateOldChatStorage() {
  const oldMessages = localStorage.getItem('chat-messages')

  if (oldMessages && !localStorage.getItem('chat-session-list')) {
    console.log('[Migration] Migrating old chat-messages to new session format')

    try {
      const messages = JSON.parse(oldMessages)

      // 기존 메시지로 새 세션 생성
      const sessionId = `session-migrated-${Date.now()}`
      const newSession: ChatSession = {
        sessionId,
        title: "이전 대화 (마이그레이션)",
        messages: messages.map(m => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        metadata: {
          source: 'migration'
        }
      }

      // 저장
      saveSessionToStorage(newSession)

      const sessionList: SessionList = {
        sessions: [{
          sessionId,
          title: newSession.title,
          lastMessage: messages[messages.length - 1]?.content || '',
          updatedAt: newSession.updatedAt
        }],
        currentSessionId: sessionId
      }
      localStorage.setItem('chat-session-list', JSON.stringify(sessionList))

      // 기존 데이터 삭제
      localStorage.removeItem('chat-messages')

      console.log('[Migration] Migration completed successfully')
    } catch (e) {
      console.error('[Migration] Migration failed:', e)
    }
  }
}
```

**실행 위치**: `app/page.tsx`의 `useEffect`

---

## 🧪 테스트 시나리오

### 시나리오 1: 새 채팅 시작
1. [+ 새 채팅] 클릭
2. ✅ 세션 목록에 "새 대화" 추가됨
3. ✅ 빈 채팅창 표시 (환영 메시지만)
4. 질문 입력 후 전송
5. ✅ 세션 제목이 첫 질문으로 자동 업데이트

### 시나리오 2: 세션 전환
1. 세션 A에서 대화 중
2. 세션 목록에서 세션 B 클릭
3. ✅ 세션 B의 대화 내용 표시
4. ✅ 세션 A의 내용은 localStorage에 보존
5. 다시 세션 A 클릭
6. ✅ 세션 A의 내용 그대로 복원

### 시나리오 3: 브라우저 새로고침
1. 여러 세션 생성 후 대화
2. F5 (새로고침)
3. ✅ 모든 세션 목록 표시
4. ✅ 마지막 활성 세션 자동 선택
5. ✅ 대화 내용 모두 복원

### 시나리오 4: Memory 조회
1. "🕐 과거 대화 기록" 클릭
2. Memory 항목 클릭
3. ✅ 모달로 대화 내용 표시
4. [이 대화로 새 채팅 시작] 클릭
5. ✅ 새 세션 생성 (읽기 전용 표시)
6. ✅ Memory 내용이 새 세션에 복사됨

### 시나리오 5: 세션 삭제
1. 세션 목록에서 세션 hover
2. 🗑️ 삭제 버튼 클릭
3. ✅ 세션 목록에서 제거
4. ✅ localStorage에서 삭제
5. ✅ 다른 세션으로 자동 전환

---

## 📅 구현 일정

### Phase 1: 세션 관리 시스템 (Day 1)
- [ ] `types/session.ts` 생성 (30분)
- [ ] `hooks/use-chat-sessions.ts` 구현 (1시간)
- [ ] `utils/session-storage.ts` 구현 (30분)
- [ ] `ChatInterface.tsx` 리팩토링 (1시간)
- [ ] 기존 데이터 마이그레이션 (30분)
- **소계**: 3.5시간

### Phase 2: UI 개선 (Day 1-2)
- [ ] `components/session-list.tsx` 구현 (1시간)
- [ ] `sidebar.tsx` 업데이트 (1시간)
- [ ] "새 채팅" 버튼 추가 (15분)
- [ ] 세션 제목 변경 다이얼로그 (30분)
- **소계**: 2시간 45분

### Phase 3: Memory 통합 (Day 2)
- [ ] `components/memory-viewer-modal.tsx` 구현 (1시간)
- [ ] `memory-history.tsx` 업데이트 (30분)
- [ ] Memory → 세션 변환 로직 (30분)
- **소계**: 2시간

### Phase 4: 통합 및 테스트 (Day 2)
- [ ] `app/page.tsx` 통합 (1시간)
- [ ] 전체 시나리오 테스트 (1시간)
- [ ] 버그 수정 및 최적화 (1시간)
- **소계**: 3시간

### 총 예상 시간: **11시간 15분** (약 1.5일)

---

## 🎯 성공 기준

### 필수 요구사항 (Must Have)
- [x] 세션별 독립적인 대화 관리
- [x] "새 채팅" 버튼으로 새 세션 생성
- [x] 세션 목록 표시 및 전환
- [x] 브라우저 새로고침 시 모든 세션 복원
- [x] Memory 클릭 시 현재 대화에 추가 안됨
- [x] localStorage 세션별 저장

### 중요 요구사항 (Should Have)
- [x] 세션 제목 자동 생성 (첫 질문)
- [x] 세션 삭제 기능
- [x] Memory 모달 뷰어
- [x] Memory → 새 세션 변환
- [x] 세션별 메타데이터 (생성일, 수정일)

### 선택 요구사항 (Nice to Have)
- [ ] 세션 제목 수동 변경
- [ ] 세션 검색 기능
- [ ] 세션 내보내기/가져오기
- [ ] 세션 즐겨찾기
- [ ] 세션 폴더 관리

---

## 🔄 마이그레이션 계획

### 기존 사용자 데이터 처리

```typescript
// 앱 시작 시 자동 실행
useEffect(() => {
  migrateOldChatStorage()
}, [])
```

**마이그레이션 로직**:
1. `chat-messages` 존재 확인
2. `chat-session-list` 없으면 마이그레이션 실행
3. 기존 메시지로 "이전 대화 (마이그레이션)" 세션 생성
4. 기존 키 삭제
5. 로그 출력

**롤백 불가**: 한 번 마이그레이션되면 되돌릴 수 없음
- 사용자에게 안내 메시지 표시 권장

---

## 📝 후속 개선 사항

### 1. Backend 통합
- 세션을 PostgreSQL에도 저장
- 여러 기기 간 동기화
- 세션 공유 기능

### 2. UI/UX 개선
- 드래그&드롭으로 세션 순서 변경
- 세션 검색 및 필터링
- 세션별 태그/라벨
- 세션 그룹화 (날짜별, 주제별)

### 3. 성능 최적화
- 가상 스크롤링 (세션 목록)
- 지연 로딩 (메시지)
- IndexedDB 사용 (대용량 데이터)

### 4. 협업 기능
- 세션 공유 링크
- 다른 사용자와 세션 공유
- 세션 코멘트/노트

---

## 🎉 결론

이 계획서는 현재 시스템의 근본적인 문제(세션 개념 부재)를 해결하고, 사용자 경험을 크게 개선할 수 있는 **세션 기반 채팅 아키텍처**를 제시합니다.

**핵심 개선 사항**:
1. ✅ 세션별 독립적인 대화 관리
2. ✅ Memory History와 현재 대화의 명확한 분리
3. ✅ localStorage 구조 개선 (세션별 저장)
4. ✅ "새 채팅" 버튼으로 직관적인 UX
5. ✅ 브라우저 새로고침 시에도 모든 세션 유지

**예상 효과**:
- 사용자 혼란 감소 (대화 중복 문제 해결)
- 데이터 관리 용이성 증가
- 확장성 확보 (향후 기능 추가 용이)
- 사용자 경험 대폭 개선

구현을 시작하시겠습니까?
