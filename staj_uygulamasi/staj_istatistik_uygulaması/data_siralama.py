import os
import pandas as pd
from sqlalchemy import create_engine, MetaData
from user_agents import parse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

def detect_browser(ua_string):
    ua_lower = ua_string.lower()
    if "brave" in ua_lower:
        return "Brave"
    elif "edg/" in ua_lower or "edge" in ua_lower:
        return "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        return "Opera"
    elif "firefox" in ua_lower:
        return "Firefox"
    elif "chrome" in ua_lower:
        return "Chrome"
    elif "safari" in ua_lower:
        return "Safari"
    elif "msie" in ua_lower or "trident" in ua_lower:
        return "Internet Explorer"
    else:
        return "Other Browser"

def parse_user_agent(ua_string):
    ua_clean = ua_string.replace("+", " ")
    parsed = parse(ua_clean)
    return {
        "browser": detect_browser(ua_clean),
        "browser_version": parsed.browser.version_string,
        "os": parsed.os.family,
        "os_version": parsed.os.version_string,
        "device": parsed.device.family if parsed.device.family != "Other" else "Unknown",
        "is_mobile": parsed.is_mobile,
        "is_pc": parsed.is_pc,
        "is_bot": parsed.is_bot,
    }

def parallel_parse_user_agents(ua_list, max_workers=None):
    if max_workers is None:
        max_workers = multiprocessing.cpu_count() - 2
    print(f"🧠 {max_workers} thread kullanılacak...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(parse_user_agent, ua) for ua in ua_list]
        results = []
        for i, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if i % 1000 == 0 or i == len(ua_list):
                percent = (i / len(ua_list)) * 100
                print(f"%{percent:.2f} işlendi.")
    return results

def process_db(input_db_path):
    print(f"\n İşleme alınıyor: {input_db_path}")
    try:
        engine = create_engine(f"sqlite:///{input_db_path}")
        metadata = MetaData()
        metadata.reflect(bind=engine)

        output_path = "duzenli_data.db"
        if os.path.exists(output_path):
            os.remove(output_path)
            print("Eski duzenli_data.db silindi.")

        out_engine = create_engine(f"sqlite:///{output_path}")
        first_chunk = True

        chunk_size = 100_000
        for chunk in pd.read_sql_table("logs", con=engine, chunksize=chunk_size):
            chunk["datetime"] = pd.to_datetime(chunk["date"] + " " + chunk["time"])
            chunk = chunk.sort_values("datetime").reset_index(drop=True)

            ua_list = chunk["cs(User-Agent)"].fillna("").tolist()
            print(f"🔍 {len(chunk)} satır UA çözümlemesi başlıyor...")
            parsed_data = parallel_parse_user_agents(ua_list)

            ua_df = pd.DataFrame(parsed_data)
            chunk.reset_index(drop=True, inplace=True)
            ua_df.reset_index(drop=True, inplace=True)
            chunk = pd.concat([chunk, ua_df], axis=1)

            # Konum sütunlarını ekle
            chunk["lat"] = None
            chunk["lon"] = None
            chunk["city"] = None
            chunk["country"] = None

            ip_file = "ip_konumlari_agent.csv"
            if os.path.exists(ip_file):
                ip_df = pd.read_csv(ip_file)
                if "c-ip" in chunk.columns and "ip" in ip_df.columns:
                    non_bot_mask = chunk["is_bot"] == 0
                    df_chunk = chunk[non_bot_mask].copy()
                    ip_filtered = ip_df[ip_df["ip"].isin(df_chunk["c-ip"])]
                    merged = pd.merge(
                        df_chunk,
                        ip_filtered,
                        left_on="c-ip",
                        right_on="ip",
                        how="left",
                        suffixes=("", "_ip")
                    )
                    for col in ["lat", "lon", "city", "country"]:
                        if col + "_ip" in merged.columns:
                            chunk.loc[merged.index, col] = merged[col + "_ip"].values
                else:
                    print("'c-ip' veya 'ip' sütunu eksik.")
            else:
                print("ip_konumlari_agent.csv bulunamadı.")

            chunk = chunk.drop(columns=["datetime"])

            chunk.to_sql("logs", con=out_engine, index=False, if_exists="append", chunksize=10_000)
            print(f"Chunk yazıldı ({len(chunk)} satır)")

        # Bağlantı kapat
        out_engine.dispose()
        engine.dispose()
        print(f"Yeni dosya tamamlandı: {output_path}")

    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    all_db_files = [f for f in os.listdir(".") if f.endswith(".db") and f != "duzenli_data.db"]

    if all_db_files:
        latest_db = max(all_db_files, key=os.path.getctime)
        process_db(latest_db)

        # Eski db dosyalarını sil
        for f in all_db_files:
            try:
                os.remove(f)
                print(f"Silindi: {f}")
            except Exception as e:
                print(f"Silinemedi: {f}, {e}")
    else:
        print("İşlenecek .db dosyası bulunamadı.")
