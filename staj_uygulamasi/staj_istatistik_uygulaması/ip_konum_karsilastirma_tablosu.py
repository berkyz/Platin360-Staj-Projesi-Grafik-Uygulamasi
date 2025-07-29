import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from dash import Dash, dcc, html, Input, Output, dash_table
import concurrent.futures
import threading
import requests
import webbrowser
import os
import signal
import pycountry

# === Ülke kodunu tam isme çevir (önbellekli) ===
_country_cache = {}
def get_country_name(code):
    if not code:
        return "Bilinmiyor"
    code = code.upper()
    if code in _country_cache:
        return _country_cache[code]
    try:
        country = pycountry.countries.get(alpha_2=code)
        name = country.name if country else code
    except:
        name = code
    _country_cache[code] = name
    return name

# === DB bağlantısı ===
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# === logs tablosundan gerekli verileri çek ===
with engine.connect() as conn:
    stmt = select(
        logs_table.c["date"],
        logs_table.c["c-ip"],
        logs_table.c["country"],
        logs_table.c["city"],
        logs_table.c["lat"],
        logs_table.c["lon"]
    )
    df = pd.read_sql(stmt, conn)

# === Tarih düzenle ===
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])
df = df.sort_values("date").reset_index(drop=True)

# === Ülke kodlarını ülke ismine çevir (paralel) ===
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    df["country_full"] = list(executor.map(get_country_name, df["country"]))

# === İlk ve son 15 gün ===
unique_dates = df["date"].dt.date.unique()
first_15 = unique_dates[:15]
last_15 = unique_dates[-15:]

df_first = df[df["date"].dt.date.isin(first_15)]
df_last = df[df["date"].dt.date.isin(last_15)]

# === Ülke bazlı sayımlar ===
first_counts = df_first["country_full"].value_counts()
last_counts = df_last["country_full"].value_counts()
all_countries = sorted(set(first_counts.index).union(last_counts.index))

rows = []
for country in all_countries:
    c1 = first_counts.get(country, 0)
    c2 = last_counts.get(country, 0)
    if c1 == 0:
        change_str = "N/A"
    else:
        change = ((c2 - c1) / c1) * 100
        change_str = f"{change:+.2f}%"
    rows.append({
        "Ülke": country,
        "İlk 15 Gün Ziyaretçi": c1,
        "Son 15 Gün Ziyaretçi": c2,
        "Yüzde Artış(%)": change_str
    })

df_result = pd.DataFrame(rows)

# === Dash Arayüzü ===
app = Dash(__name__)
app.title = "Ülke Bazlı Ziyaretçi Karşılaştırması"

app.layout = html.Div([
    html.H2("🌍 Ülke Bazlı Ziyaretçi Karşılaştırması (İnteraktif)", style={"textAlign": "center"}),

    dash_table.DataTable(
        id='country-table',
        columns=[
            {"name": col, "id": col, "type": "text" if col in ["Ülke", "Yüzde Artış(%)"] else "numeric"}
            for col in df_result.columns
        ],
        data=df_result.to_dict("records"),
        style_table={'height': '600px', 'overflowY': 'auto'},
        fixed_rows={'headers': True},
        style_cell={'textAlign': 'center', 'fontFamily': 'Arial', 'padding': '8px', 'minWidth': '120px'},
        style_header={'backgroundColor': '#f4f4f4', 'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'column_id': 'Yüzde Artış(%)', 'filter_query': '{Yüzde Artış(%)} contains "-"'},
                'backgroundColor': '#f2dede', 'color': '#a10000', 'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'Yüzde Artış(%)', 'filter_query': '{Yüzde Artış(%)} contains "+"'},
                'backgroundColor': '#dff0d8', 'color': '#006400', 'fontWeight': 'bold'
            }
        ],
        sort_action="native",
        filter_action="native",
        page_action='none'
    ),

    html.Button('Sayfayı Durdur', id='shutdown-btn', style={'margin': '20px'}),
    html.Div(id='shutdown-message', style={"color": "red", "fontWeight": "bold"})
])

# === Dash uygulamasını durdurma ===
@app.callback(
    Output('shutdown-message', 'children'),
    Input('shutdown-btn', 'n_clicks'),
    prevent_initial_call=True
)
def shutdown_app(n_clicks):
    if n_clicks:
        threading.Thread(target=lambda: requests.post("http://127.0.0.1:9050/shutdown")).start()
        return "Uygulama durduruluyor..."

@app.server.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return "Sunucu kapatılıyor..."

# === Uygulama Başlat ===
if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:9050")).start()
    app.run(debug=False, port=9050)
