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

- Uygulama başlamadan önce, `data.db` dosyasının mevcut olması gerekir.
- Eğer `data.db` yoksa veya hatalıysa, uygulama düzgün çalışmayacaktır.
- Uygulama, veriyi kendisi düzenler ancak **veri kaynağı olarak mutlaka bir `data.db` dosyası gereklidir**.

