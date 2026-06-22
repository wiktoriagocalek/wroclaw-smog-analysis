"""
Pobiera historyczne PM2.5 z archiwum GIOŚ 2024 (ZIP → XLSX).
Wynik: data/historical_pm25.json — średnia PM2.5 za styczeń 2024 per stacja.

Uruchom PRZED viz.py (raz, dane są cache'owane).
"""
import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path("data")
HIST_DIR = DATA_DIR / "historical" / "2024"
OUT_FILE = DATA_DIR / "historical_pm25.json"

# Mapowanie: kod stacji GIOŚ → id stacji używane w dane.json
STACJE_WROC = {
    "DsWrocNaGrob": 115,   # Na Grobli (dane dobowe 24g)
    "DsWrocWybCon": 117,   # Conrada-Korzeniowskiego (dane godzinowe 1g)
    "DsWrocAlWisn": 129,   # Al. Wiśniowa (dane godzinowe 1g)
    # 114 (Bartnicza) i 122 (Orzechowa) nie mierzyły PM2.5 w 2024
}

def czytaj_xlsx(sciezka: Path) -> pd.DataFrame:
    """
    Konwertuje plik GIOŚ XLSX do tidy DataFrame.

    Format pliku:
      Wiersz 0: numery kolumn (ignorujemy)
      Wiersz 1: kody stacji (np. DsWrocNaGrob)
      Wiersze 2-5: metadane (wskaźnik, czas, jednostka, kod stanowiska)
      Wiersz 6+: data/godzina | wartość stacja_1 | wartość stacja_2 | ...
    """
    raw = pd.read_excel(sciezka, header=None)

    # Wiersz 1 = kody stacji, kolumna 0 = "Kod stacji" (label)
    kody = raw.iloc[1, 1:].tolist()  # lista kodów per kolumna

    # Dane zaczynają się od wiersza 6
    dane = raw.iloc[6:, :].copy()
    dane.columns = ["data"] + kody
    dane["data"] = pd.to_datetime(dane["data"], errors="coerce")
    dane = dane.dropna(subset=["data"])

    # Zostaw tylko stacje wrocławskie które są w pliku
    kolumny_wroc = [k for k in kody if k in STACJE_WROC]
    if not kolumny_wroc:
        return pd.DataFrame(columns=["data", "station_id", "pm25"])

    # Melt: szeroka tabela → wąska (jedna stacja = jeden wiersz)
    df = dane[["data"] + kolumny_wroc].melt(
        id_vars="data",
        var_name="kod_stacji",
        value_name="pm25",
    )
    df["station_id"] = df["kod_stacji"].map(STACJE_WROC)
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    return df[["data", "station_id", "pm25"]].dropna()


print("Wczytuję PM2.5 24h (Na Grobli)...")
df_24g = czytaj_xlsx(HIST_DIR / "2024_PM25_24g.xlsx")
print(f"  wierszy: {len(df_24g)}")

print("Wczytuję PM2.5 1h (Conrada, Al. Wiśniowa)...")
df_1g = czytaj_xlsx(HIST_DIR / "2024_PM25_1g.xlsx")

# Dla danych godzinowych: policz średnią dobową
if not df_1g.empty:
    df_1g_dobowe = (
        df_1g
        .assign(dzien=df_1g["data"].dt.date)
        .groupby(["station_id", "dzien"])["pm25"]
        .mean()
        .reset_index()
        .rename(columns={"dzien": "data", "pm25": "pm25"})
    )
    df_1g_dobowe["data"] = pd.to_datetime(df_1g_dobowe["data"])
    print(f"  wierszy (po agregacji dobowej): {len(df_1g_dobowe)}")
else:
    df_1g_dobowe = pd.DataFrame(columns=["data", "station_id", "pm25"])

# Połącz oba pliki
df_24g_dobowe = df_24g.copy()
df_24g_dobowe["data"] = pd.to_datetime(df_24g_dobowe["data"]).dt.normalize()

wszystkie = pd.concat([df_24g_dobowe, df_1g_dobowe], ignore_index=True)

# Styczeń 2024
styczen = wszystkie[
    (wszystkie["data"].dt.year == 2024) &
    (wszystkie["data"].dt.month == 1)
]

print("\nŚrednia PM2.5 w styczniu 2024 per stacja:")
srednie = (
    styczen
    .groupby("station_id")["pm25"]
    .agg(["mean", "count"])
    .reset_index()
)

wynik = {}
for _, row in srednie.iterrows():
    sid = int(row["station_id"])
    mean_val = round(float(row["mean"]), 2)
    count = int(row["count"])
    # ekwiwalent papierosowy: 22 µg/m³ PM2.5 / 24h = 1 papieros
    papierosy_zima = round(mean_val / 22, 1)
    wynik[sid] = {
        "pm25_zima": mean_val,
        "papierosy_zima": papierosy_zima,
        "n_dni": count,
    }
    print(f"  Stacja {sid}: {mean_val:.1f} µg/m³ ({count} dni) → {papierosy_zima} papierosa")

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(wynik, f, ensure_ascii=False, indent=2)

print(f"\n✓ Zapisano: {OUT_FILE}")
