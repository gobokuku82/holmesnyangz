"""
전체 DB 데이터 현황 확인 스크립트
"""
import asyncio
from sqlalchemy import text
from app.db.postgre_db import get_async_db


async def check_all_data():
    async for db in get_async_db():
        try:
            print('=' * 80)
            print('📊 전체 데이터베이스 현황 확인')
            print('=' * 80)

            # 1. 부동산 데이터 확인
            print('\n🏢 부동산 관련 데이터:')
            print('-' * 80)

            estate_tables = [
                ('regions', '지역 정보'),
                ('real_estates', '부동산 매물'),
                ('transactions', '거래 정보'),
                ('real_estate_agents', '중개사'),
                ('nearby_facilities', '주변 시설'),
                ('trust_scores', '신뢰도 점수')
            ]

            for table, desc in estate_tables:
                try:
                    result = await db.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    status = '✅' if count > 0 else '⚠️'
                    print(f'   {status} {table:<25} ({desc:<15}): {count:>6}개')
                except Exception as e:
                    print(f'   ❌ {table:<25} ({desc:<15}): 테이블 없음')

            # 2. 채팅 데이터 확인
            print('\n💬 채팅 관련 데이터:')
            print('-' * 80)

            chat_tables = [
                ('chat_sessions', '채팅 세션'),
                ('chat_messages', '채팅 메시지')
            ]

            for table, desc in chat_tables:
                try:
                    result = await db.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    status = '✅' if count > 0 else '⚠️'
                    print(f'   {status} {table:<25} ({desc:<15}): {count:>6}개')
                except Exception as e:
                    print(f'   ❌ {table:<25} ({desc:<15}): 테이블 없음')

            # 3. session_id 형식 확인
            print('\n🔑 Session ID 형식:')
            print('-' * 80)

            try:
                result = await db.execute(text('''
                    SELECT
                        CASE
                            WHEN session_id LIKE 'session-%' THEN '✅ session-{uuid}'
                            WHEN session_id LIKE 'chat-%' THEN '❌ chat-{uuid}'
                            ELSE '⚠️ 기타'
                        END AS format_type,
                        COUNT(*) as count
                    FROM chat_sessions
                    GROUP BY format_type
                '''))

                rows = result.fetchall()
                if rows:
                    for row in rows:
                        print(f'   {row[0]}: {row[1]}개')
                else:
                    print('   ⚠️ 세션 데이터 없음')
            except:
                print('   ❌ chat_sessions 테이블 없음')

            # 4. 사용자 데이터 확인
            print('\n👤 사용자 관련 데이터:')
            print('-' * 80)

            user_tables = [
                ('users', '사용자'),
                ('user_profiles', '프로필'),
                ('user_favorites', '찜 목록')
            ]

            for table, desc in user_tables:
                try:
                    result = await db.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    status = '✅' if count > 0 else '⚠️'
                    print(f'   {status} {table:<25} ({desc:<15}): {count:>6}개')
                except Exception as e:
                    print(f'   ❌ {table:<25} ({desc:<15}): 테이블 없음')

            # 5. 체크포인트 데이터 확인
            print('\n💾 체크포인트 관련 데이터:')
            print('-' * 80)

            checkpoint_tables = [
                ('checkpoints', '체크포인트'),
                ('checkpoint_writes', '체크포인트 업데이트'),
                ('checkpoint_blobs', '체크포인트 블롭')
            ]

            for table, desc in checkpoint_tables:
                try:
                    result = await db.execute(text(f'SELECT COUNT(*) FROM {table}'))
                    count = result.scalar()
                    status = '✅' if count > 0 else '⚠️'
                    print(f'   {status} {table:<25} ({desc:<15}): {count:>6}개')
                except Exception as e:
                    print(f'   ❌ {table:<25} ({desc:<15}): 테이블 없음')

            # 6. 전체 요약
            print('\n' + '=' * 80)
            print('📈 전체 요약:')
            print('=' * 80)

            try:
                summary = await db.execute(text('''
                    SELECT
                        (SELECT COUNT(*) FROM real_estates) as estates,
                        (SELECT COUNT(*) FROM transactions) as transactions,
                        (SELECT COUNT(*) FROM chat_sessions) as sessions,
                        (SELECT COUNT(*) FROM chat_messages) as messages,
                        (SELECT COUNT(*) FROM users) as users
                '''))

                row = summary.fetchone()
                print(f'   🏢 부동산 매물: {row[0]:,}개')
                print(f'   💰 거래 정보: {row[1]:,}개')
                print(f'   💬 채팅 세션: {row[2]:,}개')
                print(f'   📝 채팅 메시지: {row[3]:,}개')
                print(f'   👤 사용자: {row[4]:,}개')

                # 중요 데이터 여부 판단
                print('\n' + '=' * 80)
                if row[0] > 0 or row[1] > 0:
                    print('⚠️  중요: 부동산/거래 데이터가 존재합니다!')
                    print('   → complete_rebuild_251017.sql 실행 시 모든 데이터가 삭제됩니다.')
                    print('   → 대신 chat 데이터만 삭제하는 스크립트를 사용하세요.')
                else:
                    print('✅ 부동산/거래 데이터 없음')
                    print('   → complete_rebuild_251017.sql 실행해도 안전합니다.')

            except Exception as e:
                print(f'   ❌ 요약 생성 실패: {e}')

            print('=' * 80)

        except Exception as e:
            print(f'❌ 오류 발생: {e}')
            import traceback
            traceback.print_exc()
        finally:
            break


if __name__ == '__main__':
    asyncio.run(check_all_data())
