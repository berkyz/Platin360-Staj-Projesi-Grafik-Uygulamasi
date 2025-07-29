import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import threading
import requests
import webbrowser
import os
import signal

# Veritabanı bağlantısı
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# Veriyi çek (sadece hata kodu 400+ olanlar)
with engine.connect() as conn:
    stmt = (
        select(logs_table.c["sc-status"], logs_table.c["cs-uri-stem"])
        .where(logs_table.c["sc-status"] >= 400)
    )
    df = pd.read_sql(stmt, con=conn)

df["sc-status"] = df["sc-status"].astype(int)
df["cs-uri-stem"] = df["cs-uri-stem"].fillna("Bilinmiyor").replace("/", "Ana Sayfa")

result = (
    df.groupby(["cs-uri-stem", "sc-status"])
    .size()
    .reset_index(name="count")
)
result["sc-status"] = result["sc-status"].astype(int)

error_summary = (
    result.groupby("sc-status")["count"]
    .sum()
    .reset_index()
)
error_summary["sc-status"] = error_summary["sc-status"].astype(int)

status_to_pages = {
    status: group.sort_values(by="count", ascending=False).head(10)
    for status, group in result.groupby("sc-status")
}

app = Dash(__name__)

fig_main = px.bar(
    error_summary,
    x=error_summary["sc-status"].astype(str),
    y="count",
    text="count",
    labels={"sc-status": "Hata Kodu", "count": "Toplam Hata Sayısı"},
    title="Yalnızca Gerçekleşen HTTP Hataları"
)

app.layout = html.Div([
    html.H2("Gerçekleşen HTTP Hata Kodları"),
    dcc.Graph(id='main-bar', figure=fig_main),
    html.Button('Sayfayı Durdur', id='shutdown-btn', style={'margin': '20px'}),
    html.Div("Bir hata koduna tıklayarak detayları görebilirsiniz.", id='detail-container'),
    html.Div(id='shutdown-message', style={"color": "red", "fontWeight": "bold"})
])

@app.callback(
    Output('detail-container', 'children'),
    Input('main-bar', 'clickData')
)
def show_top_pages(clickData):
    if not clickData or "points" not in clickData:
        return html.Div("Bir hata koduna tıklayarak sayfa detaylarını görebilirsiniz.")

    code_str = clickData["points"][0]["x"]
    try:
        code = int(code_str)
    except ValueError:
        return html.Div(f"Geçersiz hata kodu: {code_str}")

    top_pages = status_to_pages.get(code)
    if top_pages is None or top_pages.empty:
        return html.Div(f"{code} hata koduna ait veri bulunamadı.")

    fig = px.bar(
        top_pages,
        x="cs-uri-stem",
        y="count",
        text="count",
        title=f"{code} Hatalı En Çok Sayfa",
        labels={"cs-uri-stem": "Sayfa", "count": "Hata Sayısı"}
    )
    fig.update_traces(textposition='auto')
    return dcc.Graph(figure=fig)

@app.callback(
    Output('shutdown-message', 'children'),
    Input('shutdown-btn', 'n_clicks'),
    prevent_initial_call=True
)
def shutdown_app(n_clicks):
    if n_clicks:
        # Asenkron istek ile /shutdown endpoint'ini çağır
        threading.Thread(target=lambda: requests.post("http://127.0.0.1:9030/shutdown")).start()
        return "Uygulama durduruluyor..."

@app.server.route('/shutdown', methods=['POST'])
def shutdown():
    # Ctrl+C sinyali gönderip kapatma
    os.kill(os.getpid(), signal.SIGINT)
    return 'Server kapatılıyor...'

if __name__ == "__main__":
    # Otomatik olarak tarayıcıda aç
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:9030")).start()
    app.run(debug=False, port=9030)
