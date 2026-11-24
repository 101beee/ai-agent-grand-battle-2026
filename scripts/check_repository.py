"""문서 링크와 배포 파일을 검사한다."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
errors = []
for path in ROOT.rglob("*.md"):
    if ".venv" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    targets = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text)
    targets += re.findall(r'<img[^>]+src="([^"]+)"', text)
    for target in targets:
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        local = target.split("#", 1)[0]
        if local and not (path.parent / local).exists():
            errors.append(f"링크 없음: {path.relative_to(ROOT)} → {target}")
result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
if result.returncode == 0 and Path(result.stdout.strip()).resolve() == ROOT:
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, check=True)
    for relative in tracked.stdout.split("\0"):
        if not relative:
            continue
        path = Path(relative)
        if path.name == ".env" or path.suffix == ".log" or "runs" in path.parts:
            errors.append(f"배포 제외 파일: {relative}")
if errors:
    raise SystemExit("\n".join(errors))
print("Repository links and distribution files OK")
