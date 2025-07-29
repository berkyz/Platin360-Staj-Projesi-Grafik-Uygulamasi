import pandas as pd
import re
import psutil
from collections import Counter
from sqlalchemy import create_engine, MetaData, Table, select, func
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import matplotlib.pyplot as plt

# === Donanım bilgileri ===
cpu_count = multiprocessing.cpu_count()
num_workers = max(1, int(cpu_count * 0.9))  # %90 CPU

# RAM bilgisi
mem_available = psutil.virtual_memory().available  # bytes
target_memory = int(mem_available * 0.9)  # %90 RAM

# Ortalama satır başı boyut tahmini (1 KB)
estimated_row_size = 1024  # bytes
chunksize = max(1000, target_memory // estimated_row_size)

# === Veritabanı bağlantısı ===
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)
column_name = "cs(User-Agent)"

# === Chunk işleme fonksiyonu ===
def process_chunk(offset):
    with engine.connect() as conn:
        query = select(logs_table.c[column_name]).limit(chunksize).offset(offset)
        chunk = pd.read_sql(query, conn)
        chunk.columns = ['user_agent']
        chunk['user_agent'] = chunk['user_agent'].astype(str).str.lower()
        df_bot = chunk[chunk['user_agent'].str.contains(r'bot')]
        all_text = " ".join(df_bot['user_agent'].tolist())
        bot_words = re.findall(r'\b[\w\-]*bot[\w\-]*\b', all_text)
        return Counter(bot_words)

# === Ana işlem ===
if __name__ == "__main__":
    with engine.connect() as conn:
        total_rows = conn.execute(select(func.count()).select_from(logs_table)).scalar()

    offsets = list(range(0, total_rows, chunksize))
    bot_counts = Counter()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for partial_count in executor.map(process_chunk, offsets):
            bot_counts.update(partial_count)

    # === Verileri toparla ve temizle ===
    bot_df = pd.DataFrame(bot_counts.items(), columns=["bot_name", "count"])
    bot_df["bot_name"] = bot_df["bot_name"].astype(str).str.strip()
    bot_df["bot_name"] = bot_df["bot_name"].str.replace(r'\s+', ' ', regex=True)
    bot_df["bot_name"] = bot_df["bot_name"].str.replace(r'[^a-zA-Z0-9_\- ]', '', regex=True)
    bot_df = bot_df.groupby("bot_name", as_index=False)["count"].sum()

    # En çok geçen ilk 10 bot + Diğerleri
    top10 = bot_df.sort_values("count", ascending=False).head(10).copy()
    other_count = bot_df["count"].sum() - top10["count"].sum()
    other_row = pd.DataFrame([{"bot_name": "OtherBots", "count": other_count}])
    final_df = pd.concat([top10, other_row], ignore_index=True)

    # Yüzdelik
    total = final_df["count"].sum()
    percentages = 100 * final_df["count"] / total

    # Grafik
    colors = plt.cm.tab20.colors[:len(final_df)]
    plt.figure(figsize=(12, 6))
    bars = plt.bar(final_df["bot_name"], percentages, color=colors)
    for i, pct in enumerate(percentages):
        plt.text(i, pct + 1, f"{pct:.1f}%", ha='center', va='bottom', fontsize=9)

    plt.ylim(0, 100)
    plt.title("Bot Türleri Dağılımı (İlk 10 + OtherBots)", fontsize=14)
    plt.xlabel("Bot Türü")
    plt.ylabel("Yüzde (%)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
