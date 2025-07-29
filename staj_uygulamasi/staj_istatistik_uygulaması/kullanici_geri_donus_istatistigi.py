import pandas as pd
from sqlalchemy import create_engine, select, Table, MetaData
import seaborn as sns
import matplotlib.pyplot as plt
import mplcursors
from datetime import datetime

# --- DB bağlantısı ---
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# --- Belleğe aşırı yüklenmemek için chunk okuma ---
stmt = select(
    logs_table.c.date,
    logs_table.c.time,
    logs_table.c['c-ip'],
    logs_table.c['cs(User-Agent)']
)

chunksize = 50000
rows = []

with engine.connect() as conn:
    for chunk in pd.read_sql(stmt, conn, chunksize=chunksize):
        # Bot filtreleme (vektörel hızlı)
        chunk = chunk[~chunk["cs(User-Agent)"].str.lower().str.contains("bot", na=False)]

        # Tarih birleştirme
        datetimes = pd.to_datetime(chunk["date"] + " " + chunk["time"], errors="coerce")
        chunk = chunk.assign(datetime=datetimes)
        chunk = chunk.dropna(subset=["datetime"])

        rows.append(chunk[["datetime", "c-ip"]])

# --- Tüm chunklar birleşsin ---
df = pd.concat(rows, ignore_index=True)
df["date"] = df["datetime"].dt.date

# --- Günlük benzersiz IP listesi ---
daily_ips = df.groupby("date")["c-ip"].agg(lambda x: set(x)).reset_index(name="ips")

# --- Geri dönen kullanıcı hesaplama ---
user_logins = set()
return_counts = []
total_counts = []

for i, today_ips in enumerate(daily_ips["ips"]):
    if i == 0:
        new_logins = today_ips
        returned = set()
    else:
        new_logins = today_ips - user_logins
        returned = today_ips & user_logins
    
    return_counts.append(len(returned))
    total_counts.append(len(today_ips))
    user_logins.update(new_logins)

# İlk güne özel: geri dönen kullanıcı sıfır
return_counts[0] = 0

# --- Sonuç dataframe ---
daily_ips["returned_count"] = return_counts
daily_ips["total_count"] = total_counts
daily_ips["returned_percent"] = daily_ips["returned_count"] / daily_ips["total_count"] * 100

# --- Grafik çizimi ---
plt.figure(figsize=(12, 6))
ax = sns.lineplot(data=daily_ips, x="date", y="returned_percent", marker="o")
plt.title("Günlük Geri Dönen Kullanıcıların Yüzdesi")
plt.xlabel("Tarih")
plt.ylabel("Geri Dönen Kullanıcı (%)")
plt.ylim(0, 100)
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()

cursor = mplcursors.cursor(ax.lines, hover=True)

@cursor.connect("add")
def on_add(sel):
    x, y = sel.target
    sel.annotation.set_text(f"{y:.2f}%")

plt.show()
