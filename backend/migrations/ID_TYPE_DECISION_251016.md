# ID 타입 결정 사항

**날짜**: 2025-10-16
**결정자**: DB 담당자

---

## ✅ 최종 결정

### SERIAL 유지 (대부분 테이블)
```sql
-- 부동산 데이터, 사용자 등
users.id                    → SERIAL (INTEGER)
regions.id                  → SERIAL (INTEGER)
real_estates.id             → SERIAL (INTEGER)
transactions.id             → SERIAL (INTEGER)
real_estate_agents.id       → SERIAL (INTEGER)
nearby_facilities.id        → SERIAL (INTEGER)
trust_scores.id             → SERIAL (INTEGER)
chat_messages.id            → SERIAL (INTEGER)
```

**이유**: 성능 우선 (JOIN 속도, 인덱스 효율)

---

### UUID 사용 (채팅 세션만)
```sql
-- 채팅 세션
chat_sessions.session_id    → VARCHAR(100) (UUID 형식 문자열 저장)
                               예: "session-f7479908-ad91-4c09-87b6-a0404eea7412"
```

**이유**:
- WebSocket 연결 식별자로 사용
- 외부 노출 가능성 (보안 고려)
- 추측 불가능한 세션 ID 필요

---

## 📊 현재 구조 확인

| 테이블 | PK 컬럼 | 타입 | 비고 |
|--------|---------|------|------|
| users | id | SERIAL | ✅ 유지 |
| regions | id | SERIAL | ✅ 유지 |
| real_estates | id | SERIAL | ✅ 유지 |
| transactions | id | SERIAL | ✅ 유지 |
| **chat_sessions** | **session_id** | **VARCHAR(100)** | ✅ UUID 형식 유지 |
| chat_messages | id | SERIAL | ✅ 유지 |
| checkpoints | session_id | TEXT | ✅ UUID 형식 유지 |

---

## 결론

**변경 사항 없음** - 현재 구조가 설계 의도와 일치함

- SERIAL: 성능이 중요한 내부 데이터
- UUID: 보안이 중요한 외부 노출 데이터 (채팅 세션)
