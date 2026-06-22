# Wrocław Smog Analysis — Furnace or Engine?

**Who is responsible for Wrocław's smog: road transport or home heating?**

A full-year hourly analysis of air quality data from GIOŚ (Poland's Chief Inspectorate for Environmental Protection), comparing two key pollution markers across all of 2024:

- **PM2.5** — fine particulate matter, proxy for home heating / solid fuel combustion
- **NO₂** — nitrogen dioxide, proxy for road traffic / diesel engines

→ **[Live project in portfolio](https://wiktoriagocalek.github.io/portfolio/project-2.html)**

---

## Key Findings

| | PM2.5 (furnaces) | NO₂ (traffic) |
|---|---|---|
| **Seasonality** | Explodes Nov–Feb, near-zero May–Sep | Constant year-round |
| **Daily peak** | 21:00–23:00 (evening heating) | 07:00–09:00 & 16:00–18:00 (rush hour) |
| **WHO exceedance** | Up to 3× norm on winter nights | Moderate, stable 0.5–1× norm |
| **Verdict** | Wins in winter | Has no season |

> On cold winter evenings, low-level heating emissions generate pollution **several times exceeding** traffic emissions. But traffic never takes a day off.

---

## Project Structure

```
smog-analysis/
├── viz.py                  # Interactive Leaflet map with live GIOŚ API data
├── smog_dashboard.py       # Main pipeline: 2024 archives → charts + portfolio page
├── smog_historical.py      # Jan 2024 PM2.5 baseline (cigarette equivalent)
├── smog.py                 # Data collection utilities
├── project2_template.html  # Portfolio page template (EN/PL, SVG charts)
├── dashboard_template.html # Standalone dashboard template
├── data/
│   ├── dashboard_data.json     # Processed yearly data (heatmaps, hourly averages, KPIs)
│   ├── historical_pm25.json    # January 2024 PM2.5 baseline per station
│   ├── dane.json               # Live station readings
│   ├── stacje.csv              # Wrocław monitoring stations metadata
│   ├── pomiary.csv             # Recent hourly measurements
│   └── wroclaw-mapa.html       # Minimalist Leaflet map base
└── notebooks/
    └── 01_collect.ipynb        # Exploratory data collection
```

---

## Tech Stack

- **Python** — pandas, openpyxl, requests, json
- **Visualization** — pure SVG (no charting library), Leaflet.js, Leaflet.heat
- **Data source** — [GIOŚ API v1](https://api.gios.gov.pl/pjp-api/v1/rest/) + 2024 annual archives

---

## How to Run

**1. Install dependencies**
```bash
pip install pandas openpyxl requests
```

**2. Download 2024 GIOŚ archive** (48 MB, not included in repo)
```bash
curl -L "https://powietrze.gios.gov.pl/pjp/archives/downloadFile/582" -o data/historical/2024.zip
cd data/historical && unzip 2024.zip -d 2024/
```

**3. Process data & generate pages**
```bash
python smog_historical.py   # baseline Jan 2024
python smog_dashboard.py    # heatmaps, charts, portfolio page → project-2.html
```

**4. Generate live map**
```bash
python viz.py               # fetches current readings from GIOŚ API
```

---

## Data Sources

- **GIOŚ API** — live hourly readings: `https://api.gios.gov.pl/pjp-api/v1/rest/`
- **GIOŚ 2024 archive** — annual XLSX files: `https://powietrze.gios.gov.pl/pjp/archives/downloadFile/582`
- **WHO thresholds** — PM2.5: 15 µg/m³/day · NO₂: 25 µg/m³/day · O₃: 100 µg/m³ (8h)
- **Cigarette equivalent** — Brennan et al. (2015): 22 µg/m³ PM2.5 per 24h ≈ 1 cigarette

---

## Monitoring Stations (Wrocław)

| Code | Location | Measures |
|---|---|---|
| DsWrocWybCon | Wybrzeże Conrada | PM2.5, NO₂, O₃ |
| DsWrocAlWisn | Al. Wiśniowa | PM2.5, NO₂ |
| DsWrocNaGrob | Na Grobli | PM2.5 (24h avg) |
| DsWrocBartni | ul. Bartnicza | NO₂, NO, O₃ (traffic station) |

---

*Portfolio project by [Wiktoria Gocałek](https://github.com/wiktoriagocalek) · Data Engineering · 2026*
