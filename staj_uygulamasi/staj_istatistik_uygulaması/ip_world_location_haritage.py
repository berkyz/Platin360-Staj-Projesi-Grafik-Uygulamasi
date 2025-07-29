import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import mplcursors
from sqlalchemy import create_engine, MetaData, Table, select, func

engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

with engine.connect() as conn:
    stmt = (
        select(
            logs_table.c["c-ip"].label("ip"),
            func.count().label("count"),
            logs_table.c["lat"],
            logs_table.c["lon"],
            logs_table.c["city"],
            logs_table.c["country"]
        )
        .where(logs_table.c["is_bot"] == 0)
        .group_by(logs_table.c["c-ip"], logs_table.c["lat"], logs_table.c["lon"], logs_table.c["city"], logs_table.c["country"])
    )
    df = pd.read_sql(stmt, conn)

df = df.dropna(subset=["lat", "lon"])
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
df = df.dropna(subset=["lat", "lon"])

def get_color_and_size(count):
    if count < 10:
        return ("blue", 20)
    elif count <= 20:
        ratio = (count - 10) / 10
        r = 255
        g = int(165 + (255 - 165) * ratio)
        b = 0
        return ((r / 255, g / 255, b / 255), 30)
    else:
        ratio = min((count - 20) / 30, 1)
        r = 255
        g = int(165 * (1 - ratio))
        b = 0
        return ((r / 255, g / 255, b / 255), 40)

colors = []
sizes = []
for c in df["count"]:
    color, size = get_color_and_size(c)
    colors.append(color)
    sizes.append(size)

df["color"] = colors
df["size"] = sizes

world = gpd.read_file("data/countries.geojson")

fig, ax = plt.subplots(figsize=(20, 12))
world.plot(ax=ax, color="lightgray", edgecolor="black", linewidth=0.5)

sc = ax.scatter(
    df["lon"],
    df["lat"],
    c=df["color"].tolist(),
    s=df["size"],
    alpha=0.85,
    edgecolors="black",
    linewidth=0.3,
    marker="o",
    zorder=5,
)

cursor = mplcursors.cursor(sc, hover=True)

@cursor.connect("add")
def on_add(sel):
    i = sel.index
    ip = df.iloc[i]["ip"]
    city = df.iloc[i].get("city", "")
    country = df.iloc[i].get("country", "")
    sel.annotation.set(text=f"IP : {ip}\nBölge : {city} / {country}")
    sel.annotation.get_bbox_patch().set(alpha=0.9)

legend_elements = [
    Line2D([0], [0], marker="o", color="w", label="0-9 istek", markerfacecolor="blue", markersize=10, markeredgecolor="black"),
    Line2D([0], [0], marker="o", color="w", label="10-20 istek", markerfacecolor="orange", markersize=10, markeredgecolor="black"),
    Line2D([0], [0], marker="o", color="w", label="21+ istek", markerfacecolor="red", markersize=10, markeredgecolor="black"),
]
ax.legend(handles=legend_elements, loc="lower left", title="İstek Sayısı Renkleri")

plt.title("IP Adreslerinin İstek Sayısına Göre Konum Dağılımı", fontsize=16)
plt.xlabel("Boylam (Longitude)")
plt.ylabel("Enlem (Latitude)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()
