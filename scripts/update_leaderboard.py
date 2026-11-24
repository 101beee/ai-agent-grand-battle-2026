"""결과 CSV로 README와 리더보드를 갱신한다."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- LEADERBOARD:START -->", "<!-- LEADERBOARD:END -->"
FIELDS = ["team", "solved", "elapsed_seconds", "presentation_url"]


def read_results(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"CSV 헤더는 {','.join(FIELDS)}여야 합니다.")
        rows, teams = [], set()
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"{line}행: 열 수를 확인하세요.")
            row = {k: v.strip() for k, v in row.items()}
            team = row["team"]
            if not team or team in teams or any(c in team for c in "\n\r|<>[]\\`*_"):
                raise ValueError(f"{line}행: 팀명은 비어 있거나 중복, Markdown 특수문자를 포함할 수 없습니다.")
            try:
                solved = int(row["solved"])
                seconds = Decimal(row["elapsed_seconds"])
            except (ValueError, InvalidOperation) as exc:
                raise ValueError(f"{line}행: 해결 수는 정수, 시간은 초 단위 숫자여야 합니다.") from exc
            if solved < 0 or not seconds.is_finite() or seconds < 0:
                raise ValueError(f"{line}행: 해결 수와 시간은 유한한 0 이상의 값이어야 합니다.")
            url = row["presentation_url"]
            if url:
                parsed = urlsplit(url)
                if parsed.scheme != "https" or not parsed.netloc or any(c in url for c in "\n\r|<>() "):
                    raise ValueError(f"{line}행: 발표 링크는 공백 없는 HTTPS URL이어야 합니다.")
            teams.add(team)
            rows.append((team, solved, seconds, url))
    if len(rows) > 7:
        raise ValueError("참가팀 수는 최대 7팀입니다.")
    return sorted(rows, key=lambda r: (-r[1], r[2], r[0]))


def table(rows):
    lines = ["| 순위 | 팀명 | 해결 문제 수 | 수행 시간 | 발표 / 시연 |",
             "|:---:|---|:---:|:---:|---|"]
    previous, rank = None, 0
    for index, (team, solved, seconds, url) in enumerate(rows, 1):
        key = (solved, seconds)
        if key != previous:
            rank = index
        previous = key
        link = f"[보기]({url})" if url else ""
        lines.append(f"| {rank} | {team} | {solved} | {seconds:f}초 | {link} |")
    lines.extend(["|  |  |  |  |  |"] * (7 - len(rows)))
    return "\n".join(lines)


def replace_table(text, rendered):
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("리더보드 표 구분자를 확인하세요.")
    before, rest = text.split(START)
    _, after = rest.split(END)
    return f"{before}{START}\n{rendered}\n{END}{after}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="파일 변경 없이 동기화 상태 확인")
    args = parser.parse_args()
    rendered = table(read_results(ROOT / "leaderboard/results.csv"))
    pending = []
    for relative in ["README.md", "leaderboard/README.md"]:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        pending.append((path, text, replace_table(text, rendered)))
    if args.check:
        if any(old != new for _, old, new in pending):
            raise SystemExit("리더보드가 CSV와 다릅니다. update_leaderboard.py를 실행하세요.")
    else:
        for path, _, new in pending:
            path.write_text(new, encoding="utf-8")
    print("Leaderboard OK")


if __name__ == "__main__":
    main()
