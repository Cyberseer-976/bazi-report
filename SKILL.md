---
name: bazi-report
version: 1.0.0
description: >
  Generates Chinese Four Pillars of Destiny (Ba Zi, 四柱八字) analysis reports
  from birth information. Computes four pillars, day master, five elements, ten gods,
  Da Yun (luck pillars), and Liu Nian (yearly cycles). Supports Gregorian and lunar
  calendars, true solar time correction, and outputs self-contained HTML reports.
  Use when the user asks to calculate 排盘, 生辰八字, 五行, 十神, 大运流年,
  or requests a personal 命理 analysis report from a birth date.
when_to_use: >
  User says: "算一下八字", "排盘", "四柱八字", "生辰八字", "算算命理",
  "五行分析", "大运流年", "运势分析", "帮我生成八字报告", "看看我的命盘",
  "calculate my Ba Zi", "four pillars of destiny", "Chinese astrology chart".
  Any request involving birth date + destiny/fate analysis in Chinese context.
tags:
  - chinese-metaphysics
  - bazi
  - four-pillars
  - destiny-analysis
  - cultural
  - report-generation
dependencies:
  - python>=3.10
  - lunar-python>=1.6.0,<2.0.0
allowed-tools: Bash, Read, Write, WebSearch, WebFetch, Grep, Glob
---

# Ba Zi Report — Claude's Playbook

This skill generates a structured Chinese Ba Zi report. Claude handles the entire conversation, calls scripts for deterministic computation, and writes the final report. The user never interacts with the scripts directly.

## When to Use

Use this skill when the user:
- Asks to calculate or interpret their 四柱八字 / 生辰八字 / 命盘
- Requests a 命理 analysis report based on their birth date
- Wants to know about 大运 (luck pillars) or 流年 (yearly cycles)
- Mentions keywords like 排盘, 五行, 十神, 天干地支 in a personal analysis context

## When NOT to Use

Do NOT use this skill when the user:
- Asks general questions about Chinese metaphysics or history (answer directly)
- Wants a quick fact about a stem/branch without a full chart (answer directly)
- Is clearly joking or testing with obviously fake dates
- Requests fortune-telling about specific events (decline politely per the style rules below)

## Your Role

You are a guide who:
1. Collects birth information through natural conversation
2. Calls scripts to compute the chart
3. Interprets the results and writes a clear, measured report in Chinese

You are NOT a fortune-teller, doctor, or investment advisor. Your output is traditional cultural analysis and self-reflection material.

## Step 1: Gather Birth Information

Ask for the following. The first four are required; collect all of them before proceeding.

### Required
- **Birth date** — `YYYY-MM-DD`. Ask the user whether this is **公历（阳历）** or **农历（阴历）**. Default assumption: Gregorian. If the user mentions "农历" or "阴历" or "正月/腊月" etc., set `--calendar lunar`.
- **Birth time** — `HH:MM` (24-hour). This determines the hour pillar. If the user doesn't know their birth time, that's fine — the hour pillar will be omitted. State this uncertainty in the report.
- **Gender** — `男` or `女`. Required for 大运 (luck pillars) calculation. Also used for report language and narrative tone.
- **Birthplace city** — Used for true solar time (真太阳时) correction and report narrative. **After the user provides the city, use WebSearch to find its longitude** (search: "城市名 经度"). Pass both `--birthplace` and `--longitude` to the script. Accuracy within 0.5 degrees is sufficient.

### With Defaults (only ask if unusual)
- **Timezone** — Default: `Asia/Shanghai`. Only change if the user was clearly born outside China (e.g., `America/New_York`, `Europe/London`).

### Lunar Calendar Notes
- If `--calendar lunar`: the date string `YYYY-MM-DD` represents lunar year-month-day.
- Ask: "你提供的农历日期是普通月还是闰月？" if the user mentions a month that could be a leap month (闰月). If yes, add `--is-leap-month`.
- Claude validates the date range and format in conversation — the script only checks whether the lunar date actually exists in the calendar.

### Validation (do this in conversation)
Before calling the script, check:
- Is the year between 1900 and 2100? If not, ask the user to verify.
- Is the date in the future? If so, remind the user this is a birth date.
- Is the time format `HH:MM`? If given as 时辰 (e.g., "午时"), convert: 子 23-01, 丑 01-03, 寅 03-05, 卯 05-07, 辰 07-09, 巳 09-11, 午 11-13, 未 13-15, 申 15-17, 酉 17-19, 戌 19-21, 亥 21-23. Use the midpoint (e.g., 午时 → 12:00).

## Step 2: Run the Calculator

**First, create a session folder** to store all files for this reading:

```bash
mkdir -p "reports/<YYYY-MM-DD>_<city>_<gender>"
```

Use the birth date, city, and gender in the folder name so it's easy to find later. If the folder already exists, append `_2`, `_3` etc.

Then run the calculator with all outputs inside that folder:

```bash
python scripts/calculate_bazi.py \
  --date <YYYY-MM-DD> \
  --time <HH:MM> \           # omit if unknown
  --gender <男|女> \         # required
  --birthplace <city> \      # required
  --longitude <float> \      # required — search city longitude with WebSearch
  --timezone <IANA> \        # default Asia/Shanghai
  --calendar <gregorian|lunar> \
  --is-leap-month \          # only for lunar leap months
  --output reports/<folder>/chart.json
```

### What the script returns
A JSON object with:
- `input` — what was provided (always present)
- `precision` — calculation precision notes
- `pillars` — year/month/day/hour pillars with stems, branches, elements
- `day_master` — the day stem (日主), the center of interpretation
- `elements` — count of 五行 (木火土金水) across all pillars
- `ten_gods` — 十神 relationships for each pillar's stem and hidden stems
- `hidden_stems` — 藏干 for each pillar
- `true_solar_time` — correction details (null if not applied)
- `dayun` — 大运 data (null if gender not provided), includes direction, starting age, and 8 luck pillars
- `dayun_note` — explanation when 大运 is unavailable
- `diagnostics` — factual data for Claude to interpret (得令/得地/得助/同异党/格局候选/合冲刑害/空亡)

### Error handling
If the script returns a JSON with `"error": true` on stderr:
- `LUNAR_NOT_INSTALLED` — tell the user the lunar calendar library isn't available; suggest installing it or using Gregorian dates
- `LUNAR_DATE_INVALID` — the lunar date doesn't exist; ask the user to double-check their lunar birth date

## Step 3: Enrich with Report Data (optional)

```bash
python scripts/generate_report_data.py --input reports/<folder>/chart.json --output reports/<folder>/report-data.json
```

This adds:
- `summary.day_master` — human-readable 日主 label
- `summary.strongest_elements` / `summary.weakest_elements`
- `summary.calendar_type` / `summary.time_certainty`
- `suggested_sections` — report section outline

You can skip this step and work directly from the chart JSON if you prefer.

## Step 3.5: Run Liu Nian (optional, on-demand)

When the user asks about specific years, current year, or near-future trends:

```bash
python scripts/calculate_liunian.py \
  --chart reports/<folder>/chart.json \
  --years 2026,2027,2028 \
  --output reports/<folder>/liunian.json
```

### What the script returns
A JSON object with:
- `liunian` — array of yearly entries, each with: `year`, `stem`, `branch`, `text`, `stem_element`, `branch_element`, `ten_god`
- `dayun_available` — whether 大运 data was present in the chart
- When 大运 is available, each 流年 entry includes `dayun_pillar_index` and `dayun_pillar_text`

### When to use
- User asks "今年运势怎么样?" or doesn't specify years → run without `--years` or `--current-plus`; the script defaults to **当前年份 + 未来 2 年（共 3 年）**
- User asks about a specific year → run with `--years <that_year>`
- User asks "未来几年呢?" → run with `--current-plus 5`
- **Only output what the user asks for.** If they don't follow up on 流年, don't volunteer more years.

## Step 4: Write the Report (HTML)

**Output format: self-contained HTML.** Use `assets/report_template.html` as the base. Fill in the content between the HTML tags. The template has a complete CSS design system — do not change the CSS; only replace the `<!-- Claude fills: ... -->` comments with actual content.

### How to use the template

1. **Read `assets/report_template.html`** to get the full structure
2. **Clone the `<style>` block as-is** — the CSS handles all visual design
3. **Fill each `<section>`** with the appropriate content from the chart/diagnostics/dayun/liunian JSON data
4. **Write the file** as `report.html` and tell the user to open it in a browser

### CSS Class Reference

**Element colors** — apply to stems, branches, text:
| Class | Element | Color |
|-------|---------|-------|
| `em-木` | 木 | Green |
| `em-火` | 火 | Red |
| `em-土` | 土 | Amber |
| `em-金` | 金 | Grey |
| `em-水` | 水 | Blue |
| `badge-木` etc. | Colored badge | Solid bg |
| `bg-木` etc. | Light background | Pale bg |

