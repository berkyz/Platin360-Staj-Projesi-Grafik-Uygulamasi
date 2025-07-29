## 📂 Veri Yapısı ve Kullanımı

Bu Kivy uygulaması `data.db` adlı bir veritabanı dosyası ile çalışmaktadır.

### 🔄 Veri İşleme Süreci

1. **Veri Yükleme:**  
   Uygulama çalıştırıldığında, belirtilen klasörde bulunan ham veriler otomatik olarak yüklenir.

2. **Veri Dönüştürme:**  
   Ham veriler uygulama tarafından **düzenli bir formata dönüştürülür**. Bu işlem sırasında:
   - Veriler temizlenir,
   - Gerekli alanlara ayrılır,
   - Uyumlu hale getirilir.

3. **Veritabanı Oluşturma:**  
   Düzenlenmiş veriler `data.db` adlı bir SQLite veritabanı dosyasına kaydedilir.  
   Bu dosya uygulama tarafından veri kaynağı olarak kullanılır.

### 📁 data.db Nerededir?

- Varsayılan olarak proje klasörünün kök dizininde bulunur.
- Veritabanı silinirse veya eksikse, uygulama çalışmayabilir.

### 💡 Not:

Veritabanı dosyası `duzenli_data.db` oluşturulmadan önce uygulama düzgün çalışmaz. İlk kez çalıştırmadan önce verilerin hazır olduğundan emin olun.

