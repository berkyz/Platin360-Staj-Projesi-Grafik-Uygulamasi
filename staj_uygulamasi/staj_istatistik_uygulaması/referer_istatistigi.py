import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
from urllib.parse import urlparse
import seaborn as sns
import matplotlib.pyplot as plt
import concurrent.futures

# --- Yardımcı Fonksiyonlar ---
def son_iki_rakam_mi(s):
    s = s.strip("/")
    return len(s) >= 2 and s[-2:].isdigit()

def referer_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return None

# --- Veritabanı Bağlantısı ---
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)
logs_table = Table("logs", metadata, autoload_with=engine)

# --- Sorgu: Gerekli kolonları seç ---
stmt = select(
    logs_table.c["cs-uri-stem"],
    logs_table.c["cs(Referer)"],
    logs_table.c["cs(User-Agent)"],
    logs_table.c["sc-status"]
)

# --- Chunked okuma + filtreleme ---
chunksize = 50000
referers = []

with engine.connect() as conn:
    for chunk in pd.read_sql(stmt, conn, chunksize=chunksize):
        # Filtreleri uygula
        filtered = chunk[
            (chunk["sc-status"] == 200) &
            (~chunk["cs(User-Agent)"].str.contains("bot", case=False, na=False)) &
            (chunk["cs-uri-stem"].apply(lambda x: son_iki_rakam_mi(str(x)))) &
            (chunk["cs(Referer)"].notna()) &
            (~chunk["cs(Referer)"].str.contains("-", na=False))
        ]

        referers.extend(filtered["cs(Referer)"].tolist())

# --- Referer domainlerini paralel işle ---
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    domains = list(executor.map(referer_domain, referers))

# --- Domain sayımlarını al ---
domain_counts = pd.Series(domains).dropna().value_counts().head(15)

# --- Grafik ---
plt.figure(figsize=(10, 6))
ax = sns.barplot(
    x=domain_counts.values,
    y=domain_counts.index,
    palette="magma"
)

for i, v in enumerate(domain_counts.values):
    ax.text(v + max(domain_counts.values) * 0.01, i, str(v), va='center')

plt.xlabel("İstek Sayısı")
plt.ylabel("Referer Domain (Alan Adı)")
plt.title("En Çok Gelen 15 Referer (Alan Adına Göre Gruplanmış)")
plt.tight_layout()
plt.show()
