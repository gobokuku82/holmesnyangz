# 부동산 챗봇 프론트엔드 (Real Estate Chatbot Frontend)

## 프로젝트 개요
React와 TypeScript로 구축된 부동산 AI 챗봇 프론트엔드 애플리케이션입니다. WebSocket을 통해 백엔드와 실시간 통신하며, 사용자 친화적인 채팅 인터페이스를 제공합니다.

## 기술 스택
- **Framework**: React 19.1.1
- **Language**: TypeScript 4.9.5
- **Styling**: Styled Components 6.1.19
- **Icons**: React Icons 5.5.0
- **HTTP Client**: Axios 1.11.0
- **Build Tool**: Create React App (react-scripts 5.0.1)

## 프로젝트 구조
```
frontend/
├── public/              # 정적 파일
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/      # React 컴포넌트
│   │   ├── ChatInterface.tsx    # 메인 채팅 인터페이스
│   │   ├── MessageList.tsx      # 메시지 목록 표시
│   │   ├── InputArea.tsx        # 메시지 입력 영역
│   │   ├── AgentStatus.tsx      # 에이전트 상태 표시
│   │   ├── ProgressBar.tsx      # 진행 상태 바
│   │   └── SpinnerModal.tsx     # 로딩 스피너
│   ├── styles/          # 스타일 파일
│   │   └── GlobalStyle.ts       # 전역 스타일
│   ├── services/        # API 서비스
│   │   └── websocket.ts         # WebSocket 통신
│   ├── types/           # TypeScript 타입 정의
│   │   └── index.ts
│   ├── utils/           # 유틸리티 함수
│   ├── App.tsx          # 메인 앱 컴포넌트
│   ├── App.test.tsx     # 앱 테스트
│   └── index.tsx        # 엔트리 포인트
├── package.json         # 프로젝트 설정 및 의존성
├── tsconfig.json        # TypeScript 설정
└── README.md           # 프로젝트 문서
```

## 주요 기능

### 1. 실시간 채팅 인터페이스
- WebSocket을 통한 실시간 메시지 송수신
- 메시지 스트리밍 지원
- 타이핑 인디케이터

### 2. 에이전트 상태 표시
- 현재 활성화된 에이전트 표시
- 에이전트별 처리 상태 시각화
- 진행률 표시

### 3. 사용자 경험 기능
- 반응형 디자인 (모바일/데스크톱)
- 다크/라이트 테마 지원
- 메시지 히스토리 관리
- 자동 스크롤
- 로딩 상태 표시

### 4. 메시지 타입별 표시
- 사용자 메시지
- AI 에이전트 응답
- 시스템 메시지
- 에러 메시지

## 설치 방법

### 1. Node.js 설치 확인
```bash
# Node.js 18+ 권장
node --version
npm --version
```

### 2. 의존성 설치
```bash
# frontend 디렉토리로 이동
cd frontend

# npm을 사용한 설치
npm install

# 또는 yarn 사용
yarn install
```

## 실행 방법

### 개발 서버 실행
```bash
# frontend 디렉토리에서
npm start

# 또는 yarn 사용
yarn start
```

개발 서버는 기본적으로 http://localhost:3000 에서 실행됩니다.

### 프로덕션 빌드
```bash
# 프로덕션 빌드 생성
npm run build

# 빌드 결과물은 build/ 디렉토리에 생성됨
```

### 빌드된 파일 서빙 (프로덕션)
```bash
# serve 패키지 설치 (전역)
npm install -g serve

# 빌드 파일 서빙
serve -s build -l 3000
```

## 환경 설정

### 환경 변수
`.env` 파일을 frontend 디렉토리에 생성:
```env
# API 서버 주소
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# 기타 설정
REACT_APP_MAX_MESSAGE_LENGTH=1000
REACT_APP_RECONNECT_INTERVAL=3000
```

### WebSocket 연결 설정
`src/services/websocket.ts` 파일에서 WebSocket 연결 설정 가능:
```typescript
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
```

## 주요 컴포넌트

### ChatInterface
메인 채팅 인터페이스 컴포넌트
- WebSocket 연결 관리
- 메시지 상태 관리
- 에이전트 상태 관리

### MessageList
메시지 목록을 표시하는 컴포넌트
- 메시지 타입별 스타일링
- 자동 스크롤
- 타임스탬프 표시

### InputArea
사용자 입력을 받는 컴포넌트
- 텍스트 입력
- 전송 버튼
- 입력 유효성 검사

### AgentStatus
현재 활성 에이전트 상태를 표시
- 에이전트 이름
- 처리 상태
- 진행 시간

## 테스트

### 단위 테스트 실행
```bash
npm test
```

### 테스트 커버리지 확인
```bash
npm test -- --coverage
```

### E2E 테스트 (Cypress 등 설정 필요)
```bash
npm run e2e
```

## 빌드 및 배포

### 로컬 빌드
```bash
npm run build
```

### Docker 빌드
```dockerfile
# Dockerfile 예시
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
```

### 배포
빌드된 파일을 웹 서버(Nginx, Apache 등)에 배포:
```bash
# Nginx 설정 예시
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/build;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 개발 가이드

### 새로운 컴포넌트 추가
1. `src/components/` 디렉토리에 컴포넌트 파일 생성
2. TypeScript 인터페이스 정의
3. Styled Components로 스타일링
4. 필요한 경우 테스트 파일 작성

### 상태 관리
- React Hooks (useState, useEffect, useContext) 사용
- 복잡한 상태는 useReducer 활용
- 전역 상태가 필요한 경우 Context API 사용

### 코드 스타일
- ESLint 규칙 준수
- Prettier 포맷팅 적용
- TypeScript strict 모드 사용

## 트러블슈팅

### WebSocket 연결 실패
```javascript
// 연결 재시도 로직 확인
const reconnect = () => {
  setTimeout(() => {
    connectWebSocket();
  }, RECONNECT_INTERVAL);
};
```

### CORS 에러
백엔드 서버의 CORS 설정 확인:
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 빌드 에러
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install
```

## 성능 최적화

### 코드 스플리팅
```javascript
// Lazy loading
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));
```

### 메모이제이션
```javascript
// React.memo 사용
const MemoizedComponent = React.memo(Component);

// useMemo, useCallback 활용
const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);
```

## 브라우저 지원
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 라이선스
MIT License