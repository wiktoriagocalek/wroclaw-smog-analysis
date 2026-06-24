"""
GIOŚ API → Google BigQuery loader
ELT pipeline: Extract (GIOŚ API) → Load (BigQuery raw) → Transform (SQL views)

Setup:
  1. pip install google-cloud-bigquery
  2. Create GCP project + enable BigQuery API
  3. Create service account with BigQuery Editor role → download JSON key
  4. Set env variable: export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
  5. Set GCP_PROJECT below to your project ID
  6. Run: python bigquery_loader.py
"""

import os
import datetime
import requests
from time import sleep

from google.cloud import bigquery

# ── Config ──────────────────────────────────────────────────────────────────
GCP_PROJECT = "smog-wroclaw"
DATASET     = "smog_wroclaw"
TABLE_MEASUREMENTS = f"{GCP_PROJECT}.{DATASET}.raw_measurements"
TABLE_STATIONS     = f"{GCP_PROJECT}.{DATASET}.stations"

GIOS_BASE  = "https://api.gios.gov.pl/pjp-api/v1/rest"
CITY       = "Wrocław"
# ────────────────────────────────────────────────────────────────────────────


def fetch_wroclaw_stations() -> list[dict]:
    """Pobiera stacje pomiarowe z GIOŚ API."""
    print("Pobieram stacje z GIOŚ API...")
    stacje = []
    for page in range(30):
        r = requests.get(f"{GIOS_BASE}/station/findAll", params={"page": page, "size": 100}, timeout=15)
        r.raise_for_status()
        batch = r.json().get("Lista stacji pomiarowych", [])
        if not batch:
            break
        stacje.extend(batch)
        sleep(0.2)

    wroclaw = [
        {
            "station_id": int(s["Identyfikator stacji"]),
            "name":       s["Nazwa stacji"],
            "lat":        float(s["WGS84 φ N"]),
            "lon":        float(s["WGS84 λ E"]),
        }
        for s in stacje if s.get("Nazwa miasta") == CITY
    ]
    print(f"  Znaleziono {len(wroclaw)} stacji we Wrocławiu")
    return wroclaw


def fetch_measurements(station_id: int) -> list[dict]:
    """Pobiera czujniki i pomiary dla jednej stacji."""
    r = requests.get(f"{GIOS_BASE}/station/sensors/{station_id}", timeout=15)
    r.raise_for_status()
    czujniki = r.json().get("Lista stanowisk pomiarowych dla podanej stacji", [])

    rows = []
    for czujnik in czujniki:
        sensor_id = czujnik["Identyfikator stanowiska"]
        parameter = czujnik["Wskaźnik - kod"]
        sleep(0.3)

        r2 = requests.get(f"{GIOS_BASE}/data/getData/{sensor_id}", timeout=15)
        if r2.status_code != 200:
            print(f"    Pominięto sensor {sensor_id} ({parameter}) — status {r2.status_code}")
            continue
        for w in r2.json().get("Lista danych pomiarowych", []):
            if w["Wartość"] is not None:
                rows.append({
                    "station_id":  station_id,
                    "parameter":   parameter,
                    "measured_at": w["Data"],
                    "value":       float(w["Wartość"]),
                    "loaded_at":   datetime.datetime.utcnow().isoformat(),
                })
    return rows


def ensure_dataset(client: bigquery.Client) -> None:
    """Tworzy dataset jeśli nie istnieje."""
    dataset_ref = bigquery.Dataset(f"{GCP_PROJECT}.{DATASET}")
    dataset_ref.location = "EU"
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset {DATASET} gotowy")


def ensure_tables(client: bigquery.Client) -> None:
    """Tworzy tabele jeśli nie istnieją."""
    stations_schema = [
        bigquery.SchemaField("station_id", "INTEGER"),
        bigquery.SchemaField("name",       "STRING"),
        bigquery.SchemaField("lat",        "FLOAT"),
        bigquery.SchemaField("lon",        "FLOAT"),
    ]
    measurements_schema = [
        bigquery.SchemaField("station_id",  "INTEGER"),
        bigquery.SchemaField("parameter",   "STRING"),
        bigquery.SchemaField("measured_at", "TIMESTAMP"),
        bigquery.SchemaField("value",       "FLOAT"),
        bigquery.SchemaField("loaded_at",   "TIMESTAMP"),
    ]

    for table_id, schema in [
        (TABLE_STATIONS,     stations_schema),
        (TABLE_MEASUREMENTS, measurements_schema),
    ]:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table, exists_ok=True)
    print("Tabele gotowe")


def load_stations(client: bigquery.Client, stations: list[dict]) -> None:
    """Ładuje metadane stacji do BigQuery (nadpisuje)."""
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("station_id", "INTEGER"),
            bigquery.SchemaField("name",       "STRING"),
            bigquery.SchemaField("lat",        "FLOAT"),
            bigquery.SchemaField("lon",        "FLOAT"),
        ],
    )
    job = client.load_table_from_json(stations, TABLE_STATIONS, job_config=job_config)
    job.result()
    print(f"  Załadowano {len(stations)} stacji")


def load_measurements(client: bigquery.Client, rows: list[dict]) -> None:
    """Ładuje pomiary do BigQuery (append)."""
    if not rows:
        return
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("station_id",  "INTEGER"),
            bigquery.SchemaField("parameter",   "STRING"),
            bigquery.SchemaField("measured_at", "TIMESTAMP"),
            bigquery.SchemaField("value",       "FLOAT"),
            bigquery.SchemaField("loaded_at",   "TIMESTAMP"),
        ],
    )
    job = client.load_table_from_json(rows, TABLE_MEASUREMENTS, job_config=job_config)
    job.result()
    print(f"  Załadowano {len(rows):,} pomiarów")


def deduplicate(client: bigquery.Client) -> None:
    """Usuwa duplikaty z raw_measurements (idempotentne uruchomienia)."""
    query = f"""
    CREATE OR REPLACE TABLE `{TABLE_MEASUREMENTS}` AS
    SELECT * EXCEPT(row_num)
    FROM (
      SELECT *, ROW_NUMBER() OVER (
        PARTITION BY station_id, parameter, measured_at
        ORDER BY loaded_at DESC
      ) AS row_num
      FROM `{TABLE_MEASUREMENTS}`
    )
    WHERE row_num = 1
    """
    client.query(query).result()
    print("  Deduplication gotowa")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    client = bigquery.Client(project=GCP_PROJECT)

    ensure_dataset(client)
    ensure_tables(client)

    stations = fetch_wroclaw_stations()
    load_stations(client, stations)

    all_rows = []
    for s in stations:
        print(f"Pobieram pomiary: {s['name']}...")
        rows = fetch_measurements(s["station_id"])
        all_rows.extend(rows)
        print(f"  {len(rows)} rekordów")
        sleep(0.5)

    print(f"\nŁącznie: {len(all_rows):,} pomiarów → ładuję do BigQuery...")
    load_measurements(client, all_rows)
    deduplicate(client)

    print(f"\nGotowe! Dane w BigQuery: {TABLE_MEASUREMENTS}")
    print("Następny krok: uruchom SQL views z folderu sql/")


if __name__ == "__main__":
    main()
