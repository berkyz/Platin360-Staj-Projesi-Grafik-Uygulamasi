import pandas as pd
from sqlalchemy import create_engine, MetaData, Table, select
import seaborn as sns
import matplotlib.pyplot as plt

# 🔌 Veritabanı bağlantısı
engine = create_engine("sqlite:///duzenli_data.db")
metadata = MetaData()
metadata.reflect(bind=engine)

logs_table = Table("logs", metadata, autoload_with=engine)

# 🔄 Bellek dostu veri okuma
chunksize = 100_000
mobile_lst, pc_lst = [], []

with engine.connect() as conn:
    stmt = select(
        logs_table.c["os"],
        logs_table.c["is_mobile"],
        logs_table.c["is_pc"]
    )

    for chunk in pd.read_sql(stmt, con=conn, chunksize=chunksize):
        # Geçerli işletim sistemi kayıtlarını kontrol et
        mobile_chunk = chunk[chunk["is_mobile"] == 1]["os"].dropna().tolist()
        pc_chunk = chunk[(chunk["is_mobile"] != 1) & (chunk["is_pc"] == 1)]["os"].dropna().tolist()
        mobile_lst.extend(mobile_chunk)
        pc_lst.extend(pc_chunk)

# 📊 OS kullanım sayısı
mobile_os = pd.Series(mobile_lst).value_counts().reset_index()
mobile_os.columns = ["OS", "Users"]

pc_os = pd.Series(pc_lst).value_counts().reset_index()
pc_os.columns = ["OS", "Users"]

# 📱🖥️ Toplam kullanım dağılımı
data_usage = pd.DataFrame({
    "Device": ["Mobile", "PC"],
    "Usage": [len(mobile_lst), len(pc_lst)]
})

# --- 📈 Grafikler ---
fig, axs = plt.subplots(1, 3, figsize=(18, 6))

# 🥧 Pasta grafiği
axs[0].pie(data_usage["Usage"], labels=data_usage["Device"], autopct='%1.1f%%',
           colors=["#66b3ff", "#99ff99"])
axs[0].set_title("Mobil vs PC Kullanımı")

# 🖥️ PC işletim sistemleri
sns.barplot(x="OS", y="Users", data=pc_os, ax=axs[1], palette="Blues_d")
axs[1].set_title("PC İşletim Sistemleri")
axs[1].set_ylabel("Kullanıcı Sayısı")
axs[1].tick_params(axis='x', rotation=45, labelsize=9)

# 📱 Mobil işletim sistemleri
sns.barplot(x="OS", y="Users", data=mobile_os, ax=axs[2], palette="Greens_d")
axs[2].set_title("Mobil İşletim Sistemleri")
axs[2].set_ylabel("Kullanıcı Sayısı")
axs[2].tick_params(axis='x', rotation=45, labelsize=9)

plt.tight_layout()
plt.show()
