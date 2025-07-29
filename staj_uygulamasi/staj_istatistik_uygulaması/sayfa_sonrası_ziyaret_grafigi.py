import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from dash import Dash, dcc, html, Output, Input
import plotly.graph_objects as go
import threading
import requests

# DB bağlantısı
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

def fetch_real_user_page_visits():
    with engine.connect() as conn:
        query = (
            select(
                logs_table.c.date,
                logs_table.c.time,
                logs_table.c["c-ip"].label("ip"),
                logs_table.c["cs-uri-stem"].label("page"),
                logs_table.c["is_bot"],
                logs_table.c["sc-status"]
            )
            .where(logs_table.c.is_bot == 0)
            .where(logs_table.c["sc-status"] == 200)
        )
        df = pd.read_sql(query, conn)

    # Temizlik
    df['date'] = df['date'].astype(str).str.strip()
    df['time'] = df['time'].astype(str).str.strip()
    df['page'] = df['page'].astype(str).str.strip()
    return df

# Son iki rakam mı, vektörize ederek hızlandırabiliriz
def son_iki_rakam_mi_vectorized(pages):
    pages = pages.str.strip('/')
    mask = pages.str.len() >= 2
    last_two = pages.str[-2:]
    return mask & last_two.str.isdigit()

def process_page_visits_vectorized(df):
    # Her grup için işlem yapmak yerine vektörize edelim

    # Sort et
    df_sorted = df.sort_values(['date', 'ip', 'time'])

    # Her kaydın bir sonraki kaydının sayfasını alalım
    df_sorted['next_page'] = df_sorted.groupby(['date', 'ip'])['page'].shift(-1)

    # Şartlara göre filtre
    # '/' sonrası sayfalar
    slash_mask = df_sorted['page'] == '/'
    slash_next = df_sorted.loc[slash_mask, ['date', 'ip', 'next_page']].copy()
    slash_next = slash_next[son_iki_rakam_mi_vectorized(slash_next['next_page'])]

    # '/arama' ile başlayan sonrası sayfalar
    arama_mask = df_sorted['page'].str.startswith('/arama')
    arama_next = df_sorted.loc[arama_mask, ['date', 'ip', 'next_page']].copy()
    arama_next = arama_next[son_iki_rakam_mi_vectorized(arama_next['next_page'])]

    # Grupla topla stringle
    slash_grouped = slash_next.groupby(['date', 'ip'])['next_page'].apply(lambda x: ','.join(x)).reset_index().rename(columns={'next_page': 'slash_sonrasi_sayfalar'})
    arama_grouped = arama_next.groupby(['date', 'ip'])['next_page'].apply(lambda x: ','.join(x)).reset_index().rename(columns={'next_page': 'arama_sonrasi_sayfalar'})

    # İki tabloyu birleştir
    merged = pd.merge(slash_grouped, arama_grouped, on=['date', 'ip'], how='outer').fillna('')

    # Boş olan satırları çıkar
    filtered = merged[(merged['slash_sonrasi_sayfalar'] != '') | (merged['arama_sonrasi_sayfalar'] != '')]

    return filtered

def kisa_sayfa_adi(sayfa):
    if sayfa.count('/') > 1:
        return '/'.join(sayfa.split('/')[:2])
    return sayfa

def sayfa_frekans(df, kolon_adi):
    all_pages = df[kolon_adi].dropna().astype(str).str.split(',')
    flat_list = [p.strip() for sublist in all_pages for p in sublist if p.strip() not in ['/', '/arama']]
    short_pages = [kisa_sayfa_adi(p) for p in flat_list]
    s = pd.Series(short_pages).value_counts()
    return s

def gunluk_toplam_ziyaret(df):
    def say(s):
        if pd.isna(s) or s == "":
            return 0
        pages = [p for p in s.split(',') if p not in ['/', '/arama']]
        return len(pages)

    df["ana_sayfa_ziyaret"] = df["slash_sonrasi_sayfalar"].apply(lambda x: 0 if pd.isna(x) else say(x))
    df["arama_ziyaret"] = df["arama_sonrasi_sayfalar"].apply(lambda x: 0 if pd.isna(x) else say(x))

    toplam = df.groupby("date").agg({
        "ana_sayfa_ziyaret": "sum",
        "arama_ziyaret": "sum"
    }).reset_index()
    return toplam

# Dash app oluştur
app = Dash(__name__)

# Veriyi çek ve işle (sadece 1 kere)
raw_df = fetch_real_user_page_visits()
processed_df = process_page_visits_vectorized(raw_df)
toplam_ziyaret = gunluk_toplam_ziyaret(processed_df)

app.layout = html.Div([
    html.H2("Gün Bazlı Ana Sayfa ve Arama Sonrası Ziyaretler"),
    dcc.Graph(id='gunluk-ziyaret-grafik'),
    html.Button('Sayfayı Durdur', id='shutdown-btn', style={'margin': '20px'}),
    html.Div(id='detay-grafikler'),
    html.Div(id='shutdown-message', style={"color": "red", "fontWeight": "bold"})
])

@app.callback(
    Output('gunluk-ziyaret-grafik', 'figure'),
    Input('gunluk-ziyaret-grafik', 'clickData')
)
def goster_gunluk_grafik(clickData):
    fig = go.Figure()
    if toplam_ziyaret["ana_sayfa_ziyaret"].sum() > 0:
        fig.add_trace(go.Bar(
            x=toplam_ziyaret['date'],
            y=toplam_ziyaret['ana_sayfa_ziyaret'],
            name="Ana Sayfa Sonrası",
            text=toplam_ziyaret['ana_sayfa_ziyaret'],
            textposition='outside'
        ))
    if toplam_ziyaret["arama_ziyaret"].sum() > 0:
        fig.add_trace(go.Bar(
            x=toplam_ziyaret['date'],
            y=toplam_ziyaret['arama_ziyaret'],
            name="Arama Sonrası",
            text=toplam_ziyaret['arama_ziyaret'],
            textposition='outside'
        ))
    fig.update_layout(
        barmode='group',
        title="Gün Bazlı Ziyaretler",
        xaxis_title="Tarih",
        yaxis_title="Ziyaret Sayısı",
        yaxis=dict(tickformat='d')
    )
    return fig

@app.callback(
    Output('detay-grafikler', 'children'),
    Input('gunluk-ziyaret-grafik', 'clickData')
)
def goster_detaylar(clickData):
    if clickData is None:
        return html.Div("Lütfen bir gün seçin")

    secilen_gun = clickData['points'][0]['x'].strip()
    filtered_df = processed_df[processed_df['date'] == secilen_gun]

    if filtered_df.empty:
        return html.Div(f"Seçilen gün için veri yok: {secilen_gun}")

    ana_sayfa_df = filtered_df[filtered_df['slash_sonrasi_sayfalar'].str.strip() != '']
    arama_df = filtered_df[filtered_df['arama_sonrasi_sayfalar'].str.strip() != '']

    ana_sayfa_freq = sayfa_frekans(ana_sayfa_df, 'slash_sonrasi_sayfalar')
    arama_freq = sayfa_frekans(arama_df, 'arama_sonrasi_sayfalar')

    children = []

    if not ana_sayfa_freq.empty:
        top_ana = ana_sayfa_freq.head(15)
        ana_fig = go.Figure(go.Bar(
            x=top_ana.index,
            y=top_ana.values,
            text=top_ana.values,
            textposition='outside',
            hoverinfo='x+y'
        ))
        en_cok_ana = ana_sayfa_freq.idxmax()
        ana_fig.update_layout(
            title="Ana Sayfa Sonrası",
            xaxis_title="Sayfa",
            yaxis_title="Ziyaret Sayısı",
            yaxis=dict(tickformat='d')
        )
        children.append(html.H3("Ana Sayfa Sonrası"))
        children.append(html.P("En Çok Gidilen Sayfa: " + en_cok_ana))
        children.append(dcc.Graph(figure=ana_fig))

    if not arama_freq.empty:
        top_arama = arama_freq.head(15)
        arama_fig = go.Figure(go.Bar(
            x=top_arama.index,
            y=top_arama.values,
            text=top_arama.values,
            textposition='outside',
            hoverinfo='x+y'
        ))
        en_cok_arama = arama_freq.idxmax()
        arama_fig.update_layout(
            title="Arama Sonrası",
            xaxis_title="Sayfa",
            yaxis_title="Ziyaret Sayısı",
            yaxis=dict(tickformat='d')
        )
        children.append(html.H3("Arama Sonrası"))
        children.append(html.P("En Çok Gidilen Sayfa: " + en_cok_arama))
        children.append(dcc.Graph(figure=arama_fig))

    if not children:
        return html.Div("Seçilen gün için gösterilecek veri yok")

    return html.Div(children)

@app.callback(
    Output('shutdown-message', 'children'),
    Input('shutdown-btn', 'n_clicks'),
    prevent_initial_call=True
)
def shutdown_app(n_clicks):
    if n_clicks:
        threading.Thread(target=lambda: requests.post("http://127.0.0.1:9020/shutdown")).start()
        return "Uygulama durduruluyor..."

@app.server.route('/shutdown', methods=['POST'])
def shutdown():
    import os
    import signal
    os.kill(os.getpid(), signal.SIGINT)
    return 'Server kapatılıyor...'

# Otomatik açma
if __name__ == "__main__":
    import webbrowser
    import threading

    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:9020")).start()
    app.run(debug=False, port=9020)
