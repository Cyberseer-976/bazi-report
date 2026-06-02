#!/usr/bin/env python3
"""Liu Nian (流年) calculator — on-demand yearly cycle computation.

Takes a saved Ba Zi chart JSON and target years, returns structured
year-by-year stem/branch/ten_god data.  Called by Claude, not end users.

If the chart contains 大运 data, each 流年 is cross-referenced with the
大运 pillar it falls under.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date


# ===========================================================================
# Constants (independent copy — no import from calculate_bazi.py)
# ===========================================================================

STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

ELEMENT_BY_STEM = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
ELEMENT_BY_BRANCH = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}


# ===========================================================================
# Structured error output
# ===========================================================================

def fail(code: str, message: str) -> None:
    """Print a structured error as JSON and exit with code 1."""
    error = {"error": True, "code": code, "message": message}
    print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Core functions
# ===========================================================================

def ganzhi_from_index(index: int) -> dict[str, str]:
    """Return stem + branch for a 0–59 60-cycle index."""
    stem = STEMS[index % 10]
    branch = BRANCHES[index % 12]
    return {
        "stem": stem,
        "branch": branch,
        "text": f"{stem}{branch}",
        "stem_element": ELEMENT_BY_STEM[stem],
        "branch_element": ELEMENT_BY_BRANCH[branch],
    }


def ten_god(day_stem: str, other_stem: str) -> str:
    """Return the 十神 relationship of other_stem relative to day_stem."""
    elements = ["木", "火", "土", "金", "水"]
    polarity = {s: i % 2 for i, s in enumerate(STEMS)}
    d_el = ELEMENT_BY_STEM[day_stem]
    o_el = ELEMENT_BY_STEM[other_stem]
    rel = (elements.index(o_el) - elements.index(d_el)) % 5
    same = polarity[day_stem] == polarity[other_stem]
    table = {
        0: ("比肩", "劫财"), 1: ("食神", "伤官"),
        2: ("偏财", "正财"), 3: ("七杀", "正官"), 4: ("偏印", "正印"),
    }
    return table[rel][0 if same else 1]


def branch_ten_god(day_stem: str, branch: str) -> str:
    """Ten God of a branch (地支) relative to the day stem (日主)."""
    elements = ["木", "火", "土", "金", "水"]
    stem_polarity = {s: i % 2 for i, s in enumerate(STEMS)}
    branch_polarity = {b: i % 2 for i, b in enumerate(BRANCHES)}
    d_el = ELEMENT_BY_STEM[day_stem]
    b_el = ELEMENT_BY_BRANCH[branch]
    rel = (elements.index(b_el) - elements.index(d_el)) % 5
    same = stem_polarity[day_stem] == branch_polarity[branch]
    table = {
        0: ("比肩", "劫财"), 1: ("食神", "伤官"),
        2: ("偏财", "正财"), 3: ("七杀", "正官"), 4: ("偏印", "正印"),
    }
    return table[rel][0 if same else 1]


# ===========================================================================
# CLI
# ===========================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Liu Nian (流年) calculator for Ba Zi charts"
    )
    p.add_argument("--chart", required=True,
                   help="Path to chart JSON from calculate_bazi.py")
    p.add_argument("--years",
                   help="Comma-separated years, e.g. '2026,2027,2028'")
    p.add_argument("--current-plus", type=int,
                   help="Current year + N years to compute, e.g. 5")
    p.add_argument("--output",
                   help="Write output to file instead of stdout")
    return p.parse_args()


def collect_years(args: argparse.Namespace) -> list[int]:
    """Merge all year sources, deduplicate, and return sorted list."""
    years: set[int] = set()

    if args.years:
        for part in args.years.split(","):
            try:
                years.add(int(part.strip()))
            except ValueError:
                fail("INVALID_YEAR",
                     f"无法解析年份 \"{part.strip()}\"，请使用逗号分隔的数字年份。")

    if args.current_plus:
        current_year = date.today().year
        for i in range(1, args.current_plus + 1):
            years.add(current_year + i)

    if not years:
        # Default: current year + next 2 years (3 years total, including this year)
        current_year = date.today().year
        for i in range(0, 3):
            years.add(current_year + i)

    return sorted(years)


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    args = parse_args()

    # Read chart
    try:
        with open(args.chart, "r", encoding="utf-8") as f:
            chart = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        fail("CHART_ERROR", f"无法读取排盘文件: {e}")

    day_stem = chart["day_master"]["stem"]
    dayun = chart.get("dayun")
    years = collect_years(args)

    results = []
    for y in years:
        pillar = ganzhi_from_index((y - 4) % 60)
        entry = {
            "year": y,
            "stem": pillar["stem"],
            "branch": pillar["branch"],
            "text": pillar["text"],
            "stem_element": pillar["stem_element"],
            "branch_element": pillar["branch_element"],
            "ten_god": ten_god(day_stem, pillar["stem"]),
            "branch_ten_god": branch_ten_god(day_stem, pillar["branch"]),
        }

        # Cross-reference with 大运
        if dayun and dayun.get("pillars"):
            for dy in dayun["pillars"]:
                if dy["start_year"] <= y <= dy["end_year"]:
                    entry["dayun_pillar_index"] = dy["index"]
                    entry["dayun_pillar_text"] = dy["text"]
                    entry["dayun_in_range"] = True
                    break
            else:
                entry["dayun_pillar_index"] = None
                entry["dayun_pillar_text"] = None
                entry["dayun_in_range"] = False
        else:
            entry["dayun_pillar_index"] = None
            entry["dayun_pillar_text"] = None
            entry["dayun_in_range"] = False

        results.append(entry)

    output = {
        "liunian": results,
        "dayun_available": dayun is not None and dayun.get("calculated", False),
    }

    text = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