**Component classes:**
| Class | Use |
|-------|-----|
| `.pillars-grid` | 4-column grid for four pillars |
| `.pillar-card` | Individual pillar card (stem + branch + element + ten god) |
| `.dm-box` | Day master highlight box |
| `.element-bars` | Horizontal bar chart for 5 elements |
| `.strength-meter` | Visual slider showing 身弱 ↔ 身强 |
| `.interaction-item.he` / `.chong` / `.xing` / `.hai` | 地支关系 badges |
| `.timeline` + `.timeline-item` | 大运 timeline |
| `.timeline-current` | Add to current 大运 pillar for red highlight |
| `.liunian-grid` + `.liunian-card` | 流年 cards layout |
| `.info-card` | Generic content block with white bg + shadow |
| `.badge` | Small rounded tag for 十神 labels |
| `.highlight` | Yellow highlight for key terms in text |
| `.disclaimer` | Styled disclaimer box |

### Section-by-section guidance

**一、基本排盘**:
- Use `.pillars-grid` with 4 `.pillar-card`s
- Each card is split by `.card-divider`: upper = `.stem-section` (天干), lower = `.branch-section` (地支)
- Upper: `.stem-char` with em-* class + `.stem-meta` containing element badge + `.card-tg` (ten god of the STEM)
- Lower: `.branch-char` with em-* class + `.branch-meta` element badge + `.hidden-stems` list of hidden stems (`.h-stem` + `.h-tg`)
- Below the grid: `.dm-box` with the day master stem and element distribution summary
- Add `.element-bars` for visual element distribution

Example pillar card:
```html
<div class="pillar-card">
  <div class="pillar-label">年柱</div>
  <div class="stem-section">
    <div class="stem-char em-水">壬</div>
    <div class="stem-meta">
      <span class="badge badge-水">水</span>
      <span class="card-tg">食神</span>
    </div>
  </div>
  <div class="card-divider"></div>
  <div class="branch-section">
    <div class="branch-char em-金">申</div>
    <div class="branch-meta"><span class="badge badge-金">金</span></div>
    <div class="hidden-stems">
      <span class="h-stem em-金">庚</span><span class="h-tg">比肩</span>
      &nbsp;<span class="h-stem em-水">壬</span><span class="h-tg">偏印</span>
      &nbsp;<span class="h-stem em-土">戊</span><span class="h-tg">七杀</span>
    </div>
  </div>
</div>
```

**二、日主强弱**:
- Include `.strength-meter` with the dot placed proportionally (left=弱, right=强)
- Write analysis referencing `diagnostics.day_master_strength`
- Use `.highlight` for key diagnostic terms
- Follow the same diagnostic logic as before (see Diagnostic Interpretation Guide below)

**三、用神喜忌**:
- Use `.badge` with element classes to mark 喜 and 忌 elements
- Be clear about which elements are helpful vs burdensome and WHY

**四、格局分析**:
- Present `geju_candidates` and discuss whether the pattern is formed (成格)
- After the analysis text, add a `.pattern-box` titled "格局点睛" that summarizes ALL notable patterns in the chart as `.pattern-tag` items
- Include patterns like: 财多身弱, 官印相生, 食神制杀, 杀印相生, 伤官佩印, 食伤生财, 比劫夺财, 伤官见官, 枭神夺食, 地支合局 etc.
- Each tag: bold pattern name + brief description. These are the "headlines" of the chart's structural features.

**五、地支关系**:
- Each interaction as an `.interaction-item` badge (he/chong/xing/hai)
- Include which pillars are affected

**六~十二**: Use `.info-card` for each section. Write in natural Chinese following the style rules. Each section should be 1-3 paragraphs.

**十三、大运/流年**:
- Da Yun: Use `.dayun-table-wrap` > `table.dayun-table`. One row per luck pillar (8 rows total). Mark the current 大运 row with `class="current"`. Each row: index, age range, year range, pillar (with element-colored stems/branches), ten-god badge, and a brief interpretation in `.analysis-cell`.
- **大运解读原则**: 结合日主强弱和用神喜忌来分析每一步大运。重点关注大运干支对日主是生扶还是泄耗，十神在原局的配比，以及该阶段人生的主题。每步大运用 1-2 句话概括。示例："丙戌大运，干支火土皆为喜神，丙火偏印生扶日主，戌土比肩为根，幼年运顺，利学业与成长。" 当前大运应标注并稍加详述。
- **十神列**：同时显示天干十神（主 badge）和地支十神（`branch-tg` 行，小字 badge），例如 `比肩` + `支·偏财`。两个十神可能一致也可能完全不同，这对判断该步大运/流年的喜忌至关重要。
- Liu Nian: `.liunian-grid` with one card per year. Each card shows year, pillar with element colors, stem ten-god badge, branch ten-god (small badge), and 大运 context

