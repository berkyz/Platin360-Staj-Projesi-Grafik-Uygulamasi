import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from dash import Dash, dcc, html, Output, Input
import plotly.graph_objects as go
import flask, threading, webbrowser, requests

# DB bağlantısı
engine = create_engine("sqlite:///data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs = Table("logs", metadata, autoload_with=engine)

# === Veriyi işle ===
def get_processed_data():
    stmt = select(
        logs.c["date"], logs.c["time"], logs.c["c-ip"], logs.c["cs-uri-stem"], logs.c["sc-status"], logs.c["is_bot"]
    ).where(logs.c["sc-status"] == 200).where(logs.c["is_bot"] == 0)

    df = pd.read_sql(stmt, con=engine)
    df.columns = ["date", "time", "ip", "page", "status", "is_bot"]

    def son_iki_rakam_mi(s):
        s = s.strip("/")
        return len(s) >= 2 and s[-2:].isdigit()

    rows = []
    for tarih, df_tarih in df.groupby("date"):
        for ip, df_ip in df_tarih.groupby("ip"):
            df_ip = df_ip.sort_values("time")
            sayfalar = df_ip["page"].tolist()

            slash_indexes = [i for i, p in enumerate(sayfalar) if p == "/"]
            arama_indexes = [i for i, p in enumerate(sayfalar) if p.startswith("/arama")]

            slash_sonrasi = [
                sayfalar[i + 1] for i in slash_indexes
                if i + 1 < len(sayfalar) and son_iki_rakam_mi(sayfalar[i + 1])
            ]
            arama_sonrasi = [
                sayfalar[i + 1] for i in arama_indexes
                if i + 1 < len(sayfalar) and son_iki_rakam_mi(sayfalar[i + 1])
            ]

            if not slash_sonrasi and not arama_sonrasi:
                continue

            rows.append({
                "date": tarih,
                "ip": ip,
                "slash_sonrasi_sayfalar": ",".join(slash_sonrasi),
                "arama_sonrasi_sayfalar": ",".join(arama_sonrasi)
            })

    return pd.DataFrame(rows)

df = get_processed_data()

def sayfa_frekans(df, kolon_adi):
    all_pages = df[kolon_adi].dropna().astype(str).str.split(',')
    flat_list = [p.strip() for sublist in all_pages for p in sublist if p.strip() not in ['/', '/arama']]
    short_pages = [p.split("/")[1] if p.count("/") > 1 else p for p in flat_list]
    s = pd.Series(short_pages).value_counts()
    s.index.name = "Sayfa"
    return s

def gunluk_toplam_ziyaret(df):
    def say(s):
        if pd.isna(s) or s == "":
            return 0
        return len([p for p in s.split(',') if p.strip() not in ['/', '/arama']])

    df["ana_sayfa_ziyaret"] = df["slash_sonrasi_sayfalar"].apply(say)
    df["arama_ziyaret"] = df["arama_sonrasi_sayfalar"].apply(say)

    return df.groupby("date")[["ana_sayfa_ziyaret", "arama_ziyaret"]].sum().reset_index()

toplam_ziyaret = gunluk_toplam_ziyaret(df)

# === Dash Uygulaması ===
server = flask.Flask(__name__)
app = Dash(__name__, server=server)

app.layout = html.Div([
    html.H2("📊 Günlük Ziyaretler (Ana Sayfa / Arama Sonrası)", style={"textAlign": "center"}),
    dcc.Graph(id='gunluk-ziyaret-grafik'),
    html.Div(id='detay-grafikler'),
    html.Button("Sayfayı Durdur", id="stop-btn", n_clicks=0, style={"margin": "20px", "backgroundColor": "crimson", "color": "white"})
])

@app.callback(
    Output('gunluk-ziyaret-grafik', 'figure'),
    Input('gunluk-ziyaret-grafik', 'clickData')
)
def goster_gunluk_grafik(clickData):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=toplam_ziyaret['date'],
        y=toplam_ziyaret['ana_sayfa_ziyaret'],
        name="Ana Sayfa Sonrası",
        text=toplam_ziyaret['ana_sayfa_ziyaret'],
        textposition='outside'
    ))
    fig.add_trace(go.Bar(
        x=toplam_ziyaret['date'],
        y=toplam_ziyaret['arama_ziyaret'],
        name="Arama Sonrası",
        text=toplam_ziyaret['arama_ziyaret'],
        textposition='outside'
    ))
    fig.update_layout(
        barmode='group',
        xaxis_title="Tarih",
        yaxis_title="Ziyaret Sayısı",
        title="Günlük Ziyaretler",
        yaxis=dict(tickformat='d')
    )
    return fig

@app.callback(
    Output('detay-grafikler', 'children'),
    Input('gunluk-ziyaret-grafik', 'clickData')
)
def goster_detaylar(clickData):
    if clickData is None:
        return html.Div("Bir tarih seçin")

    secilen = clickData['points'][0]['x']
    df_gun = df[df['date'] == secilen]

    ana_df = df_gun[df_gun['slash_sonrasi_sayfalar'].notna()]
    arama_df = df_gun[df_gun['arama_sonrasi_sayfalar'].notna()]

    ana_freq = sayfa_frekans(ana_df, 'slash_sonrasi_sayfalar')
    arama_freq = sayfa_frekans(arama_df, 'arama_sonrasi_sayfalar')

    children = []

    if not ana_freq.empty:
        fig = go.Figure(go.Bar(
            x=ana_freq.head(15).index,
            y=ana_freq.head(15).values,
            text=ana_freq.head(15).values,
            textposition='outside'
        ))
        fig.update_layout(title="Ana Sayfa Sonrası En Çok Gidilen Sayfalar", xaxis_title="Sayfa", yaxis_title="Ziyaret")
        children.append(html.H4("Ana Sayfa Sonrası"))
        children.append(dcc.Graph(figure=fig))

    if not arama_freq.empty:
        fig = go.Figure(go.Bar(
            x=arama_freq.head(15).index,
            y=arama_freq.head(15).values,
            text=arama_freq.head(15).values,
            textposition='outside'
        ))
        fig.update_layout(title="Arama Sonrası En Çok Gidilen Sayfalar", xaxis_title="Sayfa", yaxis_title="Ziyaret")
        children.append(html.H4("Arama Sonrası"))
        children.append(dcc.Graph(figure=fig))

    return html.Div(children)

@app.callback(
    Output('stop-btn', 'disabled'),
    Input('stop-btn', 'n_clicks')
)
@app.callback(
    Output('stop-btn', 'children'),
    Input('stop-btn', 'n_clicks'),
    prevent_initial_call=True
)
def durdur(n):
    if n > 0:
        threading.Thread(target=lambda: requests.post("http://127.0.0.1:9020/shutdown")).start()
        return "Kapatılıyor..."
    return "Sayfayı Durdur"


# === Otomatik aç ===
def open_browser():
    webbrowser.open_new("http://127.0.0.1:9020")

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(debug=False, port=9020)
