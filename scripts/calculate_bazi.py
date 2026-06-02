#!/usr/bin/env python3
"""Ba Zi chart calculator — deterministic computation only.

This is a CLI tool called by Claude, not by end users. It accepts structured
input and returns structured JSON. Claude handles all conversation,
information gathering, and interpretation.

Supports: Gregorian & Lunar input, true solar time correction.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Lunar calendar support
# ---------------------------------------------------------------------------
try:
    from lunar import Lunar, Solar
except ImportError:
    try:
        from lunar_python import Lunar, Solar
    except ImportError:
        Lunar = None
        Solar = None


# ===========================================================================
# Constants
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
HIDDEN_STEMS = {
    "子": ["癸"], "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"],
    "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

# Approximate jie boundaries (month pillar starts at 寅 on 立春)
SOLAR_MONTH_STARTS = [
    ((2, 4), "寅"), ((3, 6), "卯"), ((4, 5), "辰"),
    ((5, 6), "巳"), ((6, 6), "午"), ((7, 7), "未"),
    ((8, 8), "申"), ((9, 8), "酉"), ((10, 8), "戌"),
    ((11, 7), "亥"), ((12, 7), "子"), ((1, 6), "丑"),
]

# Build 60-cycle reverse lookup at module load time
_ganzhi_to_index: dict[tuple[str, str], int] = {}
for _i in range(60):
    _ganzhi_to_index[(STEMS[_i % 10], BRANCHES[_i % 12])] = _i


# ===========================================================================
# Structured error output
# ===========================================================================

def fail(code: str, message: str) -> None:
    """Print a structured error as JSON and exit with code 1.

    Claude reads this JSON to decide how to respond to the user.
    """
    error = {"error": True, "code": code, "message": message}
    print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Core calculation (unchanged)
# ===========================================================================

@dataclass(frozen=True)
class Pillar:
    stem: str
    branch: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stem": self.stem,
            "branch": self.branch,
            "text": f"{self.stem}{self.branch}",
            "stem_element": ELEMENT_BY_STEM[self.stem],
            "branch_element": ELEMENT_BY_BRANCH[self.branch],
        }


def ganzhi_from_index(index: int) -> Pillar:
    return Pillar(STEMS[index % 10], BRANCHES[index % 12])


def effective_solar_year(d: date) -> int:
    return d.year if (d.month, d.day) >= (2, 4) else d.year - 1


def year_pillar(d: date) -> Pillar:
    return ganzhi_from_index((effective_solar_year(d) - 4) % 60)


def month_branch(d: date) -> str:
    md = (d.month, d.day)
    current = "丑"
    for start, branch in SOLAR_MONTH_STARTS:
        if start[0] == 1:
            continue
        if md >= start:
            current = branch
    if md >= (12, 7) or md < (1, 6):
        return "子"
    if md >= (1, 6) and md < (2, 4):
        return "丑"
    return current


def month_pillar(d: date) -> Pillar:
    y = effective_solar_year(d)
    y_stem = (y - 4) % 10
    branch = month_branch(d)
    offset = BRANCHES.index(branch) - BRANCHES.index("寅")
    if offset < 0:
        offset += 12
    yin_stem = ((y_stem % 5) * 2 + 2) % 10
    return Pillar(STEMS[(yin_stem + offset) % 10], branch)


def day_pillar(d: date) -> Pillar:
    base = date(1900, 1, 31)   # 甲辰 day
    base_index = 40
    delta = (d - base).days
    return ganzhi_from_index((base_index + delta) % 60)


def hour_branch(t: time) -> str:
    return "子" if t.hour == 23 else BRANCHES[((t.hour + 1) // 2) % 12]


def hour_pillar(day: Pillar, t: time) -> Pillar:
    branch = hour_branch(t)
    b_idx = BRANCHES.index(branch)
    d_idx = STEMS.index(day.stem)
    zi_stem = (d_idx % 5) * 2
    return Pillar(STEMS[(zi_stem + b_idx) % 10], branch)


def ten_god(day_stem: str, other_stem: str) -> str:
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
    """Ten God of a branch (地支) relative to the day stem (日主).

    Uses the branch's main element and yin/yang polarity.
    """
    elements = ["木", "火", "土", "金", "水"]
    stem_polarity = {s: i % 2 for i, s in enumerate(STEMS)}       # 0=阳, 1=阴
    branch_polarity = {b: i % 2 for i, b in enumerate(BRANCHES)}  # 子阳丑阴…
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
# 60-cycle index lookup (inverse of ganzhi_from_index)
# ===========================================================================

def ganzhi_to_index(pillar: Pillar) -> int:
    """Return 0–59 index in the 60-cycle for a given Pillar."""
    return _ganzhi_to_index[(pillar.stem, pillar.branch)]


# ===========================================================================
# Da Yun (大运) calculation
# ===========================================================================

def is_yang_stem(stem: str) -> bool:
    """True if stem is 阳 (odd-index: 甲丙戊庚壬)."""
    return STEMS.index(stem) % 2 == 0


def dayun_direction(year_stem: str, gender: str) -> str:
    """Return "顺" or "逆" for Da Yun direction.

    Male (男) + Yang Year (阳年) → 顺排 (forward)
    Male + Yin Year → 逆排 (backward)
    Female (女) + Yang Year → 逆排
    Female + Yin Year → 顺排
    """
    yang = is_yang_stem(year_stem)
    male = gender == "男"
    return "顺" if male == yang else "逆"


def calculate_dayun(
    birth_date: date,
    month_pillar: Pillar,
    day_stem: str,
    gender: str,
    year_pillar: Pillar,
) -> dict:
    """Compute 8 Da Yun luck pillars (10-year cycles).

    Uses lunar-python for precise solar term (节气) dates.
    Requires gender to be "男" or "女".
    """
    if Lunar is None or Solar is None:
        fail("LUNAR_NOT_INSTALLED",
             "lunar-python 库未安装，无法计算大运（需要精确节气日期）。"
             "请运行 pip install lunar-python。")

    # 1. Direction
    direction = dayun_direction(year_pillar.stem, gender)
    yang_label = "阳" if is_yang_stem(year_pillar.stem) else "阴"
    direction_desc = f"{gender}命{yang_label}年{'顺排' if direction == '顺' else '逆排'}"

    # 2. Precise solar term dates from lunar-python
    solar_obj = Solar.fromYmd(birth_date.year, birth_date.month, birth_date.day)
    lunar = solar_obj.getLunar()

    if direction == "顺":
        next_jie = lunar.getNextJie()
        jie_solar = next_jie.getSolar()
        jie_date = date(jie_solar.getYear(), jie_solar.getMonth(), jie_solar.getDay())
        jie_name = next_jie.getName()
        days_diff = (jie_date - birth_date).days
    else:
        prev_jie = lunar.getPrevJie()
        jie_solar = prev_jie.getSolar()
        jie_date = date(jie_solar.getYear(), jie_solar.getMonth(), jie_solar.getDay())
        jie_name = prev_jie.getName()
        days_diff = (birth_date - jie_date).days

    # 3. Starting age: 3 days = 1 year
    starting_age_years = days_diff // 3
    starting_age_months = (days_diff % 3) * 4  # each remaining day ≈ 4 months

    # 4. Generate 8 luck pillars (each 10 years)
    month_idx = ganzhi_to_index(month_pillar)
    pillars = []

    for i in range(8):
        if direction == "顺":
            idx = (month_idx + 1 + i) % 60
        else:
            idx = (month_idx - 1 - i) % 60

        pillar = ganzhi_from_index(idx)
        start_age = starting_age_years + i * 10
        end_age = start_age + 9  # 10-year span: ages [start, end]

        pillars.append({
            "index": i + 1,
            "stem": pillar.stem,
            "branch": pillar.branch,
            "text": f"{pillar.stem}{pillar.branch}",
            "stem_element": ELEMENT_BY_STEM[pillar.stem],
            "branch_element": ELEMENT_BY_BRANCH[pillar.branch],
            "ten_god": ten_god(day_stem, pillar.stem),
            "branch_ten_god": branch_ten_god(day_stem, pillar.branch),
            "start_age": start_age,
            "end_age": end_age,
            "start_year": birth_date.year + start_age,
            "end_year": birth_date.year + end_age,
        })

    return {
        "direction": "顺排" if direction == "顺" else "逆排",
        "direction_desc": direction_desc,
        "starting_age": f"{starting_age_years}岁{starting_age_months}个月"
                        if starting_age_months > 0 else f"{starting_age_years}岁",
        "starting_age_years": starting_age_years,
        "starting_age_months": starting_age_months,
        "days_to_jie": days_diff,
        "jie_name": jie_name,
        "jie_date": jie_date.isoformat(),
        "calculated": True,
        "pillars": pillars,
    }


# ===========================================================================
# Diagnostics — factual data for Claude to interpret
# ===========================================================================

# Generation & control relationships for 五行
_GEN = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}      # A 生 B
_CTRL = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}     # A 克 B

# 六合: (branch_a, branch_b) → result element
_LIU_HE: dict[tuple[str, str], str] = {
    ("子", "丑"): "土", ("寅", "亥"): "木", ("卯", "戌"): "火",
    ("辰", "酉"): "金", ("巳", "申"): "水", ("午", "未"): "土",
}

# 六冲 pairs
_LIU_CHONG: set[tuple[str, str]] = {
    ("子", "午"), ("丑", "未"), ("寅", "申"),
    ("卯", "酉"), ("辰", "戌"), ("巳", "亥"),
}

# 三合: [branches] → element
_SAN_HE: list[tuple[list[str], str]] = [
    (["申", "子", "辰"], "水"), (["亥", "卯", "未"], "木"),
    (["寅", "午", "戌"], "火"), (["巳", "酉", "丑"], "金"),
]

# 刑 labels
_XING: dict[tuple[str, str], str] = {
    ("子", "卯"): "无礼之刑",
    ("寅", "巳"): "无恩之刑", ("寅", "申"): "无恩之刑",
    ("巳", "申"): "无恩之刑",
    ("丑", "未"): "恃势之刑", ("丑", "戌"): "恃势之刑",
    ("未", "戌"): "恃势之刑",
}
_ZI_XING: set[str] = {"辰", "午", "酉", "亥"}

# 害 pairs
_LIU_HAI: set[tuple[str, str]] = {
    ("子", "未"), ("丑", "午"), ("寅", "巳"),
    ("卯", "辰"), ("申", "亥"), ("酉", "戌"),
}

# 空亡: 旬 index → two empty branches
_KONG_WANG: dict[int, list[str]] = {
    0: ["戌", "亥"], 1: ["申", "酉"], 2: ["午", "未"],
    3: ["辰", "巳"], 4: ["寅", "卯"], 5: ["子", "丑"],
}


def _de_ling(month_branch: str, dm_element: str) -> dict:
    """Judge whether day master is 得令 based on month branch element."""
    month_elem = ELEMENT_BY_BRANCH[month_branch]

    if dm_element == month_elem:
        level, relation = "旺", "同我（当令）"
    elif _GEN[month_elem] == dm_element:
        level, relation = "相", "月令生我（次旺）"
    elif _GEN[dm_element] == month_elem:
        level, relation = "休", "我生月令（泄气）"
    elif _CTRL[dm_element] == month_elem:
        level, relation = "囚", "我克月令（耗力）"
    else:
        level, relation = "死", "月令克我（最弱）"

    _LING_SCORES = {"旺": 10, "相": 7, "休": 4, "囚": 2, "死": 0}
    return {
        "level": level,
        "month_element": month_elem,
        "day_master_element": dm_element,
        "relation": relation,
        "is_de_ling": level in ("旺", "相"),
        "numeric_score": _LING_SCORES[level],
    }


def _de_di(day_stem: str, pillars: dict, hidden: dict) -> dict:
    """Check whether day stem has root (通根) in any branch.

    Two kinds of root are detected:
    1. Exact stem match — the day stem character appears in hidden stems
       (e.g. 甲 in 寅's [甲,丙,戊] → true 禄根)
    2. Same-element match — a different stem of the same element appears
       (e.g. 甲木 in 卯's [乙] → 旺根, since 乙 is also 木)

    Strength depends on hidden-stem position:
      本气 (pos 0) > 中气 (pos 1) > 余气 (pos 2)
    """
    dm_element = ELEMENT_BY_STEM[day_stem]
    same_element_stems = {s for s, el in ELEMENT_BY_STEM.items()
                          if el == dm_element}

    roots_list: list[dict] = []
    total_strength = 0.0
    root_branches: list[str] = []

    for name in ["year", "month", "day", "hour"]:
        if name not in pillars:
            continue
        hidden_list = hidden.get(name, [])
        for pos, hs in enumerate(hidden_list):
            is_exact = (hs == day_stem)
            is_same_element = hs in same_element_stems

            if not (is_exact or is_same_element):
                continue

            pos_labels = ["本气", "中气", "余气"]

            # Position-specific weight and label
            if pos == 0:  # 本气
                if is_exact:
                    level_label = "禄根"
                    weight = 3.0
                    note = f"{name}支本气藏{hs}，同字禄根（最强）"
                else:
                    level_label = "旺根"
                    weight = 2.0
                    note = f"{name}支本气藏{hs}，同五行旺根"
            elif pos == 1:  # 中气
                if is_exact:
                    level_label = "中气根"
                    weight = 1.5
                else:
                    level_label = "中气根"
                    weight = 1.0
                note = f"{name}支中气藏{hs}，{'同字' if is_exact else '同五行'}中气根"
            else:  # 余气
                if is_exact:
                    level_label = "余气根"
                    weight = 0.8
                else:
                    level_label = "余气根"
                    weight = 0.5
                note = f"{name}支余气藏{hs}，{'同字' if is_exact else '同五行'}余气根"

            root_branches.append(name)
            roots_list.append({
                "pillar": name,
                "stem": hs,
                "is_exact_stem": is_exact,
                "position": pos,
                "position_label": pos_labels[pos],
                "strength_level": level_label,
                "strength_score": weight,
                "note": note,
            })
            total_strength += weight

    # Deduplicate root_branches for backwards-compatible output
    unique_root_branches = sorted(set(root_branches),
                                  key=lambda n: ["year","month","day","hour"].index(n))

    return {
        "has_root": len(roots_list) > 0,
        "root_count": len(roots_list),
        "root_branches": unique_root_branches,
        "roots": roots_list,
        "weighted_root_score": round(total_strength, 1),
        "day_branch_root": "day" in root_branches,
        "hour_branch_root": "hour" in root_branches,
        "year_branch_root": "year" in root_branches,
        "month_branch_root": "month" in root_branches,
    }


def _de_zhu(day_stem: str, dm_element: str, pillars: dict) -> dict:
    """Analyse heavenly stems by their element relationship to day master."""
    same: list[str] = []       # 同五行（比劫）
    support: list[str] = []    # 生我（印）
    drain: list[str] = []      # 我生（食伤）
    control: list[str] = []    # 我克（财）
    restrict: list[str] = []   # 克我（官杀）

    for name, p in pillars.items():
        if name == "day":
            continue
        elem = ELEMENT_BY_STEM[p.stem]
        if elem == dm_element:
            same.append(p.stem)
        elif _GEN[elem] == dm_element:
            support.append(p.stem)
        elif _GEN[dm_element] == elem:
            drain.append(p.stem)
        elif _CTRL[dm_element] == elem:
            control.append(p.stem)
        else:
            restrict.append(p.stem)

    return {
        "same_element_stems": same, "same_count": len(same),
        "supporting_stems": support, "supporting_count": len(support),
        "draining_stems": drain, "draining_count": len(drain),
        "controlling_stems": control, "controlling_count": len(control),
        "restricting_stems": restrict, "restricting_count": len(restrict),
    }


def _tong_yi_dang(day_stem: str, pillars: dict, hidden: dict) -> dict:
    """Count 同党 vs 异党 across all stems (heavenly + hidden).

    同党 = 比肩/劫财 + 正印/偏印  (same element + generates me)
    异党 = 食神/伤官 + 正财/偏财 + 正官/七杀
    """
    POS_WEIGHTS = [0.9, 0.5, 0.3]  # 本气, 中气, 余气

    tong, yi = 0, 0
    w_tong, w_yi = 0.0, 0.0
    details: list[dict] = []

    # Heavenly stems (exclude day master itself)
    for name, p in pillars.items():
        if name == "day":
            continue
        tg = ten_god(day_stem, p.stem)
        cat = "同党" if tg in ("比肩", "劫财", "正印", "偏印") else "异党"
        weight = 1.0
        if cat == "同党":
            tong += 1
            w_tong += weight
        else:
            yi += 1
            w_yi += weight
        details.append({"source": f"{name}干", "stem": p.stem,
                        "ten_god": tg, "category": cat,
                        "weight": weight})

    # Hidden stems with position-dependent weights
    for name, stems in hidden.items():
        for pos, s in enumerate(stems):
            tg = ten_god(day_stem, s)
            cat = "同党" if tg in ("比肩", "劫财", "正印", "偏印") else "异党"
            weight = POS_WEIGHTS[pos] if pos < len(POS_WEIGHTS) else 0.3
            if cat == "同党":
                tong += 1
                w_tong += weight
            else:
                yi += 1
                w_yi += weight
            details.append({"source": f"{name}支藏", "stem": s,
                            "ten_god": tg, "category": cat,
                            "weight": weight, "position": pos})

    total = tong + yi
    w_total = w_tong + w_yi
    return {
        "tong_dang": tong,
        "yi_dang": yi,
        "total": total,
        "tong_dang_ratio": round(tong / total, 2) if total > 0 else 0,
        "weighted_tong_dang": round(w_tong, 1),
        "weighted_yi_dang": round(w_yi, 1),
        "weighted_ratio": round(w_tong / w_total, 2) if w_total > 0 else 0,
        "details": details,
    }


def _geju(month_branch: str, pillars: dict, day_stem: str) -> list[dict]:
    """Find 格局 candidates from month-branch hidden stems 透出 in heavenly stems."""
    candidates: list[dict] = []
    hidden_stems = HIDDEN_STEMS[month_branch]

    for pos, h_stem in enumerate(hidden_stems):
        for pillar_name, p in pillars.items():
            if p.stem == h_stem:
                tg = ten_god(day_stem, h_stem)
                candidates.append({
                    "hidden_stem": h_stem,
                    "hidden_position": pos + 1,  # 1=主气, 2=中气, 3=余气
                    "appears_as": f"{pillar_name}干",
                    "ten_god": tg,
                    "note": f"月支藏{h_stem}透于{pillar_name}干，可取{tg}格",
                })
                break  # A stem can only appear once

    return candidates


def _branch_interactions(pillars: dict) -> list[dict]:
    """Detect 六合/六冲/三合/刑/害 among the four branches."""
    interactions: list[dict] = []
    entries = [(name, p.branch) for name, p in pillars.items()]
    all_branches = {b for _, b in entries}

    # Pairwise: 六合, 六冲, 刑, 害
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            n1, b1 = entries[i]
            n2, b2 = entries[j]
            pair = (b1, b2)
            sorted_pair = tuple(sorted(pair))

            # 六合
            if sorted_pair in _LIU_HE:
                interactions.append({
                    "type": "六合", "branches": sorted_pair,
                    "locations": [n1, n2],
                    "result_element": _LIU_HE[sorted_pair],
                    "note": f"{sorted_pair[0]}{sorted_pair[1]}合{_LIU_HE[sorted_pair]}",
                })

            # 六冲
            if sorted_pair in _LIU_CHONG:
                interactions.append({
                    "type": "六冲", "branches": sorted_pair,
                    "locations": [n1, n2],
                    "note": f"{sorted_pair[0]}{sorted_pair[1]}冲",
                })

            # 刑
            if sorted_pair in _XING:
                interactions.append({
                    "type": "刑", "branches": sorted_pair,
                    "locations": [n1, n2],
                    "note": f"{sorted_pair[0]}{sorted_pair[1]}{_XING[sorted_pair]}",
                })

            # 害
            if sorted_pair in _LIU_HAI:
                interactions.append({
                    "type": "害", "branches": sorted_pair,
                    "locations": [n1, n2],
                    "note": f"{sorted_pair[0]}{sorted_pair[1]}害",
                })

    # 三合 / 半合
    for group, elem in _SAN_HE:
        present = sorted([b for b in group if b in all_branches])
        if len(present) >= 2:
            locs = [n for n, b in entries if b in present]
            itype = "三合" if len(present) == 3 else "半合"
            interactions.append({
                "type": itype, "branches": present,
                "locations": locs, "result_element": elem,
                "note": f"{''.join(present)}{'合' if len(present) == 3 else '半合'}{elem}",
            })

    # 自刑
    seen: dict[str, list[str]] = {}
    for n, b in entries:
        seen.setdefault(b, []).append(n)
    for b, locs in seen.items():
        if b in _ZI_XING and len(locs) >= 2:
            interactions.append({
                "type": "自刑", "branches": [b],
                "locations": locs,
                "note": f"{b}自刑（{locs[0]}支与{locs[1]}支伏吟自刑）",
            })

    return interactions


def _kong_wang(day_pillar: Pillar, pillars: dict) -> dict:
    """Compute 空亡 (xun kong) from the day pillar's 旬."""
    day_idx = ganzhi_to_index(day_pillar)
    xun_idx = day_idx // 10
    kw_branches = _KONG_WANG[xun_idx]

    affected: list[dict] = []
    for name, p in pillars.items():
        if name == "day":
            continue
        if p.branch in kw_branches:
            affected.append({"pillar": name, "branch": p.branch})

    return {
        "day_xun_index": xun_idx,
        "kong_wang_branches": kw_branches,
        "affected_pillars": affected,
        "note": f"日柱在{'甲乙丙丁戊己庚辛壬癸'[day_idx % 10]}{BRANCHES[day_idx % 12]}旬"
                f"（第{xun_idx + 1}旬），空亡{kw_branches[0]}{kw_branches[1]}",
    }


def _compute_diagnostics(
    day_stem: str,
    dm_element: str,
    pillars: dict[str, "Pillar"],
    hidden: dict[str, list[str]],
) -> dict:
    """Compute all diagnostic data. Factual output only — no interpretation."""
    month_pillar = pillars["month"]
    day_pillar = pillars["day"]

    de_ling_result = _de_ling(month_pillar.branch, dm_element)
    de_di_result = _de_di(day_stem, pillars, hidden)
    tong_yi_result = _tong_yi_dang(day_stem, pillars, hidden)

    # Composite strength score (0–100, higher = stronger 身)
    # Dimensions weighted: 得令 40%, 得地 35%, 同党比例 25%
    ling_score = de_ling_result["numeric_score"]  # 0–10
    di_score = min(de_di_result["weighted_root_score"], 10.0)  # cap at 10
    tong_score = tong_yi_result["weighted_ratio"] * 10  # 0–10

    composite = round(ling_score * 4.0 + di_score * 3.5 + tong_score * 2.5)
    composite = max(0, min(100, composite))

    # Rough classification based on composite score
    if composite >= 65:
        strength_label = "偏强"
    elif composite >= 40:
        strength_label = "中和偏强" if composite >= 52 else "中和偏弱"
    else:
        strength_label = "偏弱"

    return {
        "day_master_strength": {
            "de_ling": de_ling_result,
            "de_di": de_di_result,
            "de_zhu": _de_zhu(day_stem, dm_element, pillars),
            "tong_yi_dang": tong_yi_result,
        },
        "strength_assessment": {
            "de_ling_score": de_ling_result["numeric_score"],
            "de_di_score": round(di_score, 1),
            "tong_dang_weighted_score": round(tong_score, 1),
            "composite_score": composite,
            "preliminary_label": strength_label,
            "note": (
                "综合评分仅供参考，最终身强身弱需结合格局、合冲刑害等因素综合判定。"
                "评分维度权重：得令40% + 得地35% + 同党比例25%。"
            ),
        },
        "geju_candidates": _geju(month_pillar.branch, pillars, day_stem),
        "branch_interactions": _branch_interactions(pillars),
        "kong_wang": _kong_wang(day_pillar, pillars),
    }


# ===========================================================================
# Lunar → Gregorian conversion (must-have validation via library)
# ===========================================================================

def lunar_to_gregorian(year: int, month: int, day: int) -> date:
    """Convert lunar date to Gregorian. Exits with structured error on failure.

    Only validation that runs here is what Claude cannot determine in
    conversation: whether this lunar date actually exists in the calendar.
    """
    if Lunar is None:
        fail("LUNAR_NOT_INSTALLED",
             "lunar-python 库未安装，无法处理农历日期。请运行 pip install lunar-python。")

    try:
        lunar = Lunar.fromYmd(year, month, day)
    except Exception:
        fail("LUNAR_DATE_INVALID",
             f"农历日期不存在：{year}年{month}月{day}日。请确认日期是否正确。")

    solar = lunar.getSolar()
    return date(solar.getYear(), solar.getMonth(), solar.getDay())


# ===========================================================================
# True solar time correction
# ===========================================================================

def _day_of_year(d: date) -> int:
    return d.timetuple().tm_yday


def equation_of_time(doy: int) -> float:
    """Spencer 1971 EoT in decimal minutes. Range ≈ [-14.2, +16.4]."""
    B = 2.0 * math.pi * (doy - 1) / 365.0
    return 229.18 * (
        0.000075 + 0.001868 * math.cos(B) - 0.032077 * math.sin(B)
        - 0.014615 * math.cos(2.0 * B) - 0.040849 * math.sin(2.0 * B)
    )


def timezone_standard_meridian(tz: ZoneInfo, dt: datetime) -> float:
    """Standard meridian for this timezone (e.g., 120°E for UTC+8)."""
    offset = dt.replace(tzinfo=tz).utcoffset()
    return (offset or timedelta(hours=8)).total_seconds() / 3600.0 * 15.0


def apply_true_solar_time(
    local_dt: datetime, longitude: float, tz: ZoneInfo
) -> tuple[datetime, dict]:
    """Apply true solar time correction. Returns (corrected_dt, info_dict)."""
    meridian = timezone_standard_meridian(tz, local_dt)
    lon_corr = (longitude - meridian) * 4.0
    eot = equation_of_time(_day_of_year(local_dt.date()))
    total = lon_corr + eot

    original_time = local_dt.strftime("%H:%M")
    corrected_dt = local_dt + timedelta(minutes=total)

    info = {
        "applied": True,
        "original_time": original_time,
        "corrected_time": corrected_dt.strftime("%H:%M"),
        "longitude": longitude,
        "equation_of_time_minutes": round(eot, 2),
        "longitude_correction_minutes": round(lon_corr, 2),
        "total_correction_minutes": round(total, 2),
    }
    if corrected_dt.date() != local_dt.date():
        info["corrected_date"] = corrected_dt.strftime("%Y-%m-%d")

    return corrected_dt, info


# ===========================================================================
# CLI (Claude's internal interface — not user-facing)
# ===========================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--date", required=True)
    p.add_argument("--time")
    p.add_argument("--timezone", default="Asia/Shanghai")
    p.add_argument("--calendar", choices=["gregorian", "lunar"], default="gregorian")
    p.add_argument("--is-leap-month", action="store_true")
    p.add_argument("--longitude", type=float)
    p.add_argument("--gender", default="")
    p.add_argument("--birthplace", default="")
    p.add_argument("--output")
    return p.parse_args()


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    args = parse_args()

    # ---- Resolve effective date ----
    lunar_info = None
    if args.calendar == "lunar":
        parts = args.date.split("-")
        ly, lm, ld = int(parts[0]), int(parts[1]), int(parts[2])
        effective_date = lunar_to_gregorian(ly, lm, ld)
        lunar_info = {
            "year": ly, "month": lm, "day": ld,
            "is_leap_month": args.is_leap_month,
        }
    else:
        effective_date = date.fromisoformat(args.date)

    # ---- Parse time ----
    birth_time = time.fromisoformat(args.time) if args.time else None
    tz = ZoneInfo(args.timezone)
    local_dt = datetime.combine(effective_date, birth_time or time(12, 0), tzinfo=tz)

    # ---- True solar time ----
    solar_info = None
    if args.longitude is not None and birth_time is not None:
        local_dt, solar_info = apply_true_solar_time(local_dt, args.longitude, tz)
        effective_date = local_dt.date()
        birth_time = local_dt.time()
    elif args.longitude is not None and birth_time is None:
        solar_info = {"applied": False, "reason": "未提供出生时间"}

    # ---- Core calculation ----
    y = year_pillar(effective_date)
    m = month_pillar(effective_date)
    d = day_pillar(effective_date)
    h = hour_pillar(d, birth_time) if birth_time else None

    pillars = {"year": y, "month": m, "day": d}
    if h:
        pillars["hour"] = h

    elem = {el: 0 for el in ["木", "火", "土", "金", "水"]}
    gods, hidden = {}, {}
    for name, p in pillars.items():
        elem[ELEMENT_BY_STEM[p.stem]] += 1
        elem[ELEMENT_BY_BRANCH[p.branch]] += 1
        gods[name] = {
            "stem": ten_god(d.stem, p.stem) if name != "day" else "日主",
            "hidden_stems": [ten_god(d.stem, s) for s in HIDDEN_STEMS[p.branch]],
        }
        hidden[name] = HIDDEN_STEMS[p.branch]

    # ---- Da Yun (大运) ----
    dayun_data = None
    dayun_note = None
    if args.gender in ("男", "女"):
        try:
            dayun_data = calculate_dayun(
                effective_date, m, d.stem, args.gender, y
            )
        except Exception as exc:
            dayun_note = f"大运计算未成功: {exc}"
    elif args.gender:
        dayun_note = f"性别值 \"{args.gender}\" 无法识别，需为 男 或 女"
    else:
        dayun_note = None  # No gender provided; dayun skipped silently

    # ---- Diagnostics ----
    diagnostics = _compute_diagnostics(d.stem, ELEMENT_BY_STEM[d.stem], pillars, hidden)

    # ---- Build output ----
    precision_notes = (
        "Year/month boundaries use approximate jie dates. "
        "Use ephemeris for definitive results near solar terms."
    )
    if dayun_data:
        precision_notes += " 大运计算使用精确节气日期（lunar-python）。"
    if solar_info and solar_info.get("applied"):
        precision_notes += " 真太阳时校正已应用。"

    payload = {
        "input": {
            "calendar": args.calendar,
            "birth_date": args.date,
            "birth_time": args.time,
            "timezone": args.timezone,
            "gender": args.gender or None,
            "birthplace": args.birthplace or None,
            "lunar_date": lunar_info,
            "longitude": args.longitude,
        },
        "precision": {"level": "standard", "notes": precision_notes},
        "pillars": {n: p.to_dict() for n, p in pillars.items()},
        "day_master": {
            "stem": d.stem,
            "element": ELEMENT_BY_STEM[d.stem],
            "polarity": "阳" if STEMS.index(d.stem) % 2 == 0 else "阴",
        },
        "elements": elem,
        "ten_gods": gods,
        "hidden_stems": hidden,
        "true_solar_time": solar_info,
        "dayun": dayun_data,
        "dayun_note": dayun_note,
        "diagnostics": diagnostics,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
