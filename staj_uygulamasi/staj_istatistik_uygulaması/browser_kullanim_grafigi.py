import pandas as pd
import matplotlib.pyplot as plt
import psutil
import multiprocessing
from collections import Counter
from sqlalchemy import create_engine, MetaData, Table, select, func
from concurrent.futures import ProcessPoolExecutor

# === Donanım ayarları ===
cpu_count = multiprocessing.cpu_count()
num_workers = max(1, int(cpu_count * 0.9))  # %90 CPU
mem_available = psutil.virtual_memory().available
target_memory = int(mem_available * 0.9)  # %90 RAM
estimated_row_size = 512  # Tarayıcı bilgisi genellikle hafif
chunksize = max(1000, target_memory // estimated_row_size)

# === Veritabanı bağlantısı ===
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# === Filtreli toplam satır sayısını bul (is_bot = 0) ===
with engine.connect() as conn:
    total_rows = conn.execute(
        select(func.count()).select_from(logs_table).where(logs_table.c["is_bot"] == 0)
    ).scalar()

# === Chunk işleme fonksiyonu ===
def process_chunk(offset):
    with engine.connect() as conn:
        query = (
            select(logs_table.c["browser"])
            .where(logs_table.c["is_bot"] == 0)
            .limit(chunksize)
            .offset(offset)
        )
        chunk = pd.read_sql(query, conn)
        chunk = chunk.dropna()
        return Counter(chunk["browser"])

# === Ana işlem ===
if __name__ == "__main__":
    offsets = list(range(0, total_rows, chunksize))
    browser_counts = Counter()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for partial_count in executor.map(process_chunk, offsets):
            browser_counts.update(partial_count)

    # === Sonuçları işle ===
    browser_df = pd.DataFrame(browser_counts.items(), columns=["browser", "count"])
    browser_df = browser_df.sort_values("count", ascending=False)
    top10 = browser_df.head(10).copy()
    total = top10["count"].sum()
    percentages = 100 * top10["count"] / total

    # === Grafik ===
    colors = ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'brown', 'pink', 'gray', 'cyan']
    plt.figure(figsize=(10, 6))
    bars = plt.bar(top10["browser"], percentages, color=colors)

    for i, pct in enumerate(percentages):
        plt.text(i, pct + 1, f"{pct:.1f}%", ha='center', va='bottom', fontsize=10)

    plt.ylim(0, 100)
    plt.title("Tarayıcı Kullanım Dağılımı (Gerçek Kullanıcılar - is_bot=0)")
    plt.xlabel("Tarayıcı")
    plt.ylabel("Yüzde (%)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
