# Wrocław Smog Analysis — Furnace or Engine?

**[→ Live demo](https://wiktoriagocalek.github.io/project-4.html)**

**Who is actually responsible for Wrocław's smog — home heating or road traffic — and does the answer change depending on the hour, month, or season?**

Full-year hourly analysis of PM2.5 and NO₂ data from GIOŚ (Poland's Chief Inspectorate for Environmental Protection) across all of 2024, revealing two completely different pollution profiles driven by two completely different sources.

---

## Highlights

| | |
|---|---|
| **Hourly measurements** | 17,000+ (full year 2024 · GIOŚ archive) |
| **PM2.5 daily peak** | 22:00 — 18.3 µg/m³ (evening heating) |
| **Cigarette equivalent** | 261 cigarettes/year (PM2.5 annual exposure) |
| **Worst month** | December — avg 25.0 µg/m³ · 1.7× WHO norm |
| **NO₂ peak hours** | 07:00–09:00 and 16:00–18:00 (rush hour) |
| **Verdict** | Furnaces win in winter · Traffic has no season |

---

## Pipeline

```
GIOŚ 2024 archive (XLSX)          GIOŚ live API
─────────────────────────         ──────────────────
powietrze.gios.gov.pl             api.gios.gov.pl
2024_PM25_1g.xlsx                 /v1/rest/station/sensors
2024_NO2_1g.xlsx  (+ 28 more)     /v1/rest/data/getData/
         │                                │
         ▼                                ▼
  smog_historical.py              viz.py
  smog_dashboard.py               · live station readings
  · parse XLSX with openpyxl      · cigarette equivalent
  · hourly averages per month     · per-station insight
  · heatmap matrix (24h × 12m)         │
  · cigarette equivalent calc          ▼
         │                      data/wroclaw-mapa-dane.html
         ▼                      (Leaflet.js live map)
  data/dashboard_data.json
         │
         ▼
  project-4.html
  (portfolio page — SVG charts, heatmap, bilingual)
```

---

## File structure

```
smog-analysis/
├── smog_dashboard.py       # main pipeline: XLSX → heatmaps + portfolio page
├── smog_historical.py      # Jan 2024 PM2.5 baseline (cigarette equivalent)
├── smog.py                 # data collection utilities
├── viz.py                  # live GIOŚ API → Leaflet.js map
├── notebooks/
│   └── 01_collect.ipynb    # exploratory data collection
├── data/
│   ├── stacje.csv              # Wrocław monitoring stations metadata
│   ├── pomiary.csv             # recent hourly measurements
│   ├── dashboard_data.json     # processed yearly data (heatmaps, KPIs)
│   └── historical/             # 2024 XLSX archives (download separately)
├── README.md
└── .gitignore
```

---

## Stack

- Python 3.10+
- [pandas](https://pandas.pydata.org/) — time-series aggregation
- [openpyxl](https://openpyxl.readthedocs.io/) — XLSX parsing
- [requests](https://requests.readthedocs.io/) — GIOŚ REST API
- [Leaflet.js](https://leafletjs.com/) + Leaflet.heat — interactive map (frontend)

---

## How to run

```bash
pip install -r requirements.txt

# 1. Download 2024 GIOŚ archive (48 MB, not included in repo)
curl -L "https://powietrze.gios.gov.pl/pjp/archives/downloadFile/582" -o data/historical/2024.zip
cd data/historical && unzip 2024.zip -d 2024/ && cd ../..

# 2. Process historical data
python smog_historical.py   # → Jan 2024 baseline
python smog_dashboard.py    # → dashboard_data.json + project-4.html

# 3. Generate live station map
python viz.py               # fetches current readings from GIOŚ API
```

---

## Data sources

| Source | Dataset | Licence |
|--------|---------|---------|
| [GIOŚ](https://powietrze.gios.gov.pl/pjp/archives) | 2024 annual XLSX archives | Open (Polish public data) |
| [GIOŚ API](https://api.gios.gov.pl/pjp-api/v1/rest/) | Live hourly readings | Open |
| [WHO](https://www.who.int/news-room/feature-stories/detail/what-are-the-who-air-quality-guidelines) | Air quality guidelines | PM2.5: 15 µg/m³/day · NO₂: 25 µg/m³/day |
| Brennan et al. (2015) | Cigarette equivalent | 22 µg/m³ PM2.5 per 24h ≈ 1 cigarette |

---

## Monitoring stations (Wrocław)

| Code | Location | Measures |
|------|----------|---------|
| DsWrocWybCon | Wybrzeże Conrada | PM2.5, NO₂, O₃ |
| DsWrocAlWisn | Al. Wiśniowa | PM2.5, NO₂ |
| DsWrocNaGrob | Na Grobli | PM2.5 (24h avg) |
| DsWrocBartni | ul. Bartnicza | NO₂, NO, O₃ |

---

*Wiktoria Gocałek · 2026 · [portfolio](https://wiktoriagocalek.github.io)*
