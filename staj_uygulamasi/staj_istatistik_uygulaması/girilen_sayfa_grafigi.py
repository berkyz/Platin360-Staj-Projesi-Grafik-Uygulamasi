from sqlalchemy import create_engine, MetaData, Table, select, func
import multiprocessing
import psutil
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import seaborn as sns

cpu_count = multiprocessing.cpu_count()
mem_available = psutil.virtual_memory().available
target_memory = int(mem_available * 0.9)
estimated_row_size = 512
chunksize = max(1000, target_memory // estimated_row_size)

engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

def son_iki_rakam_mi(s):
    if not isinstance(s, str):
        return False
    s = s.strip("/")
    if len(s) < 2:
        return False
    return s[-2:].isdigit()

def read_chunks():
    with engine.connect() as conn:
        total_rows = conn.execute(select(func.count()).select_from(logs_table)).scalar()
        for offset in range(0, total_rows, chunksize):
            query = (
                select(
                    logs_table.c["date"],
                    logs_table.c["time"],
                    logs_table.c["c-ip"],
                    logs_table.c["cs-uri-stem"],
                    logs_table.c["sc-status"],
                    logs_table.c["is_bot"]
                )
                .limit(chunksize)
                .offset(offset)
            )
            result = conn.execute(query).mappings()
            yield from result

user_pages = defaultdict(list)
url_segments = []

for row in read_chunks():
    if row["is_bot"] != 0 or row["sc-status"] != 200:
        continue

    key = (row["date"], row["c-ip"])
    user_pages[key].append(row["cs-uri-stem"])

    url_segments.append(row["cs-uri-stem"])

rows = []
for (date, ip), pages in user_pages.items():
    slash_indexes = [i for i, p in enumerate(pages) if p == "/"]
    arama_indexes = [i for i, p in enumerate(pages) if p.startswith("/arama")]

    slash_sonrasi = []
    for idx in slash_indexes:
        if idx + 1 < len(pages):
            sonraki = pages[idx + 1]
            if son_iki_rakam_mi(sonraki):
                slash_sonrasi.append(sonraki)

    arama_sonrasi = []
    for idx in arama_indexes:
        if idx + 1 < len(pages):
            sonraki = pages[idx + 1]
            if son_iki_rakam_mi(sonraki):
                arama_sonrasi.append(sonraki)

    if slash_sonrasi or arama_sonrasi:
        rows.append({
            "date": date,
            "ip": ip,
            "slash_sonrasi_sayfalar": ",".join(slash_sonrasi),
            "arama_sonrasi_sayfalar": ",".join(arama_sonrasi)
        })

def get_first_segment(url):
    if url == "/":
        return "Ana Sayfa"
    if not url.startswith("/"):
        url = "/" + url
    parts = url.split("/")
    return parts[1] if len(parts) > 1 and parts[1] != "" else "Ana Sayfa"

def process_segment_chunk(url_list):
    return [get_first_segment(url) for url in url_list]

num_workers = max(1, cpu_count - 1)
chunk_len = len(url_segments) // num_workers + 1
chunks = [url_segments[i*chunk_len:(i+1)*chunk_len] for i in range(num_workers)]

with multiprocessing.Pool(num_workers) as pool:
    segment_lists = pool.map(process_segment_chunk, chunks)

all_segments = []
for seg_list in segment_lists:
    all_segments.extend(seg_list)

segment_counts = Counter(all_segments)
top_30 = segment_counts.most_common(35)[5:]

top_segments = [seg for seg, _ in top_30]
top_counts = [cnt for _, cnt in top_30]

height = max(6, 0.4 * len(top_segments))
plt.figure(figsize=(12, height))
sns.barplot(x=top_counts, y=top_segments, palette="mako")
plt.title("Başarılı İsteklerin URL Segment Dağılımı (Top 30)")
plt.xlabel("İstek Sayısı")
plt.ylabel("URL Segmenti")
plt.tight_layout()
plt.show()
