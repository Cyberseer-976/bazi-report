#!/usr/bin/env python3
"""Convert Ba Zi chart JSON into report-ready structured notes."""

from __future__ import annotations

import argparse
import json


ELEMENT_ORDER = ["木", "火", "土", "金", "水"]
ELEMENT_MEANINGS = {
    "木": "生发、规划、仁和、成长",
    "火": "表达、热情、礼仪、可见度",
    "土": "承载、稳定、信用、整合",
    "金": "规则、决断、边界、执行",
    "水": "流动、学习、沟通、适应",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    return parser.parse_args()


def _time_certainty(chart: dict) -> str:
    """Determine time certainty label based on chart input and true solar time."""
    true_solar = chart.get("true_solar_time") or {}
    if true_solar.get("applied"):
        return "已知（真太阳时校正）"
    if chart["input"].get("birth_time"):
        return "已知"
    return "未知"


def _calendar_label(chart: dict) -> str:
    """Get human-readable calendar type label."""
    cal = chart["input"].get("calendar", "gregorian")
    return "农历（阴历）" if cal == "lunar" else "公历（阳历）"


def _precision_note(chart: dict) -> str:
    """Extract precision note from chart, with fallback."""
    precision = chart.get("precision", {})
    return precision.get("notes", chart.get("precision_note", ""))


def _dayun_summary(chart: dict) -> dict | None:
    """Build human-readable dayun summary from chart data."""
    dayun = chart.get("dayun")
    if not dayun or not dayun.get("calculated"):
        return None
    return {
        "direction": dayun.get("direction_desc", dayun.get("direction")),
        "starting_age": dayun.get("starting_age"),
        "first_pillar": dayun["pillars"][0]["text"] if dayun.get("pillars") else None,
        "pillar_count": len(dayun.get("pillars", [])),
        "note": f"共 {len(dayun.get('pillars', []))} 步大运，每步 10 年",
    }


def _diagnostics_summary(chart: dict) -> dict | None:
    """Extract key diagnostic facts for report writing."""
    diag = chart.get("diagnostics")
    if not diag:
        return None

    dms = diag.get("day_master_strength", {})
    de_ling = dms.get("de_ling", {})
    de_di = dms.get("de_di", {})
    tong_yi = dms.get("tong_yi_dang", {})
    strength = diag.get("strength_assessment", {})

    return {
        "de_ling_level": de_ling.get("level"),
        "de_ling_note": de_ling.get("relation"),
        "de_ling_score": de_ling.get("numeric_score"),
        "is_de_ling": de_ling.get("is_de_ling"),
        "has_root": de_di.get("has_root"),
        "root_count": de_di.get("root_count"),
        "root_branches": de_di.get("root_branches", []),
        "weighted_root_score": de_di.get("weighted_root_score"),
        "roots_detail": de_di.get("roots", []),
        "tong_dang_count": tong_yi.get("tong_dang"),
        "yi_dang_count": tong_yi.get("yi_dang"),
        "tong_dang_ratio": tong_yi.get("tong_dang_ratio"),
        "weighted_tong_dang": tong_yi.get("weighted_tong_dang"),
        "weighted_yi_dang": tong_yi.get("weighted_yi_dang"),
        "weighted_ratio": tong_yi.get("weighted_ratio"),
        "composite_score": strength.get("composite_score"),
        "strength_label": strength.get("preliminary_label"),
        "strength_note": strength.get("note"),
        "geju_count": len(diag.get("geju_candidates", [])),
        "interaction_count": len(diag.get("branch_interactions", [])),
        "kong_wang_hit": len(diag.get("kong_wang", {}).get("affected_pillars", [])) > 0,
    }


def main() -> None:
    args = parse_args()
    with open(args.input, "r", encoding="utf-8") as f:
        chart = json.load(f)

    counts = chart["elements"]
    sorted_elements = sorted(ELEMENT_ORDER, key=lambda item: counts.get(item, 0), reverse=True)
    strongest = [element for element in sorted_elements if counts.get(element, 0) == counts.get(sorted_elements[0], 0)]
    weakest_count = counts.get(sorted_elements[-1], 0)
    weakest = [element for element in sorted_elements if counts.get(element, 0) == weakest_count]

    day_master = chart["day_master"]
    report = {
        "chart": chart,
        "summary": {
            "day_master": f"{day_master['polarity']}{day_master['element']}日主（{day_master['stem']}）",
            "strongest_elements": strongest,
            "weakest_elements": weakest,
            "element_notes": {element: ELEMENT_MEANINGS[element] for element in ELEMENT_ORDER},
            "time_certainty": _time_certainty(chart),
            "calendar_type": _calendar_label(chart),
            "precision_note": _precision_note(chart),
            "dayun": _dayun_summary(chart),
            "diagnostics": _diagnostics_summary(chart),
        },
        "suggested_sections": [
            "基本排盘",
            "日主强弱",
            "用神喜忌",
            "格局分析",
            "地支关系",
            "五行结构",
            "十神关系",
            "性格与行为模式",
            "事业与工作方式",
            "财务与资源管理",
            "关系与情感模式",
            "生活节律与健康提示",
            "大运/流年",
            "综合建议",
            "免责声明",
        ],
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
