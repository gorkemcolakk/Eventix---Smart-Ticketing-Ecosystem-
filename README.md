<div align="center">
  <img src="https://img.icons8.com/color/120/000000/ticket.png" alt="Eventix Logo" width="100"/>
  <h1>🎫 Eventix - Modern Etkinlik Biletleme Platformu</h1>
  <p>Python, Flask ve Turso kullanılarak geliştirilmiş, uçtan uca kapsamlı bir etkinlik ve bilet yönetim sistemi.</p>

  <div>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
    <img src="https://img.shields.io/badge/Turso-000000?style=for-the-badge&logo=turso&logoColor=white" alt="Turso"/>
    <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
    <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"/>
  </div>
</div>

<br />

## 🌟 Genel Bakış

**Eventix**, bir etkinliğin tüm yaşam döngüsünü yönetmek için tasarlanmış hepsi bir arada bir e-ticaret ve etkinlik yönetimi platformudur. Organizatörler tarafından etkinlik oluşturulmasından, müşterilerin bilet satın almasına ve QR kod doğrulamasına kadar Eventix, premium bir kullanıcı deneyimi sunar. Sistem; Müşteri, Organizatör ve Admin rolleriyle ayrılmış güçlü bir yetkilendirme (RBAC) yapısına sahiptir.

---

## 🔥 Temel Özellikler

### 👤 Rol Bazlı Paneller
*   **Müşteri Paneli**: Etkinlikleri inceleme, favorilere bilet ekleme, interaktif koltuk seçimi ve QR kodlu dijital biletlere erişim.
*   **Organizatör Paneli**: Etkinlik oluşturma ve yönetme, satış takibi, dinamik oturma planı tanımlama ve finansal özetler.
*   **Yönetici (Admin) Alanı**: Etkinlik onaylama/reddetme, kullanıcı yönetimi, genel analitik ve raporlama.

### 🎟️ Akıllı Biletleme ve Oturma Düzeni
*   **İnteraktif Koltuk Seçimi**: Oturma planı olan mekanlarda kullanıcılar istedikleri sıra ve koltuğu seçebilirler.
*   **QR Kod Üretimi**: Satın alınan her bilet için benzersiz bir QR kod oluşturulur ve anında e-posta ile gönderilir.
*   **Promosyon Kodları**: Sabit tutar veya yüzde bazlı indirim kuponu desteği.

### 🚀 Teknik Detaylar
*   **Turso Cloud DB**: Dağıtık SQLite üzerinden yüksek performanslı ve bulut tabanlı veritabanı yönetimi (lokal `database.db` yedeği ile).
*   **Güvenli Kimlik Doğrulama**: Parola hashing ve güvenli session yönetimi.
*   **SMTP E-posta Entegrasyonu**: Otomatik bilet gönderimi ve bildirimler.

---

## 📸 Ekran Görüntüleri

> [!TIP]
> **Nasıl Resim Eklerim?** Aşağıdaki kutucukların görünmesi için uygulamanızdan ekran görüntüleri alıp, bu dosyadaki `src` kısımlarına dosya yollarını (örneğin: `frontend/static/images/screenshot1.png`) yazmanız yeterlidir.

| Anasayfa & Keşfet | Gerçek Zamanlı Koltuk Seçimi |
| :---: | :---: |
| <img src="https://placehold.co/600x400/1e1e1e/white?text=Anasayfa+Ekran+Görüntüsü" width="400"/> | <img src="https://placehold.co/600x400/1e1e1e/white?text=Koltuk+Seçimi+Ekran+Görüntüsü" width="400"/> |

| Müşteri Paneli | Organizatör / Admin Paneli |
| :---: | :---: |
| <img src="https://placehold.co/600x400/1e1e1e/white?text=Müşteri+Dashboard" width="400"/> | <img src="https://placehold.co/600x400/1e1e1e/white?text=Yönetim+Paneli" width="400"/> |

---

## 🛠️ Kurulum ve Başlatma

1. **Projeyi Klonlayın**
   ```bash
   git clone https://github.com/gorkemcolakk/e-commerce.git
   cd e-commerce
   ```

2. **Sanal Ortam Oluşturun (Önerilen)**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows için
   ```

3. **Bağımlılıkları Yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

4. **Çevre Değişkenlerini Ayarlayın**
   Kök dizinde `.env` dosyası oluşturun ve bilgilerinizi girin (SMTP, Turso, URL):
   ```ini
   FRONTEND_URL=http://localhost:5000
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=mail@adresiniz.com
   SMTP_PASSWORD=uygulama_sifreniz
   ```

5. **Veritabanını Hazırlayın ve Başlatın**
   ```bash
   python seed.py
   python app.py
   ```
   Uygulama `http://localhost:5000` adresinde çalışmaya başlayacaktır.

---

## 🏗️ Proje Mimarisi

```
📂 E-commerce
├── 📄 app.py              # Uygulama Giriş Noktası
├── 📄 database.py         # DB Bağlantısı (Turso & SQLite)
├── 📄 payment.py          # Ödeme Simülasyonu
├── 📄 seed.py             # Örnek Veri Üretici (Mock Data)
├── 📄 utils.py            # Yardımcı Araçlar (QR, Mail, Doğrulama)
├── 📂 routes/             # Rotalar (Auth, Etkinlik, Organizatör vb.)
└── 📂 frontend/           # Şablonlar, CSS, JS ve Assetler
```

---

<div align="center">
  <p>Bitirme projesi kapsamında hazırlanan Etkinlik Yönetim Sistemi.</p>
</div>
