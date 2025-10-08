# ProcessFlow 통합 브라우저 테스트 가이드

## 🚀 서버 실행 확인

### Frontend
- **URL**: http://localhost:3000
- **상태**: ✅ Running (Next.js 14.2.16)

### Backend
- **URL**: http://localhost:8000
- **상태**: ✅ Running (FastAPI + Uvicorn)
- **API Docs**: http://localhost:8000/docs

---

## 🧪 테스트 시나리오

### Test 1: 기본 ProcessFlow 동작 확인

#### 1단계: 페이지 접속
1. 브라우저에서 http://localhost:3000 열기
2. 채팅 인터페이스 로딩 확인
3. 초기 봇 메시지 표시 확인: "안녕하세요! 도와줘 홈즈냥즈입니다..."

#### 2단계: 쿼리 전송 및 ProcessFlow 표시 확인
1. **테스트 쿼리 입력**: "강남구 아파트 시세 알려줘"
2. **예상 동작**:
   ```
   [User Message] 강남구 아파트 시세 알려줘

   [ProcessFlow 표시]
   ┌────────────────────────────────────────┐
   │ 🤖 AI 에이전트                         │
   │ 계획 중...                      0.0s   │
   │                                        │
   │ ○━━○━━○━━○  (진행 단계 표시)         │
   │ 계획 검색 분석 생성                    │
   └────────────────────────────────────────┘
   ```

3. **API 응답 도착 후**:
   - ProcessFlow가 실제 백엔드 데이터로 업데이트되는지 확인
   - 예상: "검색 (searching)" 단계가 "completed" 상태로 표시
   - 진행률 100% 표시 확인

4. **완료 후**:
   - ProcessFlow 메시지 제거 확인
   - 봇 응답 메시지 표시 확인

#### 3단계: 개발자 도구로 API 응답 확인
1. F12 또는 Ctrl+Shift+I로 개발자 도구 열기
2. **Network 탭** 이동
3. `/chat/message` POST 요청 찾기
4. **Response 확인**:
   ```json
   {
     "session_id": "...",
     "response": {
       "answer": "강남구 아파트 시세는..."
     },
     "process_flow": [  // ← 이 필드 확인!
       {
         "step": "searching",
         "label": "검색",
         "agent": "search_team",
         "status": "completed",
         "progress": 100
       }
     ],
     "execution_time_ms": 3000,
     ...
   }
   ```

5. **Console 탭** 확인:
   ```
   ✅ process_flow 데이터가 있어야 함
   ✅ "Generated process_flow with 1 steps" 로그 확인
   ```

---

### Test 2: 여러 팀 실행 시나리오

#### 테스트 쿼리들:
```
1. "민법 제2조 조문 내용 알려줘"
   → 예상: "검색 (searching)" 단계만 표시

2. "계약서 검토해줘" (계약서 첨부 필요)
   → 예상: "분석 (analyzing)" 단계 표시

3. "전세사기 위험도를 분석해줘"
   → 예상: "검색 → 분석" 2단계 표시
```

#### 각 쿼리별 확인 사항:
1. ProcessFlow 단계 개수가 실제 실행된 팀 개수와 일치하는가?
2. 각 단계의 label이 올바르게 한글로 표시되는가?
3. status가 "completed"로 표시되는가?
4. progress가 100으로 표시되는가?

---

### Test 3: 에러 처리 확인

#### 시나리오: 백엔드 중단
1. 백엔드 서버 중단 (Ctrl+C)
2. 프론트엔드에서 쿼리 전송
3. **예상 동작**:
   - ProcessFlow에 에러 상태 표시
   - 에러 메시지 표시
   - ProcessFlow 메시지 제거
   - "오류가 발생했습니다" 메시지 표시

---

## 🔍 상세 확인 항목

### ProcessFlow 컴포넌트
- [ ] ProcessFlow 메시지가 사용자 메시지 다음에 표시됨
- [ ] 봇 아이콘과 함께 카드 형태로 표시됨
- [ ] 경과 시간이 0.0s부터 증가함
- [ ] 진행 단계가 가로 방향으로 표시됨 (○━━○━━○━━○)

### 동적 단계 렌더링
- [ ] `dynamicSteps`가 전달되면 백엔드 데이터 기반 단계 표시
- [ ] `dynamicSteps`가 없으면 기존 4단계 fallback 표시
- [ ] 단계 개수가 실행된 팀에 따라 다름 (1-4개)

### API 데이터 흐름
- [ ] `/chat/message` 응답에 `process_flow` 필드 포함
- [ ] `process_flow` 배열에 각 단계 정보 포함
- [ ] 각 단계에 `step`, `label`, `agent`, `status`, `progress` 포함

