import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
import dash
from dash import dcc, html
from dash.dash_table import DataTable
from flask import Flask, request
import webbrowser
import threading
import os
import signal

# --- 1. VERİYİ DB'DEN OKU VE İŞLE ---

engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

stmt = select(
    logs_table.c["browser"],
    logs_table.c["date"],
    logs_table.c["is_bot"]
)

df = pd.read_sql(stmt, con=engine)

# Bot olmayanları filtrele
df = df[df["is_bot"] == 0].copy()
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

unique_dates = df["date"].dt.date.unique()
first_15_days = unique_dates[:15]
last_15_days = unique_dates[-15:]

df_ilk_15 = df[df["date"].dt.date.isin(first_15_days)]
df_son_15 = df[df["date"].dt.date.isin(last_15_days)]

browser_counts_ilk_15 = df_ilk_15["browser"].value_counts()
browser_counts_son_15 = df_son_15["browser"].value_counts()

all_browsers = sorted(set(browser_counts_ilk_15.index).union(browser_counts_son_15.index))

comparison_rows = []
for b in all_browsers:
    ilk_adet = browser_counts_ilk_15.get(b, 0)
    son_adet = browser_counts_son_15.get(b, 0)

    if ilk_adet == 0:
        artis_yuzdesi_str = "∞" if son_adet > 0 else "0"
    else:
        artis = ((son_adet - ilk_adet) / ilk_adet) * 100
        artis_yuzdesi_str = f"{artis:+.2f}"

    comparison_rows.append({
        "Tarayıcı": b,
        "İlk 15 Gün (Adet)": ilk_adet,
        "Son 15 Gün (Adet)": son_adet,
        "Yüzde Artış (%)": artis_yuzdesi_str
    })

comparison_df = pd.DataFrame(comparison_rows)

# --- 2. FLASK SERVER VE DASH UYGULAMASI ---

server = Flask(__name__)

@server.route('/shutdown', methods=['POST'])
def shutdown():
    # Ctrl+C sinyali gönderelim
    pid = os.getpid()
    os.kill(pid, signal.SIGINT)
    return 'Server shutting down...', 200

app = dash.Dash(__name__, server=server)
app.title = "Tarayıcı Kullanım Karşılaştırması"

app.layout = html.Div([
    html.H2("📊 Tarayıcı Kullanım Karşılaştırması (İnteraktif)", style={"textAlign": "center"}),

    DataTable(
        id='browser-table',
        columns=[
            {"name": "Tarayıcı", "id": "Tarayıcı", "type": "text"},
            {"name": "İlk 15 Gün (Adet)", "id": "İlk 15 Gün (Adet)", "type": "numeric"},
            {"name": "Son 15 Gün (Adet)", "id": "Son 15 Gün (Adet)", "type": "numeric"},
            {"name": "Yüzde Artış (%)", "id": "Yüzde Artış (%)", "type": "text"},
        ],
        data=comparison_df.to_dict("records"),
        style_cell={'textAlign': 'center', 'fontFamily': 'Arial', 'padding': '8px'},
        style_header={'backgroundColor': '#f4f4f4', 'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {
                    'column_id': 'Yüzde Artış (%)',
                    'filter_query': '{Yüzde Artış (%)} < 0'
                },
                'backgroundColor': '#f2dede',
                'color': '#a10000',
                'fontWeight': 'bold'
            },
            {
                'if': {
                    'column_id': 'Yüzde Artış (%)',
                    'filter_query': '{Yüzde Artış (%)} >= 0'
                },
                'backgroundColor': '#dff0d8',
                'color': '#006400',
                'fontWeight': 'bold'
            }
        ],
        sort_action="native",
        filter_action="native",
        page_size=10
    ),

    html.Button("Sayfayı Durdur", id="shutdown-btn", style={"marginTop": "20px"}),

    # Sayfa kapanınca shutdown isteği gönder
    html.Script('''
        window.addEventListener("beforeunload", function (e) {
            navigator.sendBeacon("/shutdown");
        });
    ''')
])

from dash.dependencies import Input, Output

@app.callback(
    Output('shutdown-btn', 'children'),
    Input('shutdown-btn', 'n_clicks')
)
def shutdown_app(n_clicks):
    if n_clicks:
        import requests
        try:
            requests.post("http://127.0.0.1:9000/shutdown")
        except:
            pass
        return "Uygulama Kapatılıyor..."
    return "Sayfayı Kapat"

def open_browser():
    webbrowser.open_new("http://127.0.0.1:9000")

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=False, port=9000)
