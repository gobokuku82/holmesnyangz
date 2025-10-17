@echo off
echo ==========================================
echo 📊 데이터베이스 현황 확인
echo ==========================================
echo.

echo 🏢 부동산 데이터:
psql -U postgres -d real_estate -c "SELECT COUNT(*) as 부동산매물 FROM real_estates;"
psql -U postgres -d real_estate -c "SELECT COUNT(*) as 거래정보 FROM transactions;"

echo.
echo 💬 채팅 데이터:
psql -U postgres -d real_estate -c "SELECT COUNT(*) as 채팅세션 FROM chat_sessions;"
psql -U postgres -d real_estate -c "SELECT COUNT(*) as 채팅메시지 FROM chat_messages;"

echo.
echo 🔑 Session ID 형식:
psql -U postgres -d real_estate -c "SELECT CASE WHEN session_id LIKE 'session-%%' THEN '✅ session-' WHEN session_id LIKE 'chat-%%' THEN '❌ chat-' ELSE '⚠️ 기타' END AS 형식, COUNT(*) as 개수 FROM chat_sessions GROUP BY 형식;"

echo.
echo ==========================================
pause
