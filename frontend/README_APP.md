# 부동산 AI 챗봇 - Frontend

## 🚀 시작하기

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 개발 서버 실행
```bash
npm start
```

앱이 http://localhost:3000 에서 실행됩니다.

## 🎨 주요 기능

### 📊 진행 상태 표시
- **전체 진행률 바**: 상단에 워크플로우 전체 진행 상황 표시
- **단계별 표시**: 질의 분석 → 계획 수립 → 실행 → 완료

### 🌀 4단계 스피너
1. **질의 분석** (thinking_spinner.gif): 사용자 입력을 분석할 때
2. **계획 수립** (planning_spinner.gif): 실행 계획을 세울 때  
3. **에이전트 실행** (excute_spnnier.gif): 각 에이전트가 작업할 때
4. **메인 로딩** (main_spinner.gif): 일반 로딩 상태

### 🤖 에이전트 상태
- 개별 에이전트 진행률 표시
- 실시간 상태 업데이트 (대기중/실행중/완료/오류)
- 각 에이전트별 진행률 퍼센트 표시

### 💬 채팅 인터페이스
- 실시간 메시지 주고받기
- 추천 질문 제안
- 타이핑 인디케이터
- 메시지 전송 상태 표시

## ⚙️ 환경 설정

`.env` 파일에서 설정 변경 가능:

```env
# 백엔드 API URL (FastAPI 서버 주소)
REACT_APP_API_URL=http://localhost:8000/api/v1

# WebSocket URL
REACT_APP_WS_URL=ws://localhost:8000/ws

# 목업 데이터 사용 여부 (개발시 true)
REACT_APP_USE_MOCK=true
```

## 📁 프로젝트 구조

```
frontend/
├── public/
│   ├── spinner/        # 스피너 GIF 파일들
│   └── character/      # 캐릭터 이미지들
├── src/
│   ├── components/     # React 컴포넌트
│   │   ├── ChatInterface.tsx    # 메인 채팅 인터페이스
│   │   ├── MessageList.tsx      # 메시지 목록
│   │   ├── InputArea.tsx        # 입력 영역
│   │   ├── SpinnerModal.tsx     # 스피너 모달
│   │   ├── ProgressBar.tsx      # 진행률 표시
│   │   └── AgentStatus.tsx      # 에이전트 상태
│   ├── services/       # API 서비스
│   │   ├── api.ts              # API 통신
│   │   └── websocket.ts        # WebSocket 연결
│   ├── types/          # TypeScript 타입 정의
│   └── styles/         # 스타일 관련
```

## 🔄 백엔드 연동

### 목업 모드 (현재)
- `REACT_APP_USE_MOCK=true`로 설정시 목업 데이터 사용
- 백엔드 없이도 UI 테스트 가능

### 실제 백엔드 연동
1. 백엔드 서버 실행:
```bash
cd ../backend
python main.py
```

2. `.env` 파일 수정:
```env
REACT_APP_USE_MOCK=false
```

3. 프론트엔드 재시작:
```bash
npm start
```

## 🎯 사용 예시

1. 앱 실행 후 추천 질문 클릭 또는 직접 입력
2. 실시간으로 처리 과정 확인:
   - 🔍 질의 분석 스피너
   - 📋 계획 수립 스피너  
   - ⚡ 에이전트 실행 스피너
   - 진행률 표시
3. 각 에이전트별 처리 상태 확인
4. 최종 답변 확인

## 📝 개발 명령어

```bash
# 개발 서버 실행
npm start

# 프로덕션 빌드
npm run build

# 테스트 실행
npm test

# 린트 검사
npm run lint
```