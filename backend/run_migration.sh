#!/bin/bash

# Git Bash용 데이터베이스 마이그레이션 스크립트

echo "============================================================"
echo "🚀 데이터베이스 마이그레이션 시작"
echo "============================================================"
echo ""

# 작업 디렉토리로 이동
cd /c/kdy/Projects/holmesnyangz/beta_v001/backend

echo "============================================================"
echo "1단계: 부동산 데이터 임포트"
echo "============================================================"
echo ""

echo "📦 아파트/오피스텔 데이터 임포트 중..."
uv run python scripts/import_apt_ofst.py
if [ $? -eq 0 ]; then
    echo "✅ 아파트/오피스텔 임포트 완료"
else
    echo "❌ 아파트/오피스텔 임포트 실패"
    exit 1
fi

echo ""
echo "📦 원룸 데이터 임포트 중..."
uv run python scripts/import_villa_house_oneroom.py --auto --type oneroom
if [ $? -eq 0 ]; then
    echo "✅ 원룸 임포트 완료"
else
    echo "❌ 원룸 임포트 실패"
    exit 1
fi

echo ""
echo "📦 빌라 데이터 임포트 중..."
uv run python scripts/import_villa_house_oneroom.py --auto --type villa
if [ $? -eq 0 ]; then
    echo "✅ 빌라 임포트 완료"
else
    echo "❌ 빌라 임포트 실패"
    exit 1
fi

echo ""
echo "============================================================"
echo "2단계: 채팅 테이블 마이그레이션"
echo "============================================================"
echo ""

uv run python scripts/init_chat_tables.py
if [ $? -eq 0 ]; then
    echo "✅ 채팅 테이블 마이그레이션 완료"
else
    echo "❌ 채팅 테이블 마이그레이션 실패"
    exit 1
fi

echo ""
echo "============================================================"
echo "3단계: 데이터 확인"
echo "============================================================"
echo ""

echo "📊 테이블 목록:"
psql -U postgres -d real_estate -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

echo ""
echo "📊 데이터 개수:"
psql -U postgres -d real_estate -c "
SELECT 'real_estates' as table, COUNT(*) as count FROM real_estates
UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL SELECT 'chat_sessions', COUNT(*) FROM chat_sessions
UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages
UNION ALL SELECT 'checkpoints', COUNT(*) FROM checkpoints;
"

echo ""
echo "============================================================"
echo "✅ 마이그레이션 완료!"
echo "============================================================"
