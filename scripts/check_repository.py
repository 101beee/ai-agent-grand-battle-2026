"""로컬 Markdown 링크, 공란 결과, 배포 금지 파일 유무를 확인한다."""
from pathlib import Path
import re

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
for path in ROOT.rglob("*"):
    if ".git" in path.parts or ".venv" in path.parts:
        continue
    if path.is_file() and (path.name == ".env" or path.suffix == ".log" or "runs" in path.parts):
        errors.append(f"배포 제외 파일: {path.relative_to(ROOT)}")
if errors:
    raise SystemExit("\n".join(errors))
print("Repository links and distribution files OK")