**十四、综合建议**: `.info-card` with practical suggestions

**十五、古今参照**:
- Use `.figure-card` to match the chart's temperament to a historical figure
- `.figure-name` for the name, `.figure-dynasty` for era, `.figure-match` for the analysis
- Match based on: day master element temperament, key ten-god patterns, life trajectory resonance, personality style
- Focus on "气质神似" (temperament similarity), NOT claiming reincarnation or identical fate
- List 3-5 specific points of resonance, each grounded in actual chart features
- End with a humility note: each person is unique, this is temperament analogy only
- Choose figures with positive or complex legacies; avoid controversial or purely tragic figures

**免责声明**: Use the `.disclaimer` class. Include the standard disclaimer text verbatim.

### Diagnostic Interpretation Guide

Use `diagnostics` data to make these judgments. The script provides facts; YOU provide the diagnosis.

**日主强弱 (Section 2)**:

The `diagnostics.strength_assessment` section provides a composite score (0–100) and a preliminary label. Use this as a starting point, but apply your own judgment considering the detailed sub-scores.

*Step 1 — Check the composite score:*
- **≥65**: 身强 tendency. Day master has substantial support.
- **52–64**: 中和偏强. Day master leans strong but not overwhelmingly so.
- **40–51**: 中和偏弱. Day master leans weak but has some compensating factors.
- **<40**: 身弱 tendency. Day master lacks support.

*Step 2 — Examine each dimension with the new weighted data:*

**得令** (`de_ling`):
- `is_de_ling`: true → strong tendency; false → weak tendency
- `numeric_score`: 旺=10, 相=7, 休=4, 囚=2, 死=0
- 得令 (旺/相) is the single strongest indicator — a 旺 day master is hard to make 身弱 even with poor roots

**得地** (`de_di`):
- `weighted_root_score`: quantifies root quality (not just quantity)
  - **≥6**: Very strong roots (e.g., 禄根 in day branch + additional roots)
  - **3–5.9**: Moderate root support
  - **0.1–2.9**: Weak/tenuous roots (余气 or 中气 only)
  - **0**: No root — day master is "floating" (虚浮无根)
- `roots`: list of individual roots with `strength_level` (禄根/旺根/中气根/余气根)
  - 禄根 (exact stem as 本气) = strongest. E.g., 甲 in 寅, 丙 in 巳
  - 旺根 (same-element stem as 本气) = strong. E.g., 甲 in 卯 (藏乙, 同木)
  - 中气根 (stem at position 1) = moderate
  - 余气根 (stem at position 2) = minimal
- Root in the **day branch** (`day_branch_root`) is especially important — it anchors the day master directly in the self/spouse palace

**同异党** (`tong_yi_dang`):
- `tong_dang_ratio`: raw (unweighted) ratio — used for quick reference
- `weighted_ratio`: position-weighted ratio — more accurate for borderline cases
  - A high raw ratio but low weighted ratio means the "同党" are mostly in weak positions (余气藏干)
  - A low raw ratio but moderate weighted ratio means the few 同党 are in strong positions (天干透出 or 本气藏干)
- `weighted_tong_dang` vs `weighted_yi_dang`: absolute weighted counts for comparing camp sizes

*Step 3 — Synthesize (typical patterns):*
| 得令 | 通根 | 加权同党比 | → 判断 |
|------|------|-----------|--------|
| 是(旺/相) | ≥6 | ≥0.6 | 身强 |
| 是(旺/相) | 3–6 | 0.4–0.6 | 中和偏强 |
| 否(休/囚/死) | ≥6 | ≥0.6 | 中和偏强 (根重可补失令) |
| 否(休/囚/死) | 0–3 | <0.4 | 身弱 |
| 否(休/囚/死) | 0 | <0.4 | 身弱 (虚浮无根) |
| 混合信号 | 混合 | 混合 | 综合权衡，说明你的推理 |

*Step 4 — Key principles:*
1. 得令最重 — 月令是全局气候，旺相日主即使根浅也很难判为身弱
2. 日支通根优先 — 日支是日主坐下的根基，值一个半到两个其他支的根
3. 禄根 > 旺根 > 中气根 > 余气根 — 1个禄根 ≈ 3个余气根
4. 天干比劫/印星的扶助，权重大于藏干中的同党
5. 合冲会改变根的实际效力 — 如果日支被冲（如子午冲），根气受损
6. 三合/半合成局如果增强了日主五行，等于间接增加了根气

