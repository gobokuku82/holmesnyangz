"""
임베딩 실행 전 사전 점검 스크립트

실행 방법:
    python backend/data/storage/legal_info/embedding/pre_check.py
"""

import sys
from pathlib import Path
import json

def check_python_version():
    """Python 버전 확인 (3.8 이상 필요)"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"[OK] Python 버전: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"[FAIL] Python 버전: {version.major}.{version.minor}.{version.micro} (3.8 이상 필요)")
        return False


def check_packages():
    """필수 패키지 설치 확인"""
    packages = {
        "chromadb": "chromadb",
        "sentence_transformers": "sentence-transformers",
        "torch": "torch"
    }

    all_ok = True
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print(f"[OK] {package_name} 설치됨")
        except ImportError:
            print(f"[FAIL] {package_name} 설치 필요: pip install {package_name}")
            all_ok = False

    return all_ok


def check_paths():
    """파일 경로 확인"""
    project_root = Path(__file__).resolve().parents[5]

    paths = {
        "청킹 파일 디렉토리": project_root / "backend" / "data" / "storage" / "legal_info" / "chunked",
        "ChromaDB 디렉토리": project_root / "backend" / "data" / "storage" / "legal_info" / "chroma_db",
        "임베딩 모델": project_root / "backend" / "app" / "service" / "models" / "kure_v1",
    }

    all_ok = True
    for name, path in paths.items():
        if path.exists():
            print(f"[OK] {name}: {path}")
        else:
            print(f"[FAIL] {name} 없음: {path}")
            all_ok = False

    return all_ok


def check_chunked_files():
    """청킹 파일 확인"""
    project_root = Path(__file__).resolve().parents[5]
    chunked_dir = project_root / "backend" / "data" / "storage" / "legal_info" / "chunked"

    if not chunked_dir.exists():
        print("[FAIL] 청킹 디렉토리 없음")
        return False

    categories = [
        "1_공통 매매_임대차",
        "2_임대차_전세_월세",
        "3_공급_및_관리_매매_분양",
        "4_기타"
    ]

    total_files = 0
    total_chunks = 0

    print("\n[INFO] 청킹 파일 분석:")
    for category in categories:
        category_path = chunked_dir / category
        if not category_path.exists():
            print(f"   [WARN] {category} 폴더 없음")
            continue

        json_files = list(category_path.glob("*_chunked.json"))
        file_count = len(json_files)

        # 청크 개수 계산
        chunk_count = 0
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                    chunk_count += len(chunks)
            except:
                pass

        total_files += file_count
        total_chunks += chunk_count

        print(f"   - {category}: {file_count}개 파일, {chunk_count}개 청크")

    print(f"\n[OK] 전체: {total_files}개 파일, {total_chunks}개 청크")

    if total_files < 20:
        print("[WARN] 경고: 파일 개수가 적습니다 (예상: 28개)")
    if total_chunks < 1500:
        print("[WARN] 경고: 청크 개수가 적습니다 (예상: 1700개)")

    return total_files > 0


def check_disk_space():
    """디스크 여유 공간 확인"""
    import shutil

    project_root = Path(__file__).resolve().parents[5]
    chroma_path = project_root / "backend" / "data" / "storage" / "legal_info" / "chroma_db"

    try:
        stat = shutil.disk_usage(chroma_path.parent)
        free_gb = stat.free / (1024**3)

        if free_gb > 1.0:
            print(f"[OK] 디스크 여유 공간: {free_gb:.2f} GB")
            return True
        else:
            print(f"[WARN] 디스크 여유 공간 부족: {free_gb:.2f} GB (1GB 이상 권장)")
            return False
    except Exception as e:
        print(f"[WARN] 디스크 공간 확인 실패: {e}")
        return True


def check_gpu():
    """GPU 사용 가능 여부 확인 (선택사항)"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[OK] GPU 사용 가능: {gpu_name}")
            return True
        else:
            print("[INFO] GPU 없음 (CPU 사용 - 속도 느림)")
            return True
    except ImportError:
        print("[INFO] PyTorch 없음 (GPU 확인 불가)")
        return True


def main():
    print("="*60)
    print("ChromaDB 재임베딩 사전 점검")
    print("="*60 + "\n")

    checks = [
        ("Python 버전", check_python_version),
        ("필수 패키지", check_packages),
        ("파일 경로", check_paths),
        ("청킹 파일", check_chunked_files),
        ("디스크 공간", check_disk_space),
        ("GPU", check_gpu),
    ]

    results = {}
    for name, check_func in checks:
        print(f"\n{'='*60}")
        print(f"[{name}]")
        print("="*60)
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"[FAIL] 점검 실패: {e}")
            results[name] = False

    # 최종 결과
    print(f"\n{'='*60}")
    print("[SUMMARY] 점검 결과 요약")
    print("="*60)

    critical_checks = ["Python 버전", "필수 패키지", "파일 경로", "청킹 파일"]
    optional_checks = ["디스크 공간", "GPU"]

    critical_ok = all(results.get(check, False) for check in critical_checks)

    for check in critical_checks:
        status = "[OK]" if results.get(check, False) else "[FAIL]"
        print(f"{status} {check}")

    print("\n선택사항:")
    for check in optional_checks:
        status = "[OK]" if results.get(check, False) else "[WARN]"
        print(f"{status} {check}")

    print("\n" + "="*60)
    if critical_ok:
        print("[SUCCESS] 모든 필수 조건 충족!")
        print("\n다음 명령어로 실행 가능:")
        print("  python backend/data/storage/legal_info/embedding/embed_legal_documents.py --test")
    else:
        print("[FAIL] 필수 조건 미충족")
        print("\n위의 [FAIL] 항목을 해결 후 다시 실행하세요.")
    print("="*60)


if __name__ == "__main__":
    main()
