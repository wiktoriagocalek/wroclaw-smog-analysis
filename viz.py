import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

# --- Wczytaj dane ---
stacje  = pd.read_csv("data/stacje.csv")
pomiary = pd.read_csv("data/pomiary.csv", parse_dates=["data"])

# --- Design system ---
INK     = "#14161c"
INK_SOFT= "#4b4f58"
BG      = "#f4f5f7"
CARD    = "#ffffff"
LINE    = "#e7e8ec"
BLUE    = "#3b55ec"
LIME    = "#b6e000"
PERIWINKLE = "#8da2f1"
KOLORY_STACJI = [BLUE, PERIWINKLE, LIME, "#a78bfa", "#60a5fa"]

# ================================================================
# SEKCJA 1: MAPA — heatmapa PM2.5 + wybielone tło + punkty stacji
# ================================================================

pm25_srednie = (
    pomiary[pomiary["parametr"] == "PM2.5"]
    .groupby("station_id")["wartosc"]
    .mean()
    .reset_index()
    .rename(columns={"wartosc": "pm25_avg"})
)
stacje_heat = stacje.merge(pm25_srednie, on="station_id", how="left")

hover_texts = []
for _, s in stacje.iterrows():
    dane_stacji = pomiary[pomiary["station_id"] == s["station_id"]]
    ostatnie = (
        dane_stacji.sort_values("data")
        .groupby("parametr")["wartosc"]
        .last()
        .dropna()
    )
    linie = "<br>".join(f"<b>{p}</b>: {v:.1f} µg/m³" for p, v in sorted(ostatnie.items()))
    nazwa_skrot = s["nazwa"].replace("Wrocław, ", "")
    hover_texts.append(f"<b>{nazwa_skrot}</b><br><br>{linie}" if linie else f"<b>{nazwa_skrot}</b><br>Brak danych")

fig_mapa = go.Figure()

# Warstwa 1: gradientowe plamy (heatmapa PM2.5)
fig_mapa.add_trace(go.Densitymapbox(
    lat=stacje_heat["lat"],
    lon=stacje_heat["lon"],
    z=stacje_heat["pm25_avg"].fillna(0),
    radius=130,
    opacity=0.6,
    colorscale=[
        [0.0, "rgba(255,255,255,0)"],
        [0.3, "rgba(59,85,236,0.2)"],
        [0.7, "rgba(239,100,80,0.5)"],
        [1.0, "rgba(200,30,30,0.8)"],
    ],
    showscale=False,
    hoverinfo="skip",
))

# Warstwa 2: małe czarne punkty stacji (jak w inspo Baton Rouge)
fig_mapa.add_trace(go.Scattermapbox(
    lat=stacje["lat"],
    lon=stacje["lon"],
    mode="markers",
    marker=dict(size=10, color=INK, opacity=1),
    text=hover_texts,
    hovertemplate="%{text}<extra></extra>",
    hoverlabel=dict(
        bgcolor=CARD,
        bordercolor=LINE,
        font=dict(family="Inter, sans-serif", size=12, color=INK),
    ),
))

