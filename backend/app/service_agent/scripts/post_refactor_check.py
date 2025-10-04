"""
Post-Refactor Check Script
리팩토링 후 변경사항을 검증하고 이전 상태와 비교
"""

import sys
import json
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# Backend 디렉토리를 sys.path에 추가
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class PostRefactorChecker:
    """리팩토링 후 검증 도구"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.pre_validation = None
        self.pre_import_map = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "root_directory": str(root_dir),
            "checks": {},
            "errors": [],
            "warnings": [],
            "changes": {}
        }

    def run_all_checks(self):
        """모든 검증 실행"""
        print("="*70)
        print("POST-REFACTOR VALIDATION CHECK")
        print("="*70)
        print(f"Target Directory: {self.root_dir}")
        print(f"Timestamp: {self.results['timestamp']}")
        print("="*70 + "\n")

        # 1. Pre-refactor 데이터 로드
        self.load_pre_refactor_data()

        # 2. Import 테스트
        self.test_imports()

        # 3. 파일 구조 변경 확인
        self.check_structure_changes()

        # 4. Import 의존성 변경 확인
        self.check_import_changes()

        # 5. 결과 저장
        self.save_results()

        # 6. 최종 리포트
        self.print_summary()

    def load_pre_refactor_data(self):
        """리팩토링 전 데이터 로드"""
        print("[1/5] Loading pre-refactor data...")

        # Pre-validation 결과 로드
        pre_validation_path = self.root_dir / "pre_refactor_validation.json"
        if pre_validation_path.exists():
            try:
                with open(pre_validation_path, 'r', encoding='utf-8') as f:
                    self.pre_validation = json.load(f)
                print(f"  [OK] Loaded pre_refactor_validation.json")
            except Exception as e:
                self.results["warnings"].append(f"Failed to load pre-validation: {e}")
                print(f"  [WARN] Could not load pre_refactor_validation.json: {e}")
        else:
            self.results["warnings"].append("pre_refactor_validation.json not found")
            print(f"  [WARN] pre_refactor_validation.json not found")

        # Import map 로드
        import_map_path = self.root_dir / "import_map.json"
        if import_map_path.exists():
            try:
                with open(import_map_path, 'r', encoding='utf-8') as f:
                    self.pre_import_map = json.load(f)
                print(f"  [OK] Loaded import_map.json (pre-refactor)")
            except Exception as e:
                self.results["warnings"].append(f"Failed to load import_map: {e}")
                print(f"  [WARN] Could not load import_map.json: {e}")
        else:
            self.results["warnings"].append("import_map.json not found")
            print(f"  [WARN] import_map.json not found")

    def test_imports(self):
        """주요 모듈 import 테스트 (리팩토링 후)"""
        print("\n[2/5] Testing imports after refactoring...")

        # 테스트할 주요 모듈들 - 리팩토링 후 새로운 구조 반영
        critical_modules = [
            # Foundation
            "app.service_agent.foundation.agent_registry",
            "app.service_agent.foundation.agent_adapter",
            "app.service_agent.foundation.separated_states",
            "app.service_agent.foundation.context",

            # Cognitive Agents (ReAct Think Layer)
            "app.service_agent.cognitive_agents.planning_agent",

            # Supervisor
            "app.service_agent.supervisor.team_supervisor",

            # Execution Agents (ReAct Act Layer)
            "app.service_agent.execution_agents.search_executor",
            "app.service_agent.execution_agents.analysis_executor",
            "app.service_agent.execution_agents.document_executor",
        ]

        import_results = []
        success_count = 0
        fail_count = 0

        for module_name in critical_modules:
            try:
                # 모듈 캐시 제거 후 재import
                if module_name in sys.modules:
                    del sys.modules[module_name]

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

                self.results["errors"].append(f"Import failed: {module_name} - {error_msg}")

        self.results["checks"]["import_tests"] = {
            "total": len(critical_modules),
            "success": success_count,
            "failed": fail_count,
            "details": import_results
        }

        print(f"\n  Summary: {success_count}/{len(critical_modules)} imports successful")

        # Pre-refactor와 비교
        if self.pre_validation and "import_tests" in self.pre_validation.get("checks", {}):
            pre_success = self.pre_validation["checks"]["import_tests"]["success"]
            if success_count < pre_success:
                warning = f"Import success count decreased: {pre_success} -> {success_count}"
                self.results["warnings"].append(warning)
                print(f"  [WARN] {warning}")
            elif success_count > pre_success:
                print(f"  [IMPROVED] Import success increased: {pre_success} -> {success_count}")

    def check_structure_changes(self):
        """파일 구조 변경사항 확인"""
        print("\n[3/5] Checking file structure changes...")

        # 현재 파일 목록 생성
        current_files = set()
        for path in self.root_dir.rglob("*"):
            if "__pycache__" in str(path) or path.is_dir():
                continue
            rel_path = str(path.relative_to(self.root_dir))
            current_files.add(rel_path)

        # Pre-refactor 파일 목록 로드
        pre_files = set()
        snapshot_path = self.root_dir / "structure_snapshot.txt"
        if snapshot_path.exists():
            try:
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if "[FILE]" in line:
                            # Extract file path from snapshot
                            # Format: "  [FILE] filename.py (size bytes)"
                            parts = line.strip().split("[FILE]")
                            if len(parts) > 1:
                                file_info = parts[1].strip().split("(")[0].strip()
                                # Reconstruct path - this is simplified
                                pre_files.add(file_info)
            except Exception as e:
                self.results["warnings"].append(f"Failed to parse structure snapshot: {e}")

        # 변경사항 분석
        added_files = current_files - pre_files
        removed_files = pre_files - current_files

        self.results["changes"]["files"] = {
            "added": list(added_files),
            "removed": list(removed_files),
            "added_count": len(added_files),
            "removed_count": len(removed_files)
        }

        print(f"  Files added: {len(added_files)}")
        if added_files:
            for f in sorted(added_files)[:5]:  # Show first 5
                print(f"    + {f}")
            if len(added_files) > 5:
                print(f"    ... and {len(added_files) - 5} more")

        print(f"  Files removed: {len(removed_files)}")
        if removed_files:
            for f in sorted(removed_files)[:5]:  # Show first 5
                print(f"    - {f}")
            if len(removed_files) > 5:
                print(f"    ... and {len(removed_files) - 5} more")

    def check_import_changes(self):
        """Import 의존성 변경 확인"""
        print("\n[4/5] Checking import dependency changes...")

        if not self.pre_import_map:
            print("  [SKIP] No pre-refactor import map available")
            return

        # 새로운 import map 생성
        try:
            from generate_import_map import generate_import_map
            new_import_map_path = self.root_dir / "import_map_post.json"
            new_import_map = generate_import_map(self.root_dir, new_import_map_path)

            # 통계 비교
            pre_stats = self.pre_import_map["metadata"]
            new_stats = new_import_map["metadata"]

            changes = {
                "total_files": {
                    "before": pre_stats["total_files"],
                    "after": new_stats["total_files"],
                    "diff": new_stats["total_files"] - pre_stats["total_files"]
                },
                "total_imports": {
                    "before": pre_stats["total_imports"],
                    "after": new_stats["total_imports"],
                    "diff": new_stats["total_imports"] - pre_stats["total_imports"]
                }
            }

            self.results["changes"]["imports"] = changes

            print(f"  Total files: {pre_stats['total_files']} -> {new_stats['total_files']} "
                  f"({changes['total_files']['diff']:+d})")
            print(f"  Total imports: {pre_stats['total_imports']} -> {new_stats['total_imports']} "
                  f"({changes['total_imports']['diff']:+d})")

        except Exception as e:
            warning = f"Failed to generate new import map: {e}"
            self.results["warnings"].append(warning)
            print(f"  [WARN] {warning}")

    def save_results(self):
        """검증 결과 저장"""
        print("\n[5/5] Saving validation results...")

        try:
            results_path = self.root_dir / "post_refactor_validation.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)

            print(f"  [OK] Results saved: {results_path.name}")

        except Exception as e:
            print(f"  [ERROR] Failed to save results: {e}")

    def print_summary(self):
        """최종 요약 출력"""
        print("\n" + "="*70)
        print("POST-REFACTOR VALIDATION SUMMARY")
        print("="*70)

        # Import 테스트 결과
        if "import_tests" in self.results["checks"]:
            it = self.results["checks"]["import_tests"]
            print(f"\n[Import Tests]")
            print(f"  Success: {it['success']}/{it['total']}")
            print(f"  Failed:  {it['failed']}/{it['total']}")

        # 파일 변경사항
        if "files" in self.results["changes"]:
            fc = self.results["changes"]["files"]
            print(f"\n[File Changes]")
            print(f"  Added:   {fc['added_count']}")
            print(f"  Removed: {fc['removed_count']}")

        # Import 변경사항
        if "imports" in self.results["changes"]:
            ic = self.results["changes"]["imports"]
            print(f"\n[Import Changes]")
            print(f"  Files:   {ic['total_files']['before']} -> {ic['total_files']['after']}")
            print(f"  Imports: {ic['total_imports']['before']} -> {ic['total_imports']['after']}")

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
            print("[RESULT] REFACTORING SUCCESSFUL")
            print("All critical imports working. Refactoring completed successfully.")
        else:
            print("[RESULT] REFACTORING INCOMPLETE - ISSUES FOUND")
            print("Please fix the errors to complete the refactoring.")
        print("="*70)


def main():
    """메인 실행 함수"""
    service_agent_dir = backend_dir / "app" / "service_agent"

    checker = PostRefactorChecker(service_agent_dir)
    checker.run_all_checks()


if __name__ == "__main__":
    main()
