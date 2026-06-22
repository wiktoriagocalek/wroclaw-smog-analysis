"""
Przetwarza archiwum GIOŚ 2024 → dashboard_data.json
Uruchom PRZED otwarciem dashboard.html.
"""
import pandas as pd
import json
from pathlib import Path

HIST = Path("data/historical/2024")
OUT  = Path("data/dashboard_data.json")

MIESIACE = ["Sty","Lut","Mar","Kwi","Maj","Cze",
            "Lip","Sie","Wrz","Paź","Lis","Gru"]

STACJE_WROC = ["DsWrocWybCon", "DsWrocAlWisn", "DsWrocBartni", "DsWrocNaGrob"]

# ── pomocnicza: wczytaj plik GIOŚ XLSX → tidy DataFrame ────────────────────
def wczytaj(sciezka: Path, stacje_filter: list[str]) -> pd.DataFrame:
    raw  = pd.read_excel(sciezka, header=None)
    kody = raw.iloc[1, 1:].tolist()
    cols = {i+1: k for i, k in enumerate(kody)
            if isinstance(k, str) and k in stacje_filter}
    if not cols:
        return pd.DataFrame(columns=["data","stacja","wartosc"])
    idx  = [0] + list(cols.keys())
    data = raw.iloc[6:, idx].copy()
    data.columns = ["data"] + list(cols.values())
    data["data"] = pd.to_datetime(data["data"], errors="coerce")
    data = data.dropna(subset=["data"])
    df = data.melt(id_vars="data", var_name="stacja", value_name="wartosc")
    df["wartosc"] = pd.to_numeric(df["wartosc"], errors="coerce")
    return df.dropna(subset=["wartosc"])

# ── pomocnicza: heatmapa godzina × miesiąc ─────────────────────────────────
def heatmapa(df: pd.DataFrame, col: str = "wartosc") -> list[dict]:
    df = df.copy()
    df["godzina"] = df["data"].dt.hour
    df["miesiac"] = df["data"].dt.month
    heat = (
        df.groupby(["godzina","miesiac"])[col]
        .mean().round(1).reset_index()
        .rename(columns={col: "v"})
    )
    return heat.to_dict(orient="records")

# ── pomocnicza: sezonowość miesięczna ──────────────────────────────────────
def sezonowosc(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    df["dzien"]   = df["data"].dt.date
    df["miesiac"] = df["data"].dt.month
    # agreguj do doby per stacja, potem średnia
    dobowe = df.groupby(["stacja","dzien","miesiac"])["wartosc"].mean().reset_index()
    sezon  = (
        dobowe.groupby("miesiac")["wartosc"]
        .agg(srednia="mean", minimum="min", maksimum="max")
        .round(1).reset_index()
    )
    sezon["label"] = sezon["miesiac"].apply(lambda m: MIESIACE[m-1])
    return sezon.to_dict(orient="records")

# ══════════════════════════════════════════════════════════════════════════════
# PM2.5 — proxy dla pieców / spalania
# ══════════════════════════════════════════════════════════════════════════════
print("Wczytuję PM2.5 1h...")
pm25_1g = wczytaj(HIST / "2024_PM25_1g.xlsx", STACJE_WROC)
print(f"  {len(pm25_1g):,} pomiarów  |  stacje: {pm25_1g['stacja'].unique().tolist()}")

print("Wczytuję PM2.5 24h (Na Grobli)...")
pm25_24g = wczytaj(HIST / "2024_PM25_24g.xlsx", STACJE_WROC)
pm25_all  = pd.concat([pm25_1g, pm25_24g], ignore_index=True)

heat_pm25  = heatmapa(pm25_all)
sezon_pm25 = sezonowosc(pm25_all)

# ══════════════════════════════════════════════════════════════════════════════
# NO2 — proxy dla ruchu samochodowego
# ══════════════════════════════════════════════════════════════════════════════
print("Wczytuję NO2 1h...")
no2_1g = wczytaj(HIST / "2024_NO2_1g.xlsx", STACJE_WROC)
print(f"  {len(no2_1g):,} pomiarów  |  stacje: {no2_1g['stacja'].unique().tolist()}")

heat_no2  = heatmapa(no2_1g)
sezon_no2 = sezonowosc(no2_1g)

# ══════════════════════════════════════════════════════════════════════════════
# O3 — proxy dla fotochemii (słońce + ciepło)
# ══════════════════════════════════════════════════════════════════════════════
print("Wczytuję O3 1h...")
o3_1g = wczytaj(HIST / "2024_O3_1g.xlsx", STACJE_WROC)
print(f"  {len(o3_1g):,} pomiarów  |  stacje: {o3_1g['stacja'].unique().tolist()}")

heat_o3  = heatmapa(o3_1g)
sezon_o3 = sezonowosc(o3_1g)

# ══════════════════════════════════════════════════════════════════════════════
# KPI (oparte na PM2.5 — główny wskaźnik zdrowotny)
# ══════════════════════════════════════════════════════════════════════════════
kpi_godz = pm25_1g.copy()
kpi_godz["godzina"] = kpi_godz["data"].dt.hour
godz_avg = kpi_godz.groupby("godzina")["wartosc"].mean()
najgorsza_godz  = int(godz_avg.idxmax())
pm25_najgorsza  = round(float(godz_avg.max()), 1)

najgorszy_mies       = int(max(sezon_pm25, key=lambda x: x["srednia"])["miesiac"])
pm25_najgorszy       = round(float(max(sezon_pm25, key=lambda x: x["srednia"])["srednia"]), 1)

conrada = pm25_1g[pm25_1g["stacja"] == "DsWrocWybCon"].copy()
conrada["dzien"] = conrada["data"].dt.date
ekwiwalent_roczny = int((conrada.groupby("dzien")["wartosc"].mean() / 22).sum())

print(f"\nKPI (PM2.5):")
print(f"  Najgorsza godzina: {najgorsza_godz}:00  ({pm25_najgorsza} µg/m³)")
print(f"  Najgorszy miesiąc: {MIESIACE[najgorszy_mies-1]}  ({pm25_najgorszy} µg/m³)")
print(f"  Ekwiwalent roczny: ~{ekwiwalent_roczny} papierosów")

# ══════════════════════════════════════════════════════════════════════════════
# Zapis
# ══════════════════════════════════════════════════════════════════════════════
# ── Średnia godzinowa przez cały rok (dla wykresu liniowego) ───────────────
def hourly_avg(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["godzina"] = d["data"].dt.hour
    return d.groupby("godzina")["wartosc"].mean().round(2).to_dict()

wynik = {
    "pm25": {"heatmap": heat_pm25, "sezonowosc": sezon_pm25,
             "hourly": hourly_avg(pm25_all),
             "who": 15,  "max_skala": 40,  "jednostka": "µg/m³",
             "opis": "PM2.5 — pył zawieszony (proxy: piece, spalanie)"},
    "no2":  {"heatmap": heat_no2,  "sezonowosc": sezon_no2,
             "hourly": hourly_avg(no2_1g),
             "who": 25,  "max_skala": 80,  "jednostka": "µg/m³",
             "opis": "NO₂ — dwutlenek azotu (proxy: ruch samochodowy)"},
    "o3":   {"heatmap": heat_o3,   "sezonowosc": sezon_o3,
             "hourly": hourly_avg(o3_1g),
             "who": 100, "max_skala": 200, "jednostka": "µg/m³",
             "opis": "O₃ — ozon (proxy: fotochemia, lato + słońce)"},
    "kpi": {
        "najgorsza_godzina":          najgorsza_godz,
        "pm25_najgorsza_godzina":     pm25_najgorsza,
        "najgorszy_miesiac":          najgorszy_mies,
        "najgorszy_miesiac_label":    MIESIACE[najgorszy_mies-1],
        "pm25_najgorszy_miesiac":     pm25_najgorszy,
        "ekwiwalent_roczny":          ekwiwalent_roczny,
    }
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(wynik, f, ensure_ascii=False, indent=2)
print(f"\n✓ Zapisano: {OUT}")

# ── Generuj dashboard.html ──────────────────────────────────────────────────
template_path = Path("dashboard_template.html")
dashboard_out = Path("data/dashboard.html")

with open(template_path, encoding="utf-8") as f:
    template = f.read()

html_out = template.replace("__DASH_DATA__", json.dumps(wynik, ensure_ascii=False))

with open(dashboard_out, "w", encoding="utf-8") as f:
    f.write(html_out)
print(f"✓ Zapisano: {dashboard_out}")

# ── Generuj portfolio/project-2.html ───────────────────────────────────────
p2_template = Path("project2_template.html")
p2_out      = Path("../project-2.html")

if p2_template.exists():
    with open(p2_template, encoding="utf-8") as f:
        p2 = f.read()
    p2 = p2.replace("__PROJECT2_DATA__", json.dumps(wynik, ensure_ascii=False))
    with open(p2_out, "w", encoding="utf-8") as f:
        f.write(p2)
    print(f"✓ Zapisano: {p2_out}")