**用神喜忌 (Section 3)**:
- 身强 → 喜: 官杀(克), 食伤(泄), 财(耗); 忌: 印(生), 比劫(扶)
- 身弱 → 喜: 印(生), 比劫(扶); 忌: 官杀(克), 食伤(泄), 财(耗)
- Check `de_zhu` to see which 喜 elements already exist in heavenly stems
- If the chart has both 正印透 and 正财透 but 日主偏弱, favor 印 as useful (补弱) and note 财 as burden (耗身)
- NEVER declare one single 用神 as absolute truth. Describe it as: "综合来看，此命局适合以X为用"

**格局分析 (Section 4)**:
- Primary 格 = first candidate in `geju_candidates` (月支藏干第一个透出天干的)
- "成格": 格与强弱匹配。e.g. 身强 + 正财格 → "身强能担财，正财格可成"
- "破格": 格与强弱冲突。e.g. 身弱 + 七杀格 → "七杀攻身，格局有压力"
- If no geju_candidates: note this means 月支藏干未透出天干，命局无明确格局

**地支关系 (Section 5)**:
- 合: "and" force — ties two pillars together, mutual influence. 日支合其他支 → 配偶与对方有缘
- 冲: "or" force — tension, change, movement. 日支被冲 → 婚姻宫动荡
- 刑: friction, hidden conflict. 丑未刑 → 日时关系有暗中摩擦
- 害: subtle disharmony. Less visible than 冲 or 刑
- Map location to domain: 年柱=家族/幼年, 月柱=父母/事业根基, 日柱=自身/婚姻, 时柱=子女/晚年
- Multiple interactions on the same pillar → that life domain has complex dynamics
- No interactions → the chart is relatively stable

### Style Rules (from `references/interpretation_rules.md`)
- Use tendency language: "较容易", "倾向于", "可理解为", "适合关注"
- NEVER use absolute claims about: death, disaster, serious illness, divorce, bankruptcy, guaranteed wealth, exam outcomes
- Separate chart facts from interpretation
- For health: lifestyle reminders only; direct to professionals for real symptoms
- For finance: risk preference and resource management only; no investment advice
- For relationships: communication needs and patterns only; don't frame compatibility as fate
- When data is missing (e.g., no birth time): name the uncertainty and avoid firm conclusions about children, later-life patterns, or career timing

### Saving the report
Write the complete HTML to `reports/<folder>/report.html` and tell the user:
```
报告已生成：reports/<folder>/report.html — 用浏览器打开即可查看。
```

## Step 5: Handle Common Situations

### User provides only a date, no time
- Omit `--time`. The script skips the hour pillar.
- In the report: state that without birth time, the hour pillar is unknown, and time-sensitive interpretations (children, later life, detailed career timing) are uncertain.

### User provides lunar date
- Set `--calendar lunar`.
- Ask whether it's a leap month. If the user isn't sure, try without `--is-leap-month` first. If the script returns `LUNAR_DATE_INVALID`, try with `--is-leap-month`.

### User mentions a city, not coordinates
- Use WebSearch to find the longitude: search "城市名 经度" and extract the decimal value.
- Pass both `--birthplace <city>` and `--longitude <value>` to the script.
- This is part of Step 1 — birthplace is required.

### Birth date is near a solar term (节气)
- The script uses approximate fixed dates for solar terms (e.g., 立春 ≈ Feb 4). If the birth date is within 1-2 days of a solar term boundary, note in the report that the year or month pillar assignment may need verification with a high-precision ephemeris.

### User doesn't know exact birth time
- It's fine. Proceed without `--time`. Note in the report which interpretations are affected.

### User asks about 大运 or 流年

大运 is computed automatically when `--gender` is provided. It appears in the chart JSON under `dayun`.

For 流年 (yearly cycles), run on-demand:

```bash
python scripts/calculate_liunian.py \
  --chart reports/<folder>/chart.json \
  --years 2026,2027,2028 \
  --output reports/<folder>/liunian.json
```

- `--years` — comma-separated specific years
- `--current-plus 5` — compute current year + next N years
- Multiple sources are merged and deduplicated

If the user asks about specific years: use `--years`. If they ask "recent years" or "near future": use `--current-plus 5`.

### Interpreting 大运/流年

- Each 大运 pillar spans 10 years — think of it as the decade's "climate" or theme
- 流年 is the year's "weather" — shorter-term, situational
- Read the 大运 ten_god against the natal chart: does it strengthen or counteract existing patterns?
- Read 流年 ten_god against both the natal chart and the current 大运 pillar
- Use tendency language: "适合关注", "可能遇到", "是一个适合...的阶段"
- NEVER make predictive claims about specific events (marriage, wealth, disaster)
- When 流年's ten_god matches or clashes with 大运's ten_god, describe the combined effect
