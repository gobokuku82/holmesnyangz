"""
Pre-Refactor Check Script
리팩토링 전 현재 상태를 검증하고 백업
"""

import sys
import json
import importlib
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Backend 디렉토리를 sys.path에 추가
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class PreRefactorChecker:
    """리팩토링 전 검증 도구"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "root_directory": str(root_dir),
            "checks": {},
            "errors": [],
            "warnings": []
        }

    def run_all_checks(self):
        """모든 검증 실행"""
        print("="*70)
        print("PRE-REFACTOR VALIDATION CHECK")
        print("="*70)
        print(f"Target Directory: {self.root_dir}")
        print(f"Timestamp: {self.results['timestamp']}")
        print("="*70 + "\n")

        # 1. Import Map 확인
        self.check_import_map()

        # 2. 파일 구조 스냅샷
        self.create_structure_snapshot()

        # 3. Import 테스트
        self.test_imports()

        # 4. 파일 존재 확인
        self.check_file_existence()

        # 5. 결과 저장
        self.save_results()

        # 6. 최종 리포트
        self.print_summary()

    def check_import_map(self):
        """Import Map 파일 확인"""
        print("[1/5] Checking import_map.json...")

        import_map_path = self.root_dir / "import_map.json"

        if not import_map_path.exists():
            error = "import_map.json not found! Run generate_import_map.py first."
            self.results["errors"].append(error)
            print(f"  [ERROR] {error}")
            return

        try:
            with open(import_map_path, 'r', encoding='utf-8') as f:
                import_map = json.load(f)

            self.results["checks"]["import_map"] = {
                "status": "ok",
                "total_files": import_map["metadata"]["total_files"],
                "total_imports": import_map["metadata"]["total_imports"],
                "generated_at": import_map["metadata"]["generated_at"]
            }

            print(f"  [OK] Import map found")
            print(f"       - Files: {import_map['metadata']['total_files']}")
            print(f"       - Imports: {import_map['metadata']['total_imports']}")

        except Exception as e:
            error = f"Failed to load import_map.json: {e}"
            self.results["errors"].append(error)
            print(f"  [ERROR] {error}")

    def create_structure_snapshot(self):
        """파일 구조 스냅샷 생성"""
        print("\n[2/5] Creating file structure snapshot...")

        try:
            snapshot = []
            snapshot.append(f"File Structure Snapshot")
            snapshot.append(f"Generated: {datetime.now().isoformat()}")
            snapshot.append(f"Root: {self.root_dir}")
            snapshot.append("="*70)
            snapshot.append("")

            # 디렉토리 트리 생성
            for path in sorted(self.root_dir.rglob("*")):
                if "__pycache__" in str(path):
                    continue

                rel_path = path.relative_to(self.root_dir)
                depth = len(rel_path.parts) - 1
                indent = "  " * depth

                if path.is_dir():
                    snapshot.append(f"{indent}[DIR]  {rel_path.name}/")
                else:
                    size = path.stat().st_size
                    snapshot.append(f"{indent}[FILE] {rel_path.name} ({size} bytes)")

            # 파일로 저장
            snapshot_path = self.root_dir / "structure_snapshot.txt"
            with open(snapshot_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(snapshot))

            self.results["checks"]["structure_snapshot"] = {
                "status": "ok",
                "file": str(snapshot_path),
                "total_items": len(snapshot) - 4  # 헤더 제외
            }

            print(f"  [OK] Structure snapshot created: {snapshot_path.name}")
            print(f"       - Total items: {len(snapshot) - 4}")

        except Exception as e:
            error = f"Failed to create structure snapshot: {e}"
            self.results["errors"].append(error)
            print(f"  [ERROR] {error}")

    def test_imports(self):
        """주요 모듈 import 테스트"""
        print("\n[3/5] Testing critical imports...")

        # 테스트할 주요 모듈들
        critical_modules = [
            "app.service_agent.foundation.agent_registry",
            "app.service_agent.foundation.agent_adapter",
            "app.service_agent.foundation.separated_states",
            "app.service_agent.foundation.context",
            "app.service_agent.planning.planning_agent",
            "app.service_agent.supervisor.team_supervisor",
            "app.service_agent.teams.search_team",
            "app.service_agent.teams.analysis_team",
            "app.service_agent.teams.document_team",
        ]

        import_results = []
        success_count = 0
        fail_count = 0

        for module_name in critical_modules:
            try:
                # 모듈 import 시도
                importlib.import_module(module_name)
                import_results.append({
                    "module": module_name,
                    "status": "ok"
                })
                success_count += 1
                print(f"  [OK] {module_name}")

            except Exception as e:
                error_msg = str(e)
                import_results.append({
                    "module": module_name,
                    "status": "error",
                    "error": error_msg
                })
                fail_count += 1
                print(f"  [FAIL] {module_name}")
                print(f"         Error: {error_msg}")

                # 상세 에러는 results에 기록
                self.results["errors"].append(f"Import failed: {module_name} - {error_msg}")

        self.results["checks"]["import_tests"] = {
            "total": len(critical_modules),
            "success": success_count,
            "failed": fail_count,
            "details": import_results
        }

        print(f"\n  Summary: {success_count}/{len(critical_modules)} imports successful")

    def check_file_existence(self):
        """중요 파일 존재 확인"""
        print("\n[4/5] Checking critical file existence...")

        critical_files = [
            "foundation/agent_registry.py",
            "foundation/agent_adapter.py",
            "foundation/separated_states.py",
            "foundation/context.py",
            "foundation/config.py",
            "planning/planning_agent.py",
            "supervisor/team_supervisor.py",
            "teams/search_team.py",
            "teams/analysis_team.py",
            "teams/document_team.py",
            "teams/__init__.py",
        ]

        file_check_results = []
        missing_files = []

        for file_rel_path in critical_files:
            file_path = self.root_dir / file_rel_path
            exists = file_path.exists()

            file_check_results.append({
                "file": file_rel_path,
                "exists": exists,
                "path": str(file_path)
            })

            if exists:
                print(f"  [OK] {file_rel_path}")
            else:
                print(f"  [MISSING] {file_rel_path}")
                missing_files.append(file_rel_path)

        self.results["checks"]["file_existence"] = {
            "total": len(critical_files),
            "exists": len(critical_files) - len(missing_files),
            "missing": len(missing_files),
            "missing_files": missing_files,
            "details": file_check_results
        }

        if missing_files:
            warning = f"{len(missing_files)} critical files are missing"
            self.results["warnings"].append(warning)

    def save_results(self):
        """검증 결과 저장"""
        print("\n[5/5] Saving validation results...")

        try:
            results_path = self.root_dir / "pre_refactor_validation.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)

            print(f"  [OK] Results saved: {results_path.name}")

        except Exception as e:
            print(f"  [ERROR] Failed to save results: {e}")

    def print_summary(self):
        """최종 요약 출력"""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)

        # Import 테스트 결과
        if "import_tests" in self.results["checks"]:
            it = self.results["checks"]["import_tests"]
            print(f"\n[Import Tests]")
            print(f"  Success: {it['success']}/{it['total']}")
            print(f"  Failed:  {it['failed']}/{it['total']}")

        # 파일 존재 확인 결과
        if "file_existence" in self.results["checks"]:
            fe = self.results["checks"]["file_existence"]
            print(f"\n[File Existence]")
            print(f"  Found:   {fe['exists']}/{fe['total']}")
            print(f"  Missing: {fe['missing']}/{fe['total']}")

        # 에러 및 경고
        print(f"\n[Issues]")
        print(f"  Errors:   {len(self.results['errors'])}")
        print(f"  Warnings: {len(self.results['warnings'])}")

        if self.results["errors"]:
            print("\n[ERROR Details]")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"  {i}. {error}")

        if self.results["warnings"]:
            print("\n[WARNING Details]")
            for i, warning in enumerate(self.results["warnings"], 1):
                print(f"  {i}. {warning}")

        # 최종 판정
        print("\n" + "="*70)
        if not self.results["errors"]:
            print("[RESULT] READY FOR REFACTORING")
            print("All critical checks passed. Safe to proceed with refactoring.")
        else:
            print("[RESULT] NOT READY - ISSUES FOUND")
            print("Please fix the errors before proceeding with refactoring.")
        print("="*70)


def main():
    """메인 실행 함수"""
    service_agent_dir = backend_dir / "app" / "service_agent"

    checker = PreRefactorChecker(service_agent_dir)
    checker.run_all_checks()


if __name__ == "__main__":
    main()
