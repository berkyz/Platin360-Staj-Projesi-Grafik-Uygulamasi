import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select, func
import matplotlib.pyplot as plt
from http import HTTPStatus
import psutil

engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

mem_available = psutil.virtual_memory().available
estimated_row_size = 100  # Status kodu ve diğer alanlar için küçük tahmin
chunksize = max(10000, mem_available // estimated_row_size)

def read_chunks():
    with engine.connect() as conn:
        total_rows = conn.execute(select(func.count()).select_from(logs_table)).scalar()
        for offset in range(0, total_rows, chunksize):
            query = select(logs_table.c["sc-status"]).limit(chunksize).offset(offset)
            result = conn.execute(query).scalars().all()
            yield result

status_counts = {}

for chunk in read_chunks():
    for status in chunk:
        status_str = str(status)
        status_counts[status_str] = status_counts.get(status_str, 0) + 1

df = pd.DataFrame(list(status_counts.items()), columns=["Status Code", "Count"])
df["Status Code"] = df["Status Code"].astype(int)
df = df.sort_values(by="Status Code").reset_index(drop=True)

status_names = []
for code in df["Status Code"]:
    try:
        status_names.append(HTTPStatus(code).phrase)
    except ValueError:
        status_names.append("Unknown")

plt.figure(figsize=(14, 8))
bars = plt.bar(df["Status Code"].astype(str), df["Count"], color="teal")

plt.title("HTTP Status Kodları ve Sayıları (Status Code'a Göre Sıralı)", fontsize=16)
plt.xlabel("Status Code", fontsize=14, labelpad=50)
plt.ylabel("Adet", fontsize=14)

y_offset = max(df["Count"]) * 0.01
for bar, count in zip(bars, df["Count"]):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + y_offset,
             f"{count:,}", ha="center", va="bottom", fontsize=11, fontweight="bold")

plt.xticks(ticks=range(len(df)), labels=df["Status Code"].astype(str), fontsize=15, rotation=45, ha="right")

ax = plt.gca()
for bar, name in zip(bars, status_names):
    ax.text(bar.get_x() + bar.get_width()/2, -max(df["Count"]) * 0.05,
            name, ha="center", va="top", fontsize=10, rotation=45, color="red")

plt.ylim(0, max(df["Count"]) * 1.15)

plt.tight_layout()
plt.show()
