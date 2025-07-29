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

### ⚠️ Önemli Not

- Uygulama başlamadan önce, `duzenli_data.db` dosyasının mevcut olması gerekir.
- Eğer `duzenli_data.db` yoksa veya hatalıysa, uygulama düzgün çalışmayacaktır.
- Uygulama, `data.db` dosyası yüklendikten sonra veriyi kendisi düzenler ve `duzenli_data.db` dosyası oluşturur ancak **veri kaynağı olarak mutlaka bir `data.db` (staj_uygulamasi/data.db) dosyası ile aynı formatta bir dosya yüklenmesi gereklidir**.

