import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("leaderboard", ROOT / "scripts/update_leaderboard.py")
lb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lb)


class LeaderboardTests(unittest.TestCase):
    def read(self, body):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.csv"
            path.write_text("team,solved,elapsed_seconds,presentation_url\n" + body, encoding="utf-8")
            return lb.read_results(path)

    def test_empty_has_seven_blank_rows(self):
        rows = self.read("")
        self.assertEqual(rows, [])
        self.assertEqual(lb.table(rows).count("|  |  |  |  |  |"), 7)

    def test_solved_then_time_and_equal_rank(self):
        rows = self.read("느린팀,3,200,\n빠른팀,3,100,\n동률팀,3,100,\n많이푼팀,4,500,\n")
        self.assertEqual([r[1:3] for r in rows], [(4, 500), (3, 100), (3, 100), (3, 200)])
        rendered = lb.table(rows)
        self.assertEqual(rendered.count("| 2 |"), 2)
        self.assertIn("| 4 | 느린팀", rendered)

    def test_rejects_invalid_and_duplicate_results(self):
        for body in ["a,1,NaN,\n", "a,1,-1,\n", "a,1.5,2,\n", "a,1,2,javascript:alert\n", "a,1,2,\na,1,3,\n"]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.read(body)

    def test_english_and_korean_results_keep_the_same_scores(self):
        rows = self.read("TeamA,3,12.5,https://example.com/demo\n")
        english, korean = lb.table(rows, "en"), lb.table(rows, "ko")
        self.assertIn("| Rank | Team | Solved |", english)
        self.assertIn("| 순위 | 팀명 | 해결 문제 수 |", korean)
        self.assertIn("| 1 | TeamA | 3 | 12.5s | [View]", english)
        self.assertIn("| 1 | TeamA | 3 | 12.5초 | [보기]", korean)


if __name__ == "__main__":
    unittest.main()
