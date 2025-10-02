#!/usr/bin/env python3
"""
Hard Query Test Suite for Legal Vector DB Search (100 Queries)
벡터 DB 검색 정확도 테스트 - 50개 기존 법률 + 50개 없는 법률

목적:
- 법률 정보 검색 정확도 평가
- 특정 조문 검색 성능 평가
- 존재하지 않는 법률에 대한 적절한 처리 확인
- SQL + ChromaDB 하이브리드 검색 성능 측정
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

# Add project root to path
current_file = Path(__file__)
tests_dir = current_file.parent
service_dir = tests_dir.parent
app_dir = service_dir.parent
backend_dir = app_dir.parent

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

sys.path.insert(0, str(backend_dir / "app" / "service"))

from supervisor.supervisor import RealEstateSupervisor
from core.context import create_default_llm_context

console = Console()


class HardQueryTester:
    """100개 하드 쿼리 테스트 실행 및 보고서 생성"""

    def __init__(self):
        self.supervisor = None
        self.test_results = []
        self.report_path = backend_dir / "app" / "service" / "reports"
        self.report_path.mkdir(exist_ok=True)

    async def initialize(self):
        """Supervisor 초기화"""
        llm_context = create_default_llm_context()
        self.supervisor = RealEstateSupervisor(llm_context=llm_context)
        console.print("[green][OK][/green] Supervisor initialized\n")

    def get_hard_queries(self) -> List[Tuple[str, str, str, bool]]:
        """
        벡터 DB 검색용 100개 하드 쿼리

        Returns:
            List[(query, expected_category, expected_key_law, should_exist)]
        """
        return [
            # === PART 1: 기존 50개 - 데이터베이스에 존재하는 법률 ===

            # === 1. 임대차 전세 관련 (15개) ===
            ("전세금을 5% 이상 올릴 수 있나요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("임대차 계약 갱신 요구권은 몇 번까지 가능한가요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("전세 계약 종료 후 보증금을 언제까지 돌려받아야 하나요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("월세를 전세로 바꿀 수 있나요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("임차인이 우선적으로 보증금을 받을 수 있는 조건은?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("전입신고를 하지 않으면 어떻게 되나요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("임대인이 계약 갱신을 거부할 수 있는 경우는?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("주택임대차보호법 제7조 내용은?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("차임 증액 제한은 얼마인가요?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("주택임대차보호법 제8조의 내용은?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("임대차 계약 묵시적 갱신이란?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("소액임차인 보증금 반환 우선순위는?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("임차권등기명령 신청 요건은?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("전세 보증금 전환 시 월세 산정 방법은?", "2_임대차_전세_월세", "주택임대차보호법", True),
            ("주택임대차보호법 제3조 대항력은?", "2_임대차_전세_월세", "주택임대차보호법", True),

            # === 2. 매매 분양 관련 (10개) ===
            ("부동산 거래 신고는 언제까지 해야 하나요?", "1_공통 매매_임대차", "부동산 거래신고 등에 관한 법률", True),
            ("분양권 전매 제한 기간은?", "3_공급_및_관리_매매_분양", "주택법", True),
            ("주택법 제2조 정의 규정은?", "3_공급_및_관리_매매_분양", "주택법", True),
            ("주택 청약 1순위 조건은?", "3_공급_및_관리_매매_분양", "주택공급에 관한 규칙", True),
            ("분양가상한제 적용 지역은?", "3_공급_및_관리_매매_분양", "주택법", True),
            ("부동산등기법 제73조는 무엇인가요?", "1_공통 매매_임대차", "부동산등기법", True),
            ("부동산 거래 허위 신고 시 처벌은?", "1_공통 매매_임대차", "부동산 거래신고 등에 관한 법률", True),
            ("분양가 공시 의무는?", "3_공급_및_관리_매매_분양", "주택법", True),
            ("공동주택관리법 제14조는?", "3_공급_및_관리_매매_분양", "공동주택관리법", True),
            ("공공분양 vs 민간분양 차이는?", "3_공급_및_관리_매매_분양", "주택법", True),

            # === 3. 중개 계약 관련 (10개) ===
            ("중개보수 요율은 얼마인가요?", "1_공통 매매_임대차", "공인중개사법", True),
            ("중개사 고의 과실 책임은?", "1_공통 매매_임대차", "공인중개사법", True),
            ("중개대상물 확인설명서 교부 의무는?", "1_공통 매매_임대차", "공인중개사법", True),
            ("쌍방대리 금지 원칙은?", "1_공통 매매_임대차", "공인중개사법", True),
            ("중개보수 지급 시기는?", "1_공통 매매_임대차", "공인중개사법", True),
            ("중개계약 해지 사유는?", "1_공통 매매_임대차", "공인중개사법", True),
            ("공인중개사법 제33조는?", "1_공통 매매_임대차", "공인중개사법", True),
            ("부동산 거래계약신고서 작성 의무는?", "1_공통 매매_임대차", "부동산 거래신고 등에 관한 법률", True),
            ("공인중개사 자격시험 과목은?", "1_공통 매매_임대차", "공인중개사법", True),
            ("중개업 등록 요건은?", "1_공통 매매_임대차", "공인중개사법", True),

            # === 4. 임대주택 관련 (8개) ===
            ("민간임대주택 등록 요건은?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("임대사업자 세제 혜택은?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("장기일반민간임대주택이란?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("임대주택 양도 제한 기간은?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("임대료 증액 제한은?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("임대의무기간 위반 시 제재는?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("공공지원민간임대주택이란?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),
            ("임대주택 분양전환 요건은?", "2_임대차_전세_월세", "민간임대주택에 관한 특별법", True),

            # === 5. 기타 부동산 법률 (7개) ===
            ("건축물의 분양에 관한 법률 적용 대상은?", "3_공급_및_관리_매매_분양", "건축물의 분양에 관한 법률", True),
            ("오피스텔 분양 광고 규제는?", "3_공급_및_관리_매매_분양", "건축물의 분양에 관한 법률", True),
            ("부동산 가격공시란?", "4_기타", "부동산 가격공시에 관한 법률", True),
            ("공시지가 이의신청 절차는?", "4_기타", "부동산 가격공시에 관한 법률", True),
            ("부동산등기 특별조치법이란?", "1_공통 매매_임대차", "부동산등기특별조치법", True),
            ("부동산 실권리자명의 등기 의무는?", "1_공통 매매_임대차", "부동산 실권리자명의 등기에 관한 법률", True),
            ("명의신탁 금지란?", "1_공통 매매_임대차", "부동산 실권리자명의 등기에 관한 법률", True),

            # === PART 2: 새로운 50개 - 데이터베이스에 없는 법률 ===

            # === 6. 민법 관련 (없는 법률) - 10개 ===
            ("민법 제618조 임대차 규정은?", "2_임대차_전세_월세", "민법", False),
            ("민법 제103조 반사회질서 행위는?", "1_공통 매매_임대차", "민법", False),
            ("민법 제108조 통정허위표시란?", "1_공통 매매_임대차", "민법", False),
            ("민법 제623조 임대인의 의무는?", "2_임대차_전세_월세", "민법", False),
            ("민법 제303조 전세권의 내용은?", "2_임대차_전세_월세", "민법", False),
            ("민법 제366조 유치권이란?", "1_공통 매매_임대차", "민법", False),
            ("민법 제356조 저당권 설정은?", "1_공통 매매_임대차", "민법", False),
            ("민법 제285조 지상권이란?", "1_공통 매매_임대차", "민법", False),
            ("민법 제569조 매매계약은?", "1_공통 매매_임대차", "민법", False),
            ("민법 제185조 물권변동은?", "1_공통 매매_임대차", "민법", False),

            # === 7. 상가건물 임대차보호법 (없는 법률) - 10개 ===
            ("상가건물 임대차보호법 제10조는?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가건물 권리금 보호 규정은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 환산보증금 기준은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 계약갱신요구권은 몇 년?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가건물 임대차보호법 제2조는?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 임차인 대항력 요건은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 우선변제권 조건은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 차임증액 제한은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 재건축 시 퇴거보상은?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),
            ("상가 임대차 분쟁조정위원회는?", "2_임대차_전세_월세", "상가건물 임대차보호법", False),

            # === 8. 세법 관련 (없는 법률) - 10개 ===
            ("소득세법 제89조 양도소득세율은?", "1_공통 매매_임대차", "소득세법", False),
            ("종합부동산세법 제7조 과세표준은?", "1_공통 매매_임대차", "종합부동산세법", False),
            ("지방세법 제11조 취득세율은?", "1_공통 매매_임대차", "지방세법", False),
            ("상속세 및 증여세법 제41조는?", "1_공통 매매_임대차", "상속세 및 증여세법", False),
            ("법인세법 제55조의2 토지 양도차익은?", "1_공통 매매_임대차", "법인세법", False),
            ("부가가치세법 제12조 과세거래는?", "1_공통 매매_임대차", "부가가치세법", False),
            ("조세특례제한법 제97조의2는?", "1_공통 매매_임대차", "조세특례제한법", False),
            ("지방세특례제한법 제15조는?", "1_공통 매매_임대차", "지방세특례제한법", False),
            ("재산세 과세기준일은?", "1_공통 매매_임대차", "지방세법", False),
            ("농어촌특별세법 적용대상은?", "1_공통 매매_임대차", "농어촌특별세법", False),

            # === 9. 도시개발 관련 (없는 법률) - 10개 ===
            ("도시 및 주거환경정비법 제35조는?", "3_공급_및_관리_매매_분양", "도시 및 주거환경정비법", False),
            ("재건축초과이익 환수에 관한 법률 제5조는?", "3_공급_및_관리_매매_분양", "재건축초과이익 환수에 관한 법률", False),
            ("도시개발법 제21조 환지계획은?", "3_공급_및_관리_매매_분양", "도시개발법", False),
            ("택지개발촉진법 시행령 제7조는?", "3_공급_및_관리_매매_분양", "택지개발촉진법", False),
            ("도시재정비 촉진법이란?", "3_공급_및_관리_매매_분양", "도시재정비 촉진을 위한 특별법", False),
            ("정비사업 조합설립인가 요건은?", "3_공급_및_관리_매매_분양", "도시 및 주거환경정비법", False),
            ("재개발 안전진단 기준은?", "3_공급_및_관리_매매_분양", "도시 및 주거환경정비법", False),
            ("리모델링 수직증축 허용 범위는?", "3_공급_및_관리_매매_분양", "도시 및 주거환경정비법", False),
            ("소규모재건축사업이란?", "3_공급_및_관리_매매_분양", "빈집 및 소규모주택 정비에 관한 특례법", False),
            ("가로주택정비사업 요건은?", "3_공급_및_관리_매매_분양", "빈집 및 소규모주택 정비에 관한 특례법", False),

            # === 10. 기타 특별법 (없는 법률) - 10개 ===
            ("감정평가법 제3조는?", "4_기타", "감정평가 및 감정평가사에 관한 법률", False),
            ("측량법 시행령 제23조는?", "4_기타", "공간정보의 구축 및 관리 등에 관한 법률", False),
            ("건축법 제14조 건축신고는?", "3_공급_및_관리_매매_분양", "건축법", False),
            ("국토계획법 제56조 개발행위허가는?", "3_공급_및_관리_매매_분양", "국토의 계획 및 이용에 관한 법률", False),
            ("농지법 제8조 농지취득자격은?", "4_기타", "농지법", False),
            ("산지관리법 제14조 산지전용허가는?", "4_기타", "산지관리법", False),
            ("개발제한구역법이란?", "4_기타", "개발제한구역의 지정 및 관리에 관한 특별조치법", False),
            ("관광진흥법상 숙박시설 규정은?", "4_기타", "관광진흥법", False),
            ("주차장법 제19조는?", "3_공급_및_관리_매매_분양", "주차장법", False),
            ("하천법상 하천구역 내 행위제한은?", "4_기타", "하천법", False),
        ]

    async def test_single_query(self, query: str, expected_category: str, expected_law: str, should_exist: bool) -> Dict[str, Any]:
        """단일 쿼리 테스트"""
        start_time = time.time()

        try:
            # Supervisor 실행
            app = self.supervisor.workflow.compile()
            initial_state = {
                "query": query,
                "chat_session_id": f"hard_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "shared_context": {},
                "messages": [],
                "todos": [],
                "todo_counter": 0
            }

            final_state = await app.ainvoke(initial_state)
            execution_time = time.time() - start_time

            # 결과 분석
            agent_results = final_state.get("agent_results", {})
            search_result = agent_results.get("search_agent", {})
            collected_data = search_result.get("collected_data", {})
            legal_data = collected_data.get("legal_search", [])

            # 검색 성능 분석
            result_count = len(legal_data) if legal_data else 0
            has_results = result_count > 0

            # "찾을 수 없음" 메시지 확인
            not_found_message = False
            if legal_data and len(legal_data) == 1:
                first_item = legal_data[0]
                if first_item.get("type") == "error" or "찾을 수 없습니다" in str(first_item.get("message", "")):
                    not_found_message = True
                    has_results = False
                    result_count = 0

            # 법률명 매칭 여부
            law_matched = False
            matched_law = None
            top_relevance = 0

            if legal_data and not not_found_message:
                for item in legal_data[:3]:  # 상위 3개만 검사
                    law_title = item.get("law_title", "")
                    relevance = item.get("relevance_score", 0)

                    if relevance > top_relevance:
                        top_relevance = relevance
                        matched_law = law_title

                    if expected_law in law_title:
                        law_matched = True
                        break

            # 카테고리 분석
            used_category = None
            if legal_data and len(legal_data) > 0 and not not_found_message:
                used_category = legal_data[0].get("category", "N/A")

            category_matched = (used_category == expected_category) if used_category else False

            # 존재 여부 검증
            if should_exist:
                # 존재해야 하는 법률 - 결과가 있어야 함
                test_passed = has_results and not not_found_message
            else:
                # 존재하지 않는 법률 - "찾을 수 없음" 메시지가 있거나 결과가 없어야 함
                test_passed = not_found_message or (not has_results)

            return {
                "query": query,
                "status": "success" if test_passed else "failed",
                "should_exist": should_exist,
                "execution_time": round(execution_time, 3),
                "result_count": result_count,
                "has_results": has_results,
                "not_found_message": not_found_message,
                "law_matched": law_matched,
                "expected_law": expected_law,
                "matched_law": matched_law,
                "top_relevance": round(top_relevance, 3),
                "category_matched": category_matched,
                "expected_category": expected_category,
                "used_category": used_category,
                "test_passed": test_passed,
                "top_3_results": [
                    {
                        "law": item.get("law_title"),
                        "article": item.get("article_number"),
                        "relevance": round(item.get("relevance_score", 0), 3)
                    }
                    for item in (legal_data[:3] if legal_data and not not_found_message else [])
                ]
            }

        except Exception as e:
            return {
                "query": query,
                "status": "error",
                "should_exist": should_exist,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "result_count": 0,
                "law_matched": False,
                "category_matched": False,
                "test_passed": False
            }

    async def run_all_tests(self):
        """100개 쿼리 전체 테스트 실행"""
        queries = self.get_hard_queries()

        console.print(f"\n[bold blue]=== Hard Query Test Suite (100 queries) ===[/bold blue]")
        console.print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        console.print(f"[cyan]Part 1: 50 queries for existing laws[/cyan]")
        console.print(f"[yellow]Part 2: 50 queries for non-existent laws[/yellow]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Testing queries...", total=len(queries))

            for i, (query, expected_category, expected_law, should_exist) in enumerate(queries, 1):
                progress.update(task, description=f"[cyan]Testing {i}/{len(queries)}: {query[:50]}...")

                result = await self.test_single_query(query, expected_category, expected_law, should_exist)
                self.test_results.append(result)

                progress.advance(task)

                # Progress feedback
                if result["test_passed"]:
                    if should_exist:
                        status_icon = "[green][OK][/green]" if result["law_matched"] else "[yellow][~][/yellow]"
                    else:
                        status_icon = "[green][V][/green]"  # 없는 법률을 정확히 처리
                else:
                    status_icon = "[red][X][/red]"

                # Part 구분 표시
                if i == 1:
                    console.print("\n[bold cyan]--- Part 1: Existing Laws (1-50) ---[/bold cyan]")
                elif i == 51:
                    console.print("\n[bold yellow]--- Part 2: Non-Existent Laws (51-100) ---[/bold yellow]")

                console.print(f"{status_icon} {i:3d}. {query[:60]:60s} | {result['result_count']:2d} results | {result['execution_time']:.2f}s")

        console.print(f"\n[green]All tests completed![/green]\n")

    def generate_report(self):
        """테스트 결과 보고서 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 통계 계산
        total_tests = len(self.test_results)

        # Part 1 (존재하는 법률) 통계
        part1_results = self.test_results[:50]
        part1_passed = sum(1 for r in part1_results if r["test_passed"])
        part1_law_matched = sum(1 for r in part1_results if r.get("law_matched", False))

        # Part 2 (존재하지 않는 법률) 통계
        part2_results = self.test_results[50:100] if len(self.test_results) >= 100 else self.test_results[50:]
        part2_passed = sum(1 for r in part2_results if r["test_passed"])
        part2_correctly_not_found = sum(1 for r in part2_results if r.get("not_found_message", False) or not r.get("has_results", False))

        # 전체 통계
        total_passed = part1_passed + part2_passed
        total_errors = sum(1 for r in self.test_results if r["status"] == "error")
        avg_execution_time = sum(r["execution_time"] for r in self.test_results) / len(self.test_results)

        # 보고서 생성
        report = {
            "test_name": "Hard Query Test 100",
            "timestamp": timestamp,
            "summary": {
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_tests - total_passed - total_errors,
                "total_errors": total_errors,
                "overall_success_rate": round((total_passed / total_tests) * 100, 2),
                "avg_execution_time": round(avg_execution_time, 3)
            },
            "part1_existing_laws": {
                "total": 50,
                "passed": part1_passed,
                "success_rate": round((part1_passed / 50) * 100, 2) if part1_results else 0,
                "law_matched": part1_law_matched,
                "law_match_rate": round((part1_law_matched / 50) * 100, 2) if part1_results else 0
            },
            "part2_nonexistent_laws": {
                "total": len(part2_results),
                "passed": part2_passed,
                "success_rate": round((part2_passed / len(part2_results)) * 100, 2) if part2_results else 0,
                "correctly_not_found": part2_correctly_not_found,
                "not_found_rate": round((part2_correctly_not_found / len(part2_results)) * 100, 2) if part2_results else 0
            },
            "detailed_results": self.test_results
        }

        # JSON 파일로 저장
        report_file = self.report_path / f"HARD_QUERY_TEST_100_REPORT_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 콘솔 출력
        console.print("\n[bold blue]=== Test Report Summary ===[/bold blue]")

        # 전체 요약 테이블
        summary_table = Table(title="Overall Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        summary_table.add_row("Total Tests", str(total_tests))
        summary_table.add_row("Passed", f"{total_passed} ({round((total_passed/total_tests)*100, 1)}%)")
        summary_table.add_row("Failed", f"{total_tests - total_passed - total_errors}")
        summary_table.add_row("Errors", str(total_errors))
        summary_table.add_row("Avg Execution Time", f"{avg_execution_time:.3f}s")
        console.print(summary_table)

        # Part 1 결과 테이블
        part1_table = Table(title="Part 1: Existing Laws (Questions 1-50)")
        part1_table.add_column("Metric", style="cyan")
        part1_table.add_column("Value", style="green")
        part1_table.add_row("Tests", "50")
        part1_table.add_row("Passed", f"{part1_passed} ({part1_passed/50*100:.1f}%)")
        part1_table.add_row("Law Matched", f"{part1_law_matched} ({part1_law_matched/50*100:.1f}%)")
        console.print(part1_table)

        # Part 2 결과 테이블
        part2_table = Table(title="Part 2: Non-Existent Laws (Questions 51-100)")
        part2_table.add_column("Metric", style="cyan")
        part2_table.add_column("Value", style="yellow")
        part2_table.add_row("Tests", str(len(part2_results)))
        part2_table.add_row("Passed", f"{part2_passed} ({part2_passed/len(part2_results)*100:.1f}%)" if part2_results else "0")
        part2_table.add_row("Correctly Not Found", f"{part2_correctly_not_found} ({part2_correctly_not_found/len(part2_results)*100:.1f}%)" if part2_results else "0")
        console.print(part2_table)

        # 실패한 케이스 출력 (최대 10개)
        failed_cases = [r for r in self.test_results if not r.get("test_passed", False)][:10]
        if failed_cases:
            console.print(f"\n[red]Failed Cases (showing first {len(failed_cases)}):[/red]")
            for case in failed_cases:
                console.print(f"  - Q{self.test_results.index(case)+1}: {case['query'][:60]}")
                if case.get("should_exist"):
                    console.print(f"    Expected: {case['expected_law']}, Got: {case.get('matched_law', 'None')}")
                else:
                    console.print(f"    Should return 'not found' but returned {case['result_count']} results")

        console.print(f"\n[green]Report saved to: {report_file}[/green]")

        return report


async def main():
    """메인 실행 함수"""
    tester = HardQueryTester()

    # 초기화
    await tester.initialize()

    # 테스트 실행
    await tester.run_all_tests()

    # 보고서 생성
    report = tester.generate_report()

    # 성공 기준 확인
    overall_success_rate = report["summary"]["overall_success_rate"]
    part1_success_rate = report["part1_existing_laws"]["success_rate"]
    part2_success_rate = report["part2_nonexistent_laws"]["success_rate"]

    console.print("\n[bold]Success Criteria Check:[/bold]")
    console.print(f"  Overall: {overall_success_rate}% (Target: 80%+) {'✅' if overall_success_rate >= 80 else '❌'}")
    console.print(f"  Part 1 (Existing): {part1_success_rate}% (Target: 85%+) {'✅' if part1_success_rate >= 85 else '❌'}")
    console.print(f"  Part 2 (Non-existent): {part2_success_rate}% (Target: 90%+) {'✅' if part2_success_rate >= 90 else '❌'}")

    return overall_success_rate >= 80


if __name__ == "__main__":
    # Run the test suite
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)