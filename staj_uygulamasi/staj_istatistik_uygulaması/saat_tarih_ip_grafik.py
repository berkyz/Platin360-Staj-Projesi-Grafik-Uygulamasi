import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import threading
import requests
import webbrowser
import os
import signal

class Time():
    def __init__(self, time):
        self.time = time
        self.ip = []

class Date():
    def __init__(self, date):
        self.date = date
        self.time_dict = {}

    def get_time_obj(self, time_key):
        if time_key not in self.time_dict:
            self.time_dict[time_key] = Time(time_key)
        return self.time_dict[time_key]

    def get_all_times(self):
        return [self.time_dict[k] for k in sorted(self.time_dict.keys())]

# DB bağlantısı ve veri çekme, ön işlem burada yapılıyor sadece bir kez
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

stmt = select(
    logs_table.c["date"], 
    logs_table.c["time"], 
    logs_table.c["c-ip"], 
    logs_table.c["cs(User-Agent)"]
)
with engine.connect() as conn:
    df = pd.read_sql(stmt, con=conn)

df = df[~df["cs(User-Agent)"].str.contains("bot", case=False, na=False)]

df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"])

interval_hours = 1
dates_dict = {}

for row in df.itertuples(index=False):
    date_str = row.date
    dt = row.datetime
    ip = row._3

    if date_str not in dates_dict:
        dates_dict[date_str] = Date(date_str)

    date_obj = dates_dict[date_str]
    hour = dt.hour
    start_hour = (hour // interval_hours) * interval_hours
    time_key = f"{start_hour:02d}:00:00"

    time_obj = date_obj.get_time_obj(time_key)
    time_obj.ip.append(ip)

rows = []
for date_obj in dates_dict.values():
    for time_obj in date_obj.get_all_times():
        total_ips = len(time_obj.ip)
        unique_ips = len(set(time_obj.ip))
        rows.append({
            "date": date_obj.date,
            "hour": time_obj.time,
            "ip_count": total_ips,
            "user_count": unique_ips
        })

df_graph = pd.DataFrame(rows)
df_graph["hour"] = pd.to_datetime(df_graph["hour"], format="%H:%M:%S").dt.strftime("%H:%M")

df_total = df_graph.groupby("date").agg({
    "ip_count": "sum",
    "user_count": "sum"
}).reset_index()

df_total_melted = df_total.melt(id_vars="date", var_name="type", value_name="count")

# Dash app oluştur
app = Dash(__name__)

app.layout = html.Div([
    html.H2("Günlük IP ve Kullanıcı Trafiği (Botlar Hariç)"),

    dcc.Graph(
        id="bar-chart",
        figure=px.bar(df_total_melted, x="date", y="count", color="type", barmode="group",
                      title="Tarihe Göre Toplam IP ve Kullanıcı Sayısı (Botlar Hariç)")
    ),

    html.H3(id="line-title", children="Bir tarihe tıklayın..."),
    dcc.Graph(id="line-chart"),

    html.Button('Sayfayı Durdur', id='shutdown-btn', style={'margin': '20px'}),
    html.Div(id='shutdown-message', style={"color": "red", "fontWeight": "bold"})
])

@app.callback(
    Output("line-chart", "figure"),
    Output("line-title", "children"),
    Input("bar-chart", "clickData")
)
def update_line_chart(clickData):
    if not clickData:
        return {}, "Bir tarihe tıklayın..."

    clicked_date = clickData["points"][0]["x"]
    df_selected = df_graph[df_graph["date"] == clicked_date]

    fig = px.line(df_selected, x="hour", y=["ip_count", "user_count"],
                  labels={"value": "Sayı", "variable": "Tür", "hour": "Saat"},
                  title=f"{clicked_date} Tarihli Saatlik IP ve Kullanıcı Trafiği (Botlar Hariç)")
    fig.update_traces(mode="lines+markers")

    return fig, f"{clicked_date} tarihinin saatlik grafiği (Botlar Hariç)"

@app.callback(
    Output('shutdown-message', 'children'),
    Input('shutdown-btn', 'n_clicks'),
    prevent_initial_call=True
)
def shutdown_app(n_clicks):
    if n_clicks:
        threading.Thread(target=lambda: requests.post("http://127.0.0.1:9040/shutdown")).start()
        return "Uygulama durduruluyor..."

@app.server.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return "Server kapatılıyor..."

if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:9040")).start()
    app.run(debug=False, port=9040)
