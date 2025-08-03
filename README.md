## 📂 Veri Yapısı ve `data.db` Gereksinimi

Bu uygulama, çalışabilmek için `data.db` adında bir veritabanı dosyasını yüklemelidir.

### 🔄 Veri İşleme Süreci

1. **Veri Girişi:**  
   - Uygulama yalnızca `data.db` formatındaki veri dosyasını kabul eder.
   - Başka formatlardaki veriler (ör. `.csv`, `.json`) doğrudan kullanılamaz.

2. **Veri Dönüştürme:**  
   - Uygulama çalıştığında, `data.db` içindeki ham veriyi işler.
   - Veriler uygulama içinde **temizlenir**, **düzenlenir** ve **kullanıma hazır hale getirilir**.

3. **Kullanım:**  
   - İşlenmiş (düzenli) veri, sadece uygulama çalıştıktan sonra oluşur ve sistem içinde kullanılır.
   - Uygulamayı `kivy_app.py` dosyasından çalıştırabilirsiniz.

### ⚠️ Önemli Not
- Uygulama başlamadan önce, `duzenli_data.db` dosyasının mevcut olması gerekir.
- Eğer `duzenli_data.db` yoksa veya hatalıysa, uygulama düzgün çalışmayacaktır.
- Uygulama, `data.db` dosyası yüklendikten sonra veriyi kendisi düzenler ve `duzenli_data.db` dosyası oluşturur ancak **veri kaynağı olarak mutlaka bir `data.db` (staj_uygulamasi/data.db) dosyası ile aynı formatta bir dosya yüklenmesi gereklidir**.
### Uygulama Tanıtımı
Uygulamada `data_siralama.py` ve `kivy_app.py` dosyaları hariç tüm py dosyaları bir grafik veya tablo çalıştırıyor. 
`kivy_app.py` dosyası bu grafikleri çalıştırabileceğimiz bir arayüz sunuyor.
`ip_konumlari_agent.csv` dosyası projenin içinde bulunan `data.db` dosyasına özel olarak hazırlanmıştır. Farklı bir data kullanımı için farklı csv dosyasına ihtiyaç duyulmaktadır. 
<img width="1366" height="768" alt="Screenshot_20250803_130126" src="https://github.com/user-attachments/assets/de9fda21-1fb2-4cca-9f02-c76946a2643a" />
Uygulama arayüzü bu şekilde görünmekte ve her tuş bir dosyayı çalıştırmaktadır.
