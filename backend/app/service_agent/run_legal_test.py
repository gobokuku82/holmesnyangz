"""
법률 정보 검색 시스템 대규모 테스트
90개 쿼리를 실행하고 상세한 결과 리포트 생성
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Path setup
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('legal_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class LegalSearchTester:
    """법률 검색 대규모 테스터"""

    def __init__(self, queries_file: str = "test_queries_100.json"):
        """초기화"""
        logger.info("="*80)
        logger.info("Legal Search System - Large Scale Test")
        logger.info("="*80)

        # 쿼리 로드
        self.queries = self._load_queries(queries_file)
        logger.info(f"Loaded {len(self.queries)} test queries")

        # LLM Context 초기화
        try:
            from app.service_agent.core.context import create_default_llm_context
            self.llm_context = create_default_llm_context()
            logger.info(f"LLM Context initialized with API key: {self.llm_context.api_key[:10]}...")
        except Exception as e:
            logger.warning(f"LLM Context initialization failed: {e}")
            self.llm_context = None

        # SearchTeam 초기화
        try:
            from app.service_agent.teams.search_team import SearchTeamSupervisor
            from app.service.core.separated_states import StateManager

            self.SearchTeamSupervisor = SearchTeamSupervisor
            self.StateManager = StateManager

            self.search_team = SearchTeamSupervisor(llm_context=self.llm_context)
            logger.info("SearchTeam initialized successfully with LLM support")

        except Exception as e:
            logger.error(f"Failed to initialize SearchTeam: {e}")
            raise

        # 결과 저장
        self.results = []
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "no_results": 0,
            "with_results": 0,
            "total_time": 0.0,
            "by_category": {}
        }

    def _load_queries(self, filename: str) -> List[Dict]:
        """쿼리 파일 로드"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data["queries"]
        except Exception as e:
            logger.error(f"Failed to load queries: {e}")
            raise

    async def run_single_test(self, query_data: Dict) -> Dict[str, Any]:
        """단일 테스트 실행"""
        query_id = query_data["id"]
        query = query_data["query"]
        category = query_data["category"]
        expected_strategy = query_data["expected_strategy"]

        logger.info(f"\n[{query_id}/90] Testing: {query}")
        logger.info(f"  Category: {category}")
        logger.info(f"  Expected: {expected_strategy}")

        try:
            # 공유 상태 생성
            shared_state = self.StateManager.create_shared_state(
                query=query,
                session_id=f"test_{query_id}"
            )

            # SearchTeam 실행
            start_time = datetime.now()
            result = await self.search_team.execute(
                shared_state,
                search_scope=["legal"]
            )
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            # 결과 분석
            success = result.get("status") == "completed"
            legal_results = result.get("legal_results", [])
            result_count = len(legal_results)

            # 로그 출력
            logger.info(f"  Status: {result.get('status')}")
            logger.info(f"  Results: {result_count} items")
            logger.info(f"  Time: {elapsed:.2f}s")

            if legal_results:
                # 상위 3개 결과 출력
                for i, item in enumerate(legal_results[:3], 1):
                    law_title = item.get('law_title', 'N/A')
                    article_number = item.get('article_number', 'N/A')
                    relevance = item.get('relevance_score', 0)
                    logger.info(f"    [{i}] {law_title} {article_number} (score: {relevance:.3f})")

            return {
                "query_id": query_id,
                "query": query,
                "category": category,
                "expected_strategy": expected_strategy,
                "status": "success" if success else "failed",
                "result_count": result_count,
                "has_results": result_count > 0,
                "elapsed_time": elapsed,
                "top_results": [
                    {
                        "law_title": r.get("law_title", ""),
                        "article_number": r.get("article_number", ""),
                        "article_title": r.get("article_title", ""),
                        "relevance_score": r.get("relevance_score", 0),
                        "content_preview": r.get("content", "")[:200]
                    }
                    for r in legal_results[:5]
                ],
                "full_result": result
            }

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            return {
                "query_id": query_id,
                "query": query,
                "category": category,
                "expected_strategy": expected_strategy,
                "status": "error",
                "error": str(e),
                "result_count": 0,
                "has_results": False,
                "elapsed_time": 0,
                "top_results": []
            }

    async def run_all_tests(self):
        """모든 테스트 실행"""
        logger.info(f"\nStarting test execution: {len(self.queries)} queries")
        logger.info("="*80)

        for query_data in self.queries:
            result = await self.run_single_test(query_data)
            self.results.append(result)

            # 통계 업데이트
            self.stats["total"] += 1
            if result["status"] == "success":
                self.stats["success"] += 1
            else:
                self.stats["failed"] += 1

            if result["has_results"]:
                self.stats["with_results"] += 1
            else:
                self.stats["no_results"] += 1

            self.stats["total_time"] += result.get("elapsed_time", 0)

            # 카테고리별 통계
            category = result["category"]
            if category not in self.stats["by_category"]:
                self.stats["by_category"][category] = {
                    "total": 0,
                    "success": 0,
                    "with_results": 0,
                    "avg_result_count": 0,
                    "total_result_count": 0
                }

            cat_stats = self.stats["by_category"][category]
            cat_stats["total"] += 1
            if result["status"] == "success":
                cat_stats["success"] += 1
            if result["has_results"]:
                cat_stats["with_results"] += 1
            cat_stats["total_result_count"] += result["result_count"]

            # 1초 대기 (부하 방지)
            await asyncio.sleep(0.1)

        # 평균 계산
        for category, cat_stats in self.stats["by_category"].items():
            if cat_stats["total"] > 0:
                cat_stats["avg_result_count"] = cat_stats["total_result_count"] / cat_stats["total"]

        logger.info("\n" + "="*80)
        logger.info("Test Execution Completed")
        logger.info("="*80)

    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        print(f"\nTotal Queries: {self.stats['total']}")
        print(f"Success: {self.stats['success']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        print(f"Failed: {self.stats['failed']}")
        print(f"With Results: {self.stats['with_results']} ({self.stats['with_results']/self.stats['total']*100:.1f}%)")
        print(f"No Results: {self.stats['no_results']}")
        print(f"Total Time: {self.stats['total_time']:.2f}s")
        print(f"Avg Time per Query: {self.stats['total_time']/self.stats['total']:.2f}s")

        print(f"\n{'='*80}")
        print("CATEGORY BREAKDOWN")
        print("="*80)

        for category, cat_stats in sorted(self.stats["by_category"].items()):
            print(f"\n[{category}]")
            print(f"  Total: {cat_stats['total']}")
            print(f"  Success: {cat_stats['success']}")
            print(f"  With Results: {cat_stats['with_results']} ({cat_stats['with_results']/cat_stats['total']*100:.1f}%)")
            print(f"  Avg Results: {cat_stats['avg_result_count']:.1f}")

    def save_report(self, output_dir: str = "reports"):
        """상세 리포트 저장"""
        Path(output_dir).mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/test_result_legal_info_{timestamp}.json"

        report = {
            "test_info": {
                "timestamp": timestamp,
                "total_queries": self.stats["total"],
                "test_duration": self.stats["total_time"],
            },
            "statistics": self.stats,
            "results": self.results
        }

        # datetime 객체 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(v) for v in obj]
            return obj

        report = convert_datetime(report)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\nReport saved: {filename}")
        print(f"\n[SAVED] Detailed report: {filename}")

        # Markdown 리포트도 생성
        self._save_markdown_report(output_dir, timestamp)

    def _save_markdown_report(self, output_dir: str, timestamp: str):
        """Markdown 형식 리포트 생성"""
        filename = f"{output_dir}/test_result_legal_info_{timestamp}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 법률 정보 검색 시스템 테스트 리포트\n\n")
            f.write(f"**테스트 일시:** {timestamp}\n\n")
            f.write(f"**총 쿼리 수:** {self.stats['total']}\n\n")

            f.write("## 📊 전체 통계\n\n")
            f.write(f"- 성공: {self.stats['success']}건 ({self.stats['success']/self.stats['total']*100:.1f}%)\n")
            f.write(f"- 실패: {self.stats['failed']}건\n")
            f.write(f"- 결과 있음: {self.stats['with_results']}건 ({self.stats['with_results']/self.stats['total']*100:.1f}%)\n")
            f.write(f"- 결과 없음: {self.stats['no_results']}건\n")
            f.write(f"- 총 소요 시간: {self.stats['total_time']:.2f}초\n")
            f.write(f"- 평균 응답 시간: {self.stats['total_time']/self.stats['total']:.2f}초\n\n")

            f.write("## 📂 카테고리별 통계\n\n")
            f.write("| 카테고리 | 총 쿼리 | 성공 | 결과율 | 평균 결과 수 |\n")
            f.write("|---------|--------|------|--------|-------------|\n")

            for category, cat_stats in sorted(self.stats["by_category"].items()):
                success_rate = cat_stats['with_results']/cat_stats['total']*100 if cat_stats['total'] > 0 else 0
                f.write(f"| {category} | {cat_stats['total']} | {cat_stats['success']} | {success_rate:.1f}% | {cat_stats['avg_result_count']:.1f} |\n")

            f.write("\n## 🔍 상세 결과\n\n")

            for result in self.results:
                f.write(f"### [{result['query_id']}] {result['query']}\n\n")
                f.write(f"- **카테고리:** {result['category']}\n")
                f.write(f"- **예상 전략:** {result['expected_strategy']}\n")
                f.write(f"- **상태:** {result['status']}\n")
                f.write(f"- **결과 수:** {result['result_count']}건\n")
                f.write(f"- **소요 시간:** {result.get('elapsed_time', 0):.2f}초\n\n")

                if result.get("top_results"):
                    f.write("**상위 결과:**\n\n")
                    for i, top in enumerate(result["top_results"], 1):
                        f.write(f"{i}. **{top['law_title']} {top['article_number']}**\n")
                        if top.get('article_title'):
                            f.write(f"   - 제목: {top['article_title']}\n")
                        f.write(f"   - 관련도: {top['relevance_score']:.3f}\n")
                        f.write(f"   - 내용: {top['content_preview']}...\n\n")
                else:
                    f.write("*결과 없음*\n\n")

                f.write("---\n\n")

        logger.info(f"Markdown report saved: {filename}")
        print(f"[SAVED] Markdown report: {filename}")


async def main():
    """메인 함수"""
    try:
        print("\n" + "="*80)
        print("Legal Information Search System - Large Scale Test")
        print("="*80)

        # Tester 초기화
        tester = LegalSearchTester()

        # 테스트 실행
        await tester.run_all_tests()

        # 결과 요약
        tester.print_summary()

        # 리포트 저장
        tester.save_report()

        print("\n" + "="*80)
        print("Test Completed Successfully")
        print("="*80)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
