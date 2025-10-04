"""
Import Map Generator
모든 Python 파일의 import 관계를 분석하여 JSON으로 저장
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime

# Backend 디렉토리를 sys.path에 추가
backend_dir = Path(__file__).parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class ImportAnalyzer(ast.NodeVisitor):
    """AST를 사용하여 import 문을 추출하는 방문자"""

    def __init__(self):
        self.imports: List[Dict[str, str]] = []

    def visit_Import(self, node: ast.Import):
        """import xxx 형태 처리"""
        for alias in node.names:
            self.imports.append({
                "type": "import",
                "module": alias.name,
                "alias": alias.asname if alias.asname else None,
                "line": node.lineno
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """from xxx import yyy 형태 처리"""
        module = node.module if node.module else ""
        level = node.level  # relative import의 레벨 (., .., ...)

        for alias in node.names:
            self.imports.append({
                "type": "from_import",
                "module": module,
                "name": alias.name,
                "alias": alias.asname if alias.asname else None,
                "level": level,
                "line": node.lineno
            })
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Dict:
    """파일의 import 정보를 분석"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        return {
            "file_path": str(file_path.relative_to(backend_dir)),
            "absolute_path": str(file_path),
            "imports": analyzer.imports,
            "total_imports": len(analyzer.imports)
        }
    except Exception as e:
        return {
            "file_path": str(file_path.relative_to(backend_dir)),
            "absolute_path": str(file_path),
            "error": str(e),
            "imports": [],
            "total_imports": 0
        }


def get_internal_imports(imports: List[Dict], project_root: str = "app") -> List[Dict]:
    """프로젝트 내부 import만 필터링"""
    internal = []
    for imp in imports:
        module = imp.get("module", "")
        if module.startswith(project_root):
            internal.append(imp)
    return internal


def generate_import_map(root_dir: Path, output_file: Path):
    """전체 import map 생성"""

    print(f"[*] Scanning directory: {root_dir}")

    # 모든 Python 파일 찾기
    py_files = list(root_dir.rglob("*.py"))
    print(f"[*] Found {len(py_files)} Python files")

    # 각 파일 분석
    file_imports = []
    for py_file in py_files:
        # __pycache__ 제외
        if "__pycache__" in str(py_file):
            continue

        print(f"  Analyzing: {py_file.relative_to(root_dir)}")
        analysis = analyze_file(py_file)
        file_imports.append(analysis)

    # Import 통계
    total_imports = sum(f["total_imports"] for f in file_imports)
    files_with_errors = [f for f in file_imports if "error" in f]

    # 내부 import 의존성 그래프 생성
    dependency_graph = {}
    for file_data in file_imports:
        rel_path = file_data["file_path"]
        internal_imports = get_internal_imports(file_data["imports"])

        if internal_imports:
            dependency_graph[rel_path] = {
                "imports": internal_imports,
                "import_count": len(internal_imports)
            }

    # Import map 생성
    import_map = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "root_directory": str(root_dir),
            "total_files": len(py_files),
            "total_imports": total_imports,
            "files_with_errors": len(files_with_errors)
        },
        "files": file_imports,
        "dependency_graph": dependency_graph,
        "errors": files_with_errors if files_with_errors else []
    }

    # JSON으로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(import_map, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Import map generated: {output_file}")
    print(f"[*] Statistics:")
    print(f"   - Total files: {len(py_files)}")
    print(f"   - Total imports: {total_imports}")
    print(f"   - Files with errors: {len(files_with_errors)}")
    print(f"   - Internal dependencies: {len(dependency_graph)}")

    return import_map


def print_summary(import_map: Dict):
    """Import map 요약 출력"""
    print("\n" + "="*60)
    print("IMPORT MAP SUMMARY")
    print("="*60)

    dep_graph = import_map["dependency_graph"]

    # 가장 많이 import되는 모듈
    module_usage = {}
    for file_path, data in dep_graph.items():
        for imp in data["imports"]:
            module = imp.get("module", "")
            if module:
                module_usage[module] = module_usage.get(module, 0) + 1

    print("\n[TOP 10] Most Imported Modules:")
    sorted_modules = sorted(module_usage.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (module, count) in enumerate(sorted_modules, 1):
        print(f"   {i:2d}. {module} ({count} times)")

    # 가장 많은 import를 가진 파일
    print("\n[TOP 10] Files with Most Imports:")
    sorted_files = sorted(dep_graph.items(), key=lambda x: x[1]["import_count"], reverse=True)[:10]
    for i, (file_path, data) in enumerate(sorted_files, 1):
        print(f"   {i:2d}. {file_path} ({data['import_count']} imports)")

    print("\n" + "="*60)


if __name__ == "__main__":
    # 디렉토리 설정
    service_agent_dir = backend_dir / "app" / "service_agent"
    output_file = service_agent_dir / "import_map.json"

    print("Import Map Generator")
    print("="*60)

    # Import map 생성
    import_map = generate_import_map(service_agent_dir, output_file)

    # 요약 출력
    print_summary(import_map)

    print(f"\n[SAVED] Import map saved to: {output_file}")
