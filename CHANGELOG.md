# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-02

### Added

- Initial release: Ba Zi Report Claude Code skill
- Core Ba Zi chart calculator (`calculate_bazi.py`) — four pillars, day master, five elements, ten gods, hidden stems, Da Yun (luck pillars)
- Liu Nian (yearly cycle) calculator (`calculate_liunian.py`)
- Report data enricher (`generate_report_data.py`)
- Self-contained HTML report template with five-element color design system
- Gregorian and lunar calendar support via `lunar-python`
- True solar time correction based on birthplace longitude
- Diagnostic system: day master strength (得令/得地/同异党), pattern candidates (格局), branch interactions (合冲刑害空亡)
- Reference documentation: interpretation rules, report schema, terminology glossary, disclaimers
- Bilingual README (Chinese/English)

[1.0.0]: https://github.com/Cyberseer-976/bazi-report/releases/tag/v1.0.0
