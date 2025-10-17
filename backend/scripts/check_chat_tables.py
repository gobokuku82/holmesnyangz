"""
Chat Tables Data Verification Script
챗봇 관련 테이블 데이터 확인
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def check_chat_tables():
    """채팅 관련 테이블 데이터 확인"""
    print("\n" + "=" * 70)
    print("=== 챗봇 관련 테이블 데이터 확인 ===")
    print("=" * 70)

    try:
        from app.db.postgre_db import SessionLocal
        from sqlalchemy import text, inspect

        db = SessionLocal()

        try:
            # 1. 연결 확인
            db.execute(text("SELECT 1"))
            print("✅ PostgreSQL 연결 성공\n")

            # 2. 모든 테이블 목록 조회
            inspector = inspect(db.bind)
            all_tables = inspector.get_table_names()

            print(f"📊 전체 테이블 개수: {len(all_tables)}개\n")

            # 3. 챗봇/메모리 관련 테이블 구분
            chat_tables = ['chat_sessions', 'chat_messages']
            checkpoint_tables = ['checkpoints', 'checkpoint_blobs', 'checkpoint_writes', 'checkpoint_migrations']
            user_tables = ['users', 'user_profiles', 'local_auths', 'social_auths', 'user_favorites']
            real_estate_tables = ['regions', 'real_estates', 'transactions', 'real_estate_agents',
                                   'nearby_facilities', 'trust_scores']

            # 4. 테이블별 데이터 카운트
            print("=" * 70)
            print("📋 테이블 데이터 카운트")
            print("=" * 70)

            def print_table_counts(category, tables):
                print(f"\n🔹 {category}")
                print("-" * 70)
                for table in tables:
                    if table in all_tables:
                        result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                        status = "✅" if result > 0 else "⚠️ (비어있음)"
                        print(f"  {status} {table:30s} : {result:>8,}개")
                    else:
                        print(f"  ❌ {table:30s} : 테이블 없음")

            # 채팅 관련
            print_table_counts("채팅 & 세션 (Chat & Session)", chat_tables)

            # LangGraph 체크포인트
            print_table_counts("LangGraph 체크포인트 (Memory State)", checkpoint_tables)

            # 사용자 관련
            print_table_counts("사용자 & 인증 (Users & Auth)", user_tables)

            # 부동산 관련
            print_table_counts("부동산 데이터 (Real Estate)", real_estate_tables)

            # 5. chat_sessions 상세 조회
            print("\n" + "=" * 70)
            print("📝 chat_sessions 상세 정보")
            print("=" * 70)

            sessions_count = db.execute(text("SELECT COUNT(*) FROM chat_sessions")).scalar()

            if sessions_count > 0:
                # 최근 5개 세션
                result = db.execute(text("""
                    SELECT
                        session_id,
                        user_id,
                        title,
                        message_count,
                        is_active,
                        created_at,
                        updated_at
                    FROM chat_sessions
                    ORDER BY updated_at DESC
                    LIMIT 5
                """))

                print(f"\n최근 세션 5개 (전체 {sessions_count}개):\n")
                for row in result:
                    print(f"  📌 {row[0]}")
                    print(f"     제목: {row[2]}")
                    print(f"     메시지: {row[3]}개 | 활성: {row[4]} | 사용자: {row[1]}")
                    print(f"     생성: {row[5]} | 수정: {row[6]}")
                    print()
            else:
                print("\n  ⚠️ chat_sessions 테이블이 비어있습니다")

            # 6. chat_messages 상세 조회
            print("=" * 70)
            print("💬 chat_messages 상세 정보")
            print("=" * 70)

            messages_count = db.execute(text("SELECT COUNT(*) FROM chat_messages")).scalar()

            if messages_count > 0:
                # 최근 10개 메시지
                result = db.execute(text("""
                    SELECT
                        id,
                        session_id,
                        role,
                        LEFT(content, 50) as preview,
                        created_at
                    FROM chat_messages
                    ORDER BY created_at DESC
                    LIMIT 10
                """))

                print(f"\n최근 메시지 10개 (전체 {messages_count:,}개):\n")
                for row in result:
                    print(f"  💬 [{row[2]}] {row[3]}...")
                    print(f"     세션: {row[1]} | ID: {row[0]} | 시간: {row[4]}")
                    print()
            else:
                print("\n  ⚠️ chat_messages 테이블이 비어있습니다")

            # 7. checkpoints 상세 조회
            print("=" * 70)
            print("🔖 checkpoints 상세 정보")
            print("=" * 70)

            checkpoints_count = db.execute(text("SELECT COUNT(*) FROM checkpoints")).scalar()

            if checkpoints_count > 0:
                # 세션별 체크포인트 개수
                result = db.execute(text("""
                    SELECT
                        session_id,
                        COUNT(*) as checkpoint_count
                    FROM checkpoints
                    GROUP BY session_id
                    ORDER BY checkpoint_count DESC
                    LIMIT 10
                """))

                print(f"\n세션별 체크포인트 개수 (전체 {checkpoints_count:,}개):\n")
                for row in result:
                    print(f"  🔖 {row[0]:40s} : {row[1]:>5}개")
            else:
                print("\n  ⚠️ checkpoints 테이블이 비어있습니다")

            # 8. 기타 테이블 (비어있는 테이블 찾기)
            print("\n" + "=" * 70)
            print("📭 비어있는 테이블 (Empty Tables)")
            print("=" * 70)

            empty_tables = []
            for table in all_tables:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if count == 0:
                    empty_tables.append(table)

            if empty_tables:
                print(f"\n⚠️ 데이터가 없는 테이블 ({len(empty_tables)}개):\n")
                for table in empty_tables:
                    print(f"  - {table}")
            else:
                print("\n✅ 모든 테이블에 데이터가 있습니다!")

            print("\n" + "=" * 70)
            print("✅ 챗봇 테이블 확인 완료!")
            print("=" * 70)

        finally:
            db.close()

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_chat_tables()
