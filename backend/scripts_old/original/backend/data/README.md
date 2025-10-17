# 홈즈냥 부동산 AI 서비스 - 데이터베이스 설정

## 데이터베이스 구조

### PostgreSQL (관계형 데이터베이스)
- **사용자 관리**: 인증, 프로필, 소셜 로그인
- **부동산 매물**: 기본 정보, 이미지, 신뢰도 점수
- **AI 분석**: 상담 기록, 계약 분석
- **사용자 활동**: 즐겨찾기, 조회 기록, 알림

### MongoDB (문서 데이터베이스) 
- **대출 상품**: 은행별 대출 상품 정보 (JSON 형태)
- **법률 문서**: 부동산 관련 법률, 시행령, 시행규칙
- **용어사전**: 부동산 전문 용어 정의
- **AI 분석 결과**: 복잡한 분석 결과 저장

### ChromaDB (벡터 데이터베이스)
- **임베딩 저장**: 문서 검색 및 유사도 분석
- **RAG 시스템**: 법률 문서, 용어사전 검색

### Redis (캐시/세션)
- **세션 관리**: 사용자 로그인 세션
- **캐시**: 자주 조회되는 데이터
- **실시간 데이터**: 알림, 채팅 등

## 빠른 시작

### Docker Compose 사용 (권장)

```bash
# 모든 데이터베이스 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 상태 확인
docker-compose ps

# 서비스 중지
docker-compose down
```

### 수동 초기화

```bash
# 실행 권한 부여
chmod +x init_databases.sh

# 모든 데이터베이스 초기화
./init_databases.sh

# PostgreSQL만 초기화
./init_databases.sh postgresql

# MongoDB만 초기화  
./init_databases.sh mongodb

# 기존 대출 데이터 마이그레이션
./init_databases.sh migrate

# 데이터베이스 상태 확인
./init_databases.sh status
```

## 접속 정보

### PostgreSQL
- **호스트**: localhost:5432
- **데이터베이스**: homescat_db
- **사용자**: postgres
- **비밀번호**: postgres

### MongoDB
- **호스트**: localhost:27017
- **데이터베이스**: homescat_db
- **관리자**: admin / admin123

### ChromaDB
- **API 엔드포인트**: http://localhost:8000
- **Health Check**: http://localhost:8000/api/v1/heartbeat

### Redis
- **호스트**: localhost:6379
- **데이터베이스**: 0 (기본)

## 관리 도구

### pgAdmin (PostgreSQL 관리)
- **URL**: http://localhost:5050
- **이메일**: admin@homescat.com
- **비밀번호**: admin123

### MongoDB Express (MongoDB 관리)
- **URL**: http://localhost:8081
- **사용자**: admin / admin123

## 환경 변수

스크립트 실행 시 다음 환경 변수를 설정할 수 있습니다:

```bash
# PostgreSQL 설정
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_DB=homescat_db

# MongoDB 설정
export MONGODB_HOST=localhost
export MONGODB_PORT=27017
export MONGODB_DB=homescat_db
export MONGODB_USER=admin
export MONGODB_PASSWORD=admin123
```

## 파일 구조

```
data/
├── postgresql_schema.sql      # PostgreSQL 스키마 정의
├── mongodb_schema.js         # MongoDB 컬렉션 스키마
├── init_databases.sh         # 데이터베이스 초기화 스크립트
├── docker-compose.yml        # Docker 서비스 정의
├── redis.conf               # Redis 설정
├── README.md                # 이 파일
├── 은행대출/                 # 대출 상품 JSON 파일들
├── 부동산관련_법률_시행령_시행규칙/ # 법률 문서들
└── 부동산용어/               # 용어 정의 문서
```

## 주의사항

1. **프로덕션 환경**에서는 반드시 비밀번호를 변경하세요
2. **방화벽 설정**으로 불필요한 포트 접근을 차단하세요
3. **백업 전략**을 수립하여 정기적으로 데이터를 백업하세요
4. **모니터링**을 통해 데이터베이스 성능을 관찰하세요

## 문제 해결

### 연결 오류
```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs [service-name]

# 포트 사용 확인
netstat -an | grep -E "(5432|27017|8000|6379)"
```

### 권한 오류
```bash
# 스크립트 실행 권한 확인
chmod +x init_databases.sh

# Docker 권한 확인 (Linux/Mac)
sudo usermod -aG docker $USER
```

### 데이터 초기화
```bash
# 모든 데이터 삭제 후 재시작
docker-compose down -v
docker-compose up -d
```