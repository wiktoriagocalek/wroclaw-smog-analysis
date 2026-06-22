import requests
import pandas as pd
from time import sleep

BASE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"

# --- KROK 1: Pobierz wszystkie stacje i odfiltruj Wrocław ---
print("Pobieram stacje...")

wszystkie_stacje = []
for page in range(30):
    r = requests.get(f"{BASE_URL}/station/findAll", params={"page": page, "size": 100})
    dane = r.json()
    stacje_na_stronie = dane.get("Lista stacji pomiarowych", [])
    if not stacje_na_stronie:
        break
    wszystkie_stacje.extend(stacje_na_stronie)
    sleep(0.2)

wroclaw = [s for s in wszystkie_stacje if s.get("Nazwa miasta") == "Wrocław"]
print(f"Stacje we Wrocławiu: {len(wroclaw)}")

stacje_df = pd.DataFrame([{
    "station_id": s["Identyfikator stacji"],
    "nazwa":      s["Nazwa stacji"],
    "lat":        float(s["WGS84 φ N"]),
    "lon":        float(s["WGS84 λ E"]),
} for s in wroclaw])

# --- KROK 2: Pobierz czujniki dla każdej stacji ---
print("\nPobieram czujniki...")

czujniki_lista = []
for _, stacja in stacje_df.iterrows():
    r = requests.get(f"{BASE_URL}/station/sensors/{stacja['station_id']}")
    czujniki = r.json().get("Lista stanowisk pomiarowych dla podanej stacji", [])
    for c in czujniki:
        czujniki_lista.append({
            "sensor_id":   c["Identyfikator stanowiska"],
            "station_id":  stacja["station_id"],
            "nazwa_stacji": stacja["nazwa"],
            "parametr":    c["Wskaźnik"],
            "kod":         c["Wskaźnik - kod"],
        })
    print(f"  {stacja['nazwa']}: {len(czujniki)} czujników")
    sleep(0.3)

czujniki_df = pd.DataFrame(czujniki_lista)
print(f"\nWszystkie parametry: {czujniki_df['kod'].unique()}")

# --- KROK 3: Pobierz pomiary ---
print("\nPobieram pomiary (to chwilę potrwa)...")

pomiary_lista = []
for _, czujnik in czujniki_df.iterrows():
    r = requests.get(f"{BASE_URL}/data/getData/{czujnik['sensor_id']}")
    wartosci = r.json().get("Lista danych pomiarowych", [])
    for w in wartosci:
        if w["Wartość"] is not None:
            pomiary_lista.append({
                "station_id": czujnik["station_id"],
                "nazwa_stacji": czujnik["nazwa_stacji"],
                "parametr":   czujnik["kod"],
                "data":       w["Data"],
                "wartosc":    w["Wartość"],
            })
    sleep(0.3)

pomiary_df = pd.DataFrame(pomiary_lista)
print(f"Pobrano {len(pomiary_df):,} pomiarów")

# --- KROK 4: Zapisz do CSV ---
stacje_df.to_csv("data/stacje.csv", index=False)
czujniki_df.to_csv("data/czujniki.csv", index=False)
pomiary_df.to_csv("data/pomiary.csv", index=False)

print("\nZapisano pliki:")
print("  data/stacje.csv")
print("  data/czujniki.csv")
print("  data/pomiary.csv")
print("\nPodgląd pomiarów:")
print(pomiary_df.head(10))
