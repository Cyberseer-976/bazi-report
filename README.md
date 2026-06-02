# 四柱八字 Claude Code 技能 · Ba Zi Report Skill

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Skill Type](https://img.shields.io/badge/claude%20code-skill-orange)](https://code.claude.com/docs/zh-CN/skills)

从出生信息生成**四柱八字命理分析报告**的 Claude Code 技能。计算四柱、日主、五行、十神、大运、流年，支持公历/农历、真太阳时校正，输出自包含的 HTML 报告。

A Claude Code skill that generates **Chinese Four Pillars of Destiny (Ba Zi)** analysis reports. Computes pillars, day master, five elements, ten gods, Da Yun (luck pillars), and Liu Nian (yearly cycles). Supports both Gregorian and lunar calendars, true solar time correction, and outputs self-contained HTML reports.

---

## 定位声明 · Disclaimer

本技能基于传统四柱八字体系，适合作为**文化参考和自我观察工具**。命理分析不等同于医学、法律、投资、心理咨询或其他专业意见，也不应替代现实中的专业判断与行动选择。

This skill is a **cultural analysis and self-reflection tool**, NOT fortune-telling, medical advice, or investment guidance.

---

## 功能特性 · Features

- 📅 **四柱排盘** — 年柱/月柱/日柱/时柱，含天干地支及藏干
- 🎯 **日主分析** — 日干五行、阴阳、强弱判断
- 🔢 **五行统计** — 木火土金水分布
- 🏷️ **十神关系** — 天干十神 + 藏干十神 + 地支十神
- 📈 **大运计算** — 顺排/逆排方向、起运年龄、8 步大运（每步 10 年）
- 📆 **流年推演** — 按需计算指定年份或近几年的流年干支与十神
- ⏰ **真太阳时校正** — 根据出生地经度自动校正时间
- 🌙 **农历支持** — 支持公历和农历输入，自动转换
- 📄 **自包含 HTML 报告** — 精美的 CSS 设计系统，五大元素配色，响应式布局，支持打印
- 🔍 **自动经度查询** — Claude 通过 WebSearch 自动查找出生城市的经度

---

## 安装 · Installation

### 1. 克隆仓库

```bash
# 安装为用户级技能（所有项目可用）
git clone https://github.com/Cyberseer-976/bazi-report.git ~/.claude/skills/bazi-report

# 或者安装为项目级技能（仅当前项目）
git clone https://github.com/Cyberseer-976/bazi-report.git .claude/skills/bazi-report
```

### 2. 安装 Python 依赖

```bash
pip install -r ~/.claude/skills/bazi-report/requirements.txt
```

需要 **Python 3.10+**。

---

## 使用方法 · Usage

直接与 Claude 对话即可触发，无需手动调用脚本：

```
帮我算一下四柱八字
```

Claude 会引导你提供以下信息：

| 信息 | 说明 |
|------|------|
| **出生日期** | `YYYY-MM-DD`，公历或农历 |
| **出生时间** | `HH:MM`（24 小时制），未知可省略 |
| **性别** | 男/女，用于大运计算 |
| **出生城市** | 用于真太阳时校正（Claude 自动查找经度） |

对话示例：

> 👤 帮我算一下八字，2000年9月3日早上7点，男，陕西铜川出生
>
> 🤖 好的，我来为你排盘。已查到铜川经度约 108.95°E...（运行计算）
>    📄 报告已生成：reports/2000-09-03_铜川_男/report.html

之后你可以继续追问：

- "帮我看看近三年的流年运势"
- "五行缺什么？"
- "适合做什么工作？"

---

## 项目结构 · Project Structure

```
bazi-report/
├── SKILL.md                         # 技能定义（Claude 的 Playbook）
├── README.md                        # 本文件
├── LICENSE                          # MIT
├── requirements.txt                 # Python 依赖
├── .gitignore
├── scripts/
│   ├── calculate_bazi.py            # 核心排盘计算
│   ├── calculate_liunian.py         # 流年计算
│   └── generate_report_data.py      # 报告数据格式化
├── assets/
│   └── report_template.html         # HTML 报告模板（含完整 CSS 设计系统）
├── references/
│   ├── interpretation_rules.md      # 解读规则与措辞约束
│   ├── report_schema.md             # 报告章节结构
│   ├── terminology.md               # 术语表
│   └── disclaimers.md               # 免责声明模板
└── reports/                         # 生成的报告（gitignored）
```

---

## 工作原理 · How It Works

整个流程由 **Claude 驱动**，Python 脚本只负责确定性计算：

```
用户对话 → Claude 收集信息 → Claude 调用脚本 → 脚本返回 JSON → Claude 解读 + 填模板 → HTML 报告
```

| 脚本 | 职责 |
|------|------|
| `calculate_bazi.py` | 核心排盘：四柱干支、日主、五行、十神、藏干、大运、格局诊断、地支关系、空亡 |
| `generate_report_data.py` | 数据增强：将原始 JSON 转为报告友好的结构化摘要 |
| `calculate_liunian.py` | 流年计算：指定年份的干支与十神，与大运交叉引用 |

用户**从不直接与脚本交互** — Claude 处理所有对话、信息收集和解读。

---

## 依赖 · Dependencies

- **Python** ≥ 3.10
- **[lunar-python](https://pypi.org/project/lunar-python/)** ≥ 1.6.0 — 农历日期转换与精确节气计算

---

## 贡献 · Contributing

欢迎贡献！以下方向特别受欢迎：

- 🐛 Bug 修复和脚本改进
- 📝 解读规则与参考文档的补充
- 🌐 多语言支持（英文报告模板）
- ✨ 新的诊断规则和格局识别
- 📊 更好的报告可视化

请提交 Issue 或 Pull Request。

---

## 许可 · License

MIT © Ba Zi Report Contributors