fig_mapa.update_layout(
    mapbox=dict(
        style="carto-positron",
        center=dict(lat=51.1, lon=17.03),
        zoom=11.5,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=520,
    paper_bgcolor=CARD,
    showlegend=False,
)

pio.write_html(fig_mapa, "data/mapa_stacji.html", full_html=True, include_plotlyjs="cdn")

print("✓ Mapa zapisana: data/mapa_stacji.html")

# ================================================================
# SEKCJA 2: WYKRES 24H (PM2.5 per stacja)
# ================================================================

pm25 = pomiary[pomiary["parametr"] == "PM2.5"].copy()
pm25 = pm25.sort_values("data")

fig = go.Figure()

for i, (_, s) in enumerate(stacje.iterrows()):
    dane_stacji = pm25[pm25["station_id"] == s["station_id"]]
    if dane_stacji.empty:
        continue
    nazwa_skrot = s["nazwa"].replace("Wrocław, ", "")
    fig.add_trace(go.Scatter(
        x=dane_stacji["data"],
        y=dane_stacji["wartosc"],
        name=nazwa_skrot,
        mode="lines+markers",
        line=dict(color=KOLORY_STACJI[i % len(KOLORY_STACJI)], width=2),
        marker=dict(size=5),
    ))

fig.add_hline(
    y=15, line_dash="dash", line_color="#ef4444",
    annotation_text="norma WHO (15 µg/m³)",
    annotation_font=dict(color="#ef4444", size=11),
)

fig.update_layout(
    font_family="Inter, sans-serif",
    font_color=INK,
    paper_bgcolor=CARD,
    plot_bgcolor=CARD,
    title=dict(text="PM2.5 we Wrocławiu — ostatnie 24h", font=dict(size=16, color=INK), x=0),
    xaxis=dict(showgrid=True, gridcolor=LINE, tickfont=dict(size=11, color=INK_SOFT), title=""),
    yaxis=dict(showgrid=True, gridcolor=LINE, tickfont=dict(size=11, color=INK_SOFT), title="µg/m³"),
    legend=dict(font=dict(size=11), bgcolor=BG, bordercolor=LINE, borderwidth=1),
    margin=dict(l=20, r=20, t=48, b=20),
    height=360,
)

pio.write_html(fig, "data/wykres_24h.html", full_html=False, include_plotlyjs="cdn")
print("✓ Wykres zapisany: data/wykres_24h.html")
print("\nGotowe!")

# ================================================================
# SEKCJA 3: Eksport danych do JSON (dla mapy Leaflet)
# ================================================================

import json

def generuj_insight(station_id: int, pomiary: dict, miesiac: int) -> str | None:
    """Generuje jednozdaniowy insight na podstawie aktualnych pomiarów stacji."""
    WHO = {
        "PM2.5": (10, 25), "PM10": (20, 50),
        "NO2":   (10, 25), "O3":   (60, 100),
        "SO2":   (20, 40), "CO":   (1000, 4000), "C6H6": (1, 5),
    }
    czerwone, zolte = [], []
    for p, v in pomiary.items():
        if p in WHO:
            lo, hi = WHO[p]
            if v > hi:   czerwone.append(p)
            elif v > lo: zolte.append(p)

    lato = miesiac in range(4, 10)   # kwiecień–wrzesień
    zima = not lato

    if "O3" in czerwone and lato:
        return "Podwyższony ozon (O₃) wynika z reakcji fotochemicznych przy wysokim nasłonecznieniu — typowe dla popołudniowych godzin letnich."
    if "O3" in zolte and lato:
        return "Ozon (O₃) na poziomie umiarkowanym — reakcje fotochemiczne aktywne, ale poniżej progu alarmowego WHO."
    if "PM2.5" in czerwone and zima:
        if station_id in (114, 115):
            return "Ekstremalne PM2.5 wywołane niską emisją z ogrzewania domowego przy bezwietrznej pogodzie — efekt inwersji temperatur."
        return "Wysokie PM2.5 to efekt spalania paliw stałych i niekorzystnych warunków atmosferycznych (inwersja temperatur)."
    if "NO2" in czerwone:
        if station_id == 129:
            return "Skok NO₂ koreluje z ruchem samochodowym na Al. Wiśniowej — jednej z ruchliwszych arterii Wrocławia."
        if station_id == 117:
            return "Podwyższone NO₂ przy ul. Conrada-Korzeniowskiego odzwierciedla emisję komunikacyjną tej miejskiej arterii."
        return "Podwyższony NO₂ wskazuje na lokalną emisję komunikacyjną."
    if "PM2.5" in czerwone or "PM10" in czerwone:
        return "Wysoka koncentracja pyłów zawieszonych — zalecane ograniczenie aktywności fizycznej na zewnątrz."
    if "NO2" in zolte:
        if station_id == 129:
            return "Umiarkowane NO₂ na Al. Wiśniowej — emisja komunikacyjna z trasy wylotowej, poniżej progu alarmowego WHO."
        if station_id == 117:
            return "Umiarkowane NO₂ przy ul. Conrada-Korzeniowskiego — typowy poziom dla miejskiej arterii w godzinach szczytu."
        return "Umiarkowany poziom NO₂ — emisja komunikacyjna w tle, poniżej progu alarmowego WHO."
    if "PM2.5" in zolte and lato:
        return "Umiarkowane PM2.5 w sezonie letnim — prawdopodobnie napływ zanieczyszczeń z innych regionów lub lokalny ruch drogowy."
    if not czerwone and not zolte and pomiary:
        return "Wszystkie wskaźniki poniżej norm WHO — dobra jakość powietrza w tej chwili."
    return None


# Wczytaj dane historyczne (styczeń 2024) jeśli dostępne
hist_path = "data/historical_pm25.json"
try:
    with open(hist_path, encoding="utf-8") as f:
        hist = {int(k): v for k, v in json.load(f).items()}
    print(f"✓ Dane historyczne wczytane: {len(hist)} stacji")
except FileNotFoundError:
    hist = {}
    print("⚠ Brak data/historical_pm25.json — uruchom smog_historical.py")

# Stacje z ostatnimi pomiarami per parametr
stacje_json = []
for _, s in stacje.iterrows():
    sid = int(s["station_id"])
    dane_stacji = pomiary[pomiary["station_id"] == sid]
    ostatnie = (
        dane_stacji.sort_values("data")
        .groupby("parametr")["wartosc"]
        .last()
        .dropna()
        .to_dict()
    )
    # Ekwiwalent papierosowy: 22 µg/m³ PM2.5 / 24h = 1 papieros (WHO/Brennan 2015)
    pm25_srednia = pomiary[
        (pomiary["station_id"] == sid) &
        (pomiary["parametr"] == "PM2.5")
    ]["wartosc"].mean()
    papierosy = round(float(pm25_srednia) / 22, 1) if not pd.isna(pm25_srednia) else None

    # Dane historyczne (styczeń 2024)
    hist_stacja = hist.get(sid, {})

    import datetime
    miesiac = datetime.date.today().month
    insight = generuj_insight(sid, ostatnie, miesiac)

    stacje_json.append({
        "id":              sid,
        "nazwa":           s["nazwa"].replace("Wrocław, ", ""),
        "lat":             s["lat"],
        "lon":             s["lon"],
        "pomiary":         ostatnie,
        "papierosy":       papierosy,
        "papierosy_zima":  hist_stacja.get("papierosy_zima"),
        "pm25_zima":       hist_stacja.get("pm25_zima"),
        "insight":         insight,
    })

# Heatmapa: lista [lat, lon, intensywnosc] dla PM2.5
heat_json = []
for _, s in stacje.iterrows():
    val = pomiary[
        (pomiary["station_id"] == s["station_id"]) &
        (pomiary["parametr"] == "PM2.5")
    ]["wartosc"].mean()
    if not pd.isna(val):
        heat_json.append([s["lat"], s["lon"], round(float(val), 2)])

dane_export = {"stacje": stacje_json, "heatmap": heat_json}

with open("data/dane.json", "w", encoding="utf-8") as f:
    json.dump(dane_export, f, ensure_ascii=False, indent=2)

print("✓ Dane zapisane: data/dane.json")

# ================================================================
# SEKCJA 4: Generuj wroclaw-mapa-dane.html (oryginał + nakładka)
# ================================================================

with open("data/wroclaw-mapa.html", "r", encoding="utf-8") as f:
    html = f.read()

nakładka = f"""
  <script>const DANE = {json.dumps(dane_export, ensure_ascii=False)};</script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>

  <style>
    #info-panel {{
      display: none;
      position: fixed;
      z-index: 9999;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.12), 0 16px 32px rgba(0,0,0,0.10);
      padding: 16px;
      min-width: 230px;
      max-width: 280px;
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      pointer-events: all;
    }}
    #info-panel .adres {{
      font-size: 13px; font-weight: 600; color: #111; margin: 0 0 2px;
    }}
    #info-panel .meta {{
      font-size: 10px; color: #999; margin: 0 0 12px;
      letter-spacing: 0.5px; text-transform: uppercase;
    }}
    #info-panel .params {{
      display: flex; flex-wrap: wrap; gap: 5px;
    }}
    /* Chipy parametrów z conditional formatting */
    .chip {{
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      border-radius: 6px;
      padding: 4px 9px;
      font-size: 11px;
      cursor: default;
      transition: opacity 0.1s;
    }}
    .chip:hover {{ opacity: 0.8; }}
    .chip.ok    {{ background: #e8f5e9; color: #2e7d32; }}
    .chip.warn  {{ background: #fff8e1; color: #f57f17; }}
    .chip.bad   {{ background: #fdecea; color: #c62828; }}
    .chip.muted {{ background: #f4f5f7; color: #4b4f58; }}
    .chip .dot  {{ width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }}
    .chip.ok   .dot {{ background: #43a047; }}
    .chip.warn .dot {{ background: #ffa000; }}
    .chip.bad  .dot {{ background: #e53935; }}
    .chip .val {{
      display: none;
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      background: #14161c;
      color: #fff;
      font-size: 11px;
      padding: 4px 9px;
      border-radius: 6px;
      white-space: nowrap;
      pointer-events: none;
      z-index: 9999;
    }}
    .chip:hover .val {{ display: block; }}
    /* Progress bar ekwiwalentu papierosowego */
    .cig-bar-wrap {{
      margin-top: 3px;
      background: #f4f5f7;
      border-radius: 4px;
      height: 6px;
      overflow: hidden;
      width: 100%;
    }}
    .cig-bar {{
      height: 100%;
      border-radius: 4px;
      transition: width 0.4s ease;
    }}
  </style>

  <script>
    window.addEventListener('load', function() {{

      // Zablokuj oddalanie poniżej domyślnego zoomu
      map.setMinZoom(map.getZoom());

      // Heatmapa PM2.5
      const heat = DANE.heatmap.map(([lat, lon, val]) => [lat, lon, val / 25]);
      L.heatLayer(heat, {{
        radius: 80, blur: 60, maxZoom: 14,
        gradient: {{
          0.0: 'rgba(255,255,255,0)',
          0.4: 'rgba(139,162,241,0.3)',
          0.7: 'rgba(59,85,236,0.55)',
          1.0: 'rgba(59,85,236,0.9)'
        }}
      }}).addTo(map);

      // Floating panel (Google Maps style)
      const panel = document.createElement('div');
      panel.id = 'info-panel';
      document.body.appendChild(panel);

      let hideTimer;

      // Progi WHO dla conditional formatting chipów
      const WHO = {{
        'PM2.5': [10, 25], 'PM10': [20, 50],
        'NO2': [10, 25], 'O3': [60, 100],
        'SO2': [20, 40], 'CO': [1000, 4000], 'C6H6': [1, 5],
      }};
      function chipClass(param, val) {{
        const t = WHO[param];
        if (!t) return 'muted';
        return val < t[0] ? 'ok' : val < t[1] ? 'warn' : 'bad';
      }}

      function showPanel(s, e) {{
        clearTimeout(hideTimer);
        const n = Object.keys(s.pomiary).length;
        const chipy = Object.entries(s.pomiary)
          .sort(([a],[b]) => a.localeCompare(b))
          .map(([p,v]) => {{
            const cls = chipClass(p, v);
            return `<span class="chip ${{cls}}"><span class="dot"></span>${{p}}<span class="val">${{v.toFixed(1)}} µg/m³</span></span>`;
          }})
          .join('');

        const brakDanych = n === 0;

        // Ekwiwalent papierosowy z progress barem (skala 0–10) i porównaniem zimowym
        let papierosyHtml = '';
        if (s.papierosy === null || s.papierosy === undefined) {{
          papierosyHtml = `
            <div style="margin-top:12px;padding-top:10px;border-top:1px solid #e7e8ec;">
              <p style="font-size:10px;color:#999;margin:0 0 4px;letter-spacing:0.5px;text-transform:uppercase;">Ekwiwalent papierosowy</p>
              <p style="font-size:11px;color:#bbb;margin:0;">Stacja nie mierzy PM2.5 — ekwiwalent niedostępny.</p>
            </div>`;
        }} else {{
          const pct      = Math.min(s.papierosy / 10 * 100, 100);
          const barColor = s.papierosy < 0.5 ? '#43a047' : s.papierosy < 1 ? '#ffa000' : '#e53935';
          const label    = s.papierosy < 0.5 ? 'bezpiecznie' : s.papierosy < 1 ? 'umiarkowanie' : 'wysoko';

          let zimaHtml = '';
          if (s.papierosy_zima !== null && s.papierosy_zima !== undefined) {{
            const zimaPct   = Math.min(s.papierosy_zima / 10 * 100, 100);
            const zimaColor = s.papierosy_zima < 0.5 ? '#43a047' : s.papierosy_zima < 1 ? '#ffa000' : '#e53935';
            zimaHtml = `
              <div style="margin-top:8px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                  <span style="font-size:10px;color:#bbb;">Styczeń 2024 (śr. miesięczna)</span>
                  <span style="font-size:10px;font-weight:600;color:${{zimaColor}}">${{s.papierosy_zima.toFixed(1)}} pap.</span>
                </div>
                <div class="cig-bar-wrap" style="background:#f0f0f0;">
                  <div class="cig-bar" style="width:${{zimaPct}}%;background:${{zimaColor}};opacity:0.45;"></div>
                </div>
              </div>`;
          }}

          papierosyHtml = `
            <div style="margin-top:12px;padding-top:10px;border-top:1px solid #e7e8ec;">
              <p style="font-size:10px;color:#999;margin:0 0 6px;letter-spacing:0.5px;text-transform:uppercase;">Ekwiwalent papierosowy</p>
              <div style="display:flex;align-items:baseline;gap:4px;margin-bottom:5px;">
                <span style="font-size:18px;font-weight:700;color:#111;">${{s.papierosy.toFixed(1)}}</span>
                <span style="font-size:11px;color:#4b4f58;"> papierosa / dobę</span>
                <span style="font-size:10px;color:${{barColor}};font-weight:600;margin-left:auto;">${{label}}</span>
              </div>
              <div class="cig-bar-wrap">
                <div class="cig-bar" style="width:${{pct}}%;background:${{barColor}};"></div>
              </div>
              ${{zimaHtml}}
              <p style="font-size:10px;color:#bbb;margin:6px 0 0;">WHO: 22 µg/m³ PM2.5 / 24h = 1 papieros · skala 0–10</p>
            </div>`;
        }}

        const insightHtml = s.insight ? `
          <div style="margin-top:8px;padding-top:8px;border-top:1px solid #f4f5f7;">
            <p style="font-size:10px;color:#aaa;font-style:italic;margin:0;line-height:1.5;">
              ${{s.insight}}
            </p>
          </div>` : '';

        panel.innerHTML = `
          <p class="adres">${{s.nazwa}}</p>
          <p class="meta">${{brakDanych ? 'brak aktualnych danych · stacja GIOŚ' : n + ' czujnik' + (n===1?'':n<5?'i':'ów') + ' · stacja GIOŚ'}}</p>
          <div class="params">${{brakDanych ? '<span style="font-size:11px;color:#999;">Czujnik prawdopodobnie w serwisie.</span>' : chipy}}</div>
          ${{papierosyHtml}}
          ${{insightHtml}}`;

        // Pozycja przy kursorze, nie wychodzi poza ekran
        const x = Math.min(e.originalEvent.clientX + 16, window.innerWidth - 300);
        const y = Math.min(e.originalEvent.clientY - 10, window.innerHeight - 200);
        panel.style.left = x + 'px';
        panel.style.top  = y + 'px';
        panel.style.display = 'block';
      }}

      function scheduleHide() {{
        hideTimer = setTimeout(() => {{ panel.style.display = 'none'; }}, 200);
      }}

      panel.addEventListener('mouseenter', () => clearTimeout(hideTimer));
      panel.addEventListener('mouseleave', scheduleHide);

      // Markery stacji — koncentryczne koła (rozmiar = liczba czujników)
      function bullseye(n, color) {{
        const base = 10 + n * 2.5;  // rozmiar zależny od liczby czujników
        const size = base * 2 + 20;
        const cx = size / 2;
        const rings = [
          {{ r: base + 10, op: 0.04 }},
          {{ r: base + 6,  op: 0.07 }},
          {{ r: base + 2,  op: 0.12 }},
          {{ r: base - 2,  op: 0.20 }},
          {{ r: base - 6,  op: 0.40 }},
          {{ r: 4,          op: 1.00 }},
        ].filter(ring => ring.r > 0);

        const circles = rings.map(ring =>
          `<circle cx="${{cx}}" cy="${{cx}}" r="${{ring.r}}" fill="${{color}}" opacity="${{ring.op}}"/>`
        ).join('');

        const svg = `<svg width="${{size}}" height="${{size}}" viewBox="0 0 ${{size}} ${{size}}" xmlns="http://www.w3.org/2000/svg">${{circles}}</svg>`;

        return L.divIcon({{
          html: svg,
          className: '',
          iconSize: [size, size],
          iconAnchor: [cx, cx],
        }});
      }}

      DANE.stacje.forEach(s => {{
        const n = Object.keys(s.pomiary).length;
        const brakDanych = n === 0;
        const kolor = brakDanych ? '#b0b3bb' : '#3b55ec';
        const rozmiar = brakDanych ? 3 : n;

        const marker = L.marker([s.lat, s.lon], {{
          icon: bullseye(rozmiar, kolor),
          interactive: true,
        }}).addTo(map);

        marker.on('mouseover', (e) => showPanel(s, e));
        marker.on('mouseout', scheduleHide);
      }});

    }});
  </script>
"""

# Wstaw przed </body>
html_out = html.replace("</body>", nakładka + "\n</body>")

with open("data/wroclaw-mapa-dane.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("✓ Mapa z danymi: data/wroclaw-mapa-dane.html")