### UI/UX
- [ ] 활성 단계: 파란색 + 회전 애니메이션
- [ ] 완료 단계: 초록색 + 체크 아이콘
- [ ] 대기 단계: 회색 + 원형 점
- [ ] 연결선이 완료된 단계까지 초록색으로 변경

---

## 🐛 예상 가능한 문제

### 문제 1: process_flow가 null
**증상**: API 응답에 `process_flow: null`

**원인**:
- `planning_state.execution_steps`가 비어 있음
- StepMapper 변환 실패

**확인 방법**:
```bash
# Backend 로그 확인
tail -f backend/logs/app.log

# 다음 로그 찾기:
"Generated process_flow with X steps"
```

**해결**:
- `planning_node`에서 `execution_steps` 생성 확인
- `converters.py`의 try-except 로그 확인

---

### 문제 2: ProcessFlow가 정적 단계만 표시
**증상**: 항상 "계획 → 검색 → 분석 → 생성" 4단계 표시

**원인**:
- `message.processFlowSteps`가 undefined
- API 응답에 `process_flow` 없음
- ChatInterface가 데이터 전달하지 않음

**확인 방법**:
```javascript
// 브라우저 Console에서 확인
console.log(messages.find(m => m.type === 'process-flow'))

// processFlowSteps 필드 확인
```

**해결**:
- ChatInterface의 `handleSendMessage`에서 `response.process_flow` 처리 확인
- `setMessages` 업데이트 로직 확인

---

### 문제 3: TypeScript 에러
**증상**: 브라우저 Console에 TypeScript 타입 에러

**원인**:
- `ProcessFlowStep` 인터페이스 import 누락
- `Message.processFlowSteps` 타입 불일치

**해결**:
```typescript
// types/chat.ts 확인
export interface ProcessFlowStep { ... }

// chat-interface.tsx 확인
import type { ProcessFlowStep } from "@/types/chat"
```

---

### 문제 4: CORS 에러
**증상**: Network 탭에서 CORS 에러

**원인**:
- Backend CORS 설정 문제

**해결**:
```python
# backend/app/main.py 확인
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## ✅ 성공 기준

다음 항목이 모두 충족되면 테스트 성공:

1. **API 응답**
   - [x] `process_flow` 필드 존재
   - [x] 1개 이상의 step 포함
   - [x] 각 step이 `step`, `label`, `agent`, `status`, `progress` 포함

2. **UI 표시**
   - [ ] ProcessFlow 컴포넌트가 쿼리 전송 시 표시됨
   - [ ] 백엔드 데이터 기반 동적 단계 렌더링
   - [ ] 실행된 팀에 따라 단계 개수 변화
   - [ ] 완료 후 ProcessFlow 제거, 답변 표시

3. **에러 처리**
   - [ ] 에러 발생 시 적절한 UI 표시
   - [ ] ProcessFlow 에러 상태 표시
   - [ ] 복구 가능 (새 쿼리 전송 시 정상 작동)

---

## 📸 스크린샷 체크리스트

테스트 완료 후 다음 상태 캡처:

1. **ProcessFlow 표시 중**
   - 쿼리 전송 직후
   - 진행 단계 애니메이션

2. **API 응답 확인**
   - Network 탭에서 `/chat/message` Response
   - `process_flow` 필드 내용

3. **완료 후 UI**
   - ProcessFlow 제거됨
   - 봇 응답 표시됨

4. **여러 팀 실행 시**
   - 1팀 실행 (1단계만)
   - 2팀 실행 (2단계)

---

## 🚀 테스트 후 다음 단계

### 성공 시
1. ✅ Part 1-2 완료 확인
2. 📝 브라우저 테스트 결과 문서화
3. 🎉 배포 준비

### 실패 시
1. 🐛 문제 식별 (위 "예상 가능한 문제" 참조)
2. 🔧 디버깅 및 수정
3. 🔄 재테스트

---

## 📞 도움말

### 서버 재시작
```bash
# 백엔드 재시작
cd backend
../venv/Scripts/python -m uvicorn app.main:app --reload

# 프론트엔드 재시작
cd frontend
npm run dev
```

### 로그 확인
```bash
# 백엔드 로그
tail -f backend/logs/app.log

# 프론트엔드 Console
브라우저 개발자 도구 (F12) → Console 탭
```

### API 직접 테스트
```bash
# Swagger UI
http://localhost:8000/docs

# cURL
curl -X POST "http://localhost:8000/chat/message" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "강남구 아파트 시세",
    "session_id": "test-session"
  }'
```

---

**작성일**: 2025-10-08
**테스트 대상**: TODO + ProcessFlow Integration (Part 1-2)
**문서 버전**: 1.0
