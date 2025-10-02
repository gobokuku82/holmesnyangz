@echo off
echo ============================================================
echo ChromaDB 임베딩 진행 상황 확인
echo ============================================================
echo.
echo [프로세스 상태]
tasklist | findstr python
echo.
echo [로그 파일 마지막 20줄]
tail -n 20 backend\data\storage\legal_info\embedding\embedding_log.txt
echo.
echo [ChromaDB 파일 크기]
dir backend\data\storage\legal_info\chroma_db /s | findstr "파일"
echo.
echo ============================================================
echo 진행 상황 모니터링: tail -f backend\data\storage\legal_info\embedding\embedding_log.txt
echo ============================================================
