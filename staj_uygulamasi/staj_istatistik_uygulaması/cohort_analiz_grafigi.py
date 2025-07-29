import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, MetaData, Table, select, func
import psutil
import multiprocessing

# === Sistem Kaynakları ===
cpu_count = multiprocessing.cpu_count()
mem_available = psutil.virtual_memory().available
target_memory = int(mem_available * 0.9)  # %90 RAM kullanımı
estimated_row_size = 512  # Ortalama satır boyutu (bytes)
chunksize = max(1000, target_memory // estimated_row_size)

# === Veritabanı bağlantısı ===
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# === Chunk okuma fonksiyonu ===
def read_chunks():
    with engine.connect() as conn:
        total_rows = conn.execute(select(func.count()).select_from(logs_table)).scalar()
        for offset in range(0, total_rows, chunksize):
            query = (
                select(
                    logs_table.c.date,
                    logs_table.c.time,
                    logs_table.c['c-ip'],
                    logs_table.c['cs(User-Agent)'],
                    logs_table.c['is_bot']
                )
                .limit(chunksize)
                .offset(offset)
            )
            yield pd.read_sql(query, con=conn)

# === Tüm chunk'ları oku ve birleştir ===
df = pd.concat(read_chunks(), ignore_index=True)

# === Bot filtreleme ===
df = df[df['is_bot'] == 0]

# === datetime oluştur (sıralama yok) ===
df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
df = df.dropna(subset=["datetime"]).reset_index(drop=True)

# === Günlük benzersiz IP'ler ===
df = (
    df.assign(date=df["datetime"].dt.date)
      .groupby("date")["c-ip"]
      .agg(lambda x: list(set(x)))
      .reset_index()
      .rename(columns={"c-ip": "c-ips"})
)
daily_ips = df.copy()

# === İlk kez gelen IP'ler ===
seen_ips = set()
first_time_ips = []
for ips in daily_ips['c-ips']:
    ips_set = set(ips)
    new_ips = ips_set - seen_ips
    first_time_ips.append(list(new_ips))
    seen_ips.update(ips_set)
daily_ips['first_time_ips'] = first_time_ips

# === Cohort günleri ===
cohort_map = []
for index, row in daily_ips.iterrows():
    date = row['date']
    for ip in row['first_time_ips']:
        cohort_map.append((ip, date))
cohort_df = pd.DataFrame(cohort_map, columns=['c-ip', 'cohort_date'])

# === Ziyaret günleri ===
visit_map = []
for index, row in daily_ips.iterrows():
    date = row['date']
    for ip in row['c-ips']:
        visit_map.append((ip, date))
visit_df = pd.DataFrame(visit_map, columns=['c-ip', 'visit_date'])

# === Merge ve gün farkı ===
merged = visit_df.merge(cohort_df, on='c-ip')
merged['days_since_cohort'] = (
    pd.to_datetime(merged['visit_date']) - pd.to_datetime(merged['cohort_date'])
).dt.days

# === Retention tablosu ===
retention = (
    merged.groupby(['cohort_date', 'days_since_cohort'])['c-ip']
    .nunique()
    .reset_index()
    .pivot(index='cohort_date', columns='days_since_cohort', values='c-ip')
)
cohort_sizes = retention[0]
retention_pct = retention.divide(cohort_sizes, axis=0)

# === Heatmap çizimi ===
plt.figure(figsize=(14, 8))
sns.heatmap(retention_pct, annot=True, fmt=".0%", cmap="YlGnBu")
plt.title("Cohort Retention Heatmap (Günlük)")
plt.xlabel("Cohort'tan Kaç Gün Sonra")
plt.ylabel("Cohort Günü")
plt.tight_layout()
plt.show()
