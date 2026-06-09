<div align="center">

  <img src="./images/poster.png" alt="Eventix Poster" width="100%" style="border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6); margin-bottom: 20px;"/>
  <br/>


<!-- LOGO SVG - Bilet tasarımı -->
<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">
  <defs>
    <linearGradient id="rg1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/>
      <stop offset="100%" style="stop-color:#ec4899"/>
    </linearGradient>
  </defs>
  <rect x="8" y="20" width="64" height="40" rx="7" fill="url(#rg1)" opacity="0.95"/>
  <circle cx="8" cy="40" r="7" fill="#0f0f1a"/>
  <circle cx="72" cy="40" r="7" fill="#0f0f1a"/>
  <line x1="20" y1="40" x2="60" y2="40" stroke="rgba(255,255,255,0.35)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <circle cx="40" cy="40" r="7" fill="rgba(255,255,255,0.18)"/>
  <path d="M37 40l2 2 4-4" stroke="#ffffff" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>

# Eventix — Biletleme & Etkinlik Yönetim Platformu

### *Katılımcılar için eşsiz bir deneyim, organizatörler için maksimum kontrol.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Local-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Turso](https://img.shields.io/badge/Turso-Cloud_DB-4FF8D2?style=for-the-badge&logo=turso&logoColor=black)](https://turso.tech/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br/>

</div>

---

## 📌 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Canlı Demo & Ekran Görüntüleri](#-canlı-demo--ekran-görüntüleri)
- [Temel Özellikler](#-temel-özellikler)
- [İletişim](#-iletişim)

---

## 🎯 Proje Hakkında

**Eventix**, konserlere, festivallere, tiyatro gösterilerine, workshoplara ve daha fazlasına bilet satın almayı ve etkinlik yönetmeyi kolaylaştıran **tam yığın (full-stack) bir biletleme platformudur.** Flask ile geliştirilmiş RESTful bir backend, saf HTML/CSS/JavaScript ile oluşturulmuş modern bir frontend ve Turso (dağıtık SQLite) cloud veritabanını bir araya getirir.

Platform; **3 farklı kullanıcı rolü** (Müşteri, Organizatör, Admin) ile çalışır ve her rol için özel bir kontrol paneli sunar. Bilet satın alındığı anda HMAC-SHA256 ile imzalı benzersiz QR kodlar üretilir ve kullanıcıya HTML tasarımlı e-bilet mail olarak gönderilir.

**Neden Eventix?**
- 🌍 **Çok dilli:** Türkçe, İngilizce ve Almanca tam destek
- 🔐 **Güvenli:** JWT kimlik doğrulama, rate limiting, HMAC imzalı QR kodlar
- ⚡ **Hızlı:** Turso Cloud ile küresel dağıtık veritabanı, sunucu taraflı önbellekleme
- 🎨 **Modern:** Dark mode öncelikli, glassmorphism ve gradient tasarım
- 📧 **Akıllı:** Doğum günü e-postaları, iade bildirimleri, kapıda QR doğrulama

---

## 🖼️ Canlı Demo & Ekran Görüntüleri


> 🚀 **[Canlı Projeyi Görüntüle: Eventix Ticketing Platform](https://eventix-smart-ticketing-ecosystem.onrender.com/index.html)**

---

### 📱 Mobil Uyumluluk (Responsive)

<div align="center">
  <img src="./images/mobile_home.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
  <img src="./images/mobile_event.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
  <img src="./images/mobile_seat.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
</div>
<br/>
<div align="center">
  <img src="./images/mobile_menu.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
  <img src="./images/mobile_organizer.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
  <img src="./images/mobile_promo.jpg" width="230" style="border-radius: 12px; margin: 0 5px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);"/>
</div>

---

### Ana Sayfa

<div align="center">
  <img src="./images/homepage_hero.png" alt="Eventix Ana Sayfa Hero" width="900" style="border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);"/>
  <br/><sub>Hero alanı, arama/filtrele ve navigasyon</sub>
</div>

<br/>

<div align="center">
  <img src="./images/homepage_events.png" alt="Eventix Ana Sayfa Etkinlikler" width="900" style="border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);"/>
  <br/><sub>Öne çıkan popüler konser, tiyatro ve atölye kartları</sub>
</div>

<br/>

### Giriş & Kayıt

| Giriş Sayfası | Kayıt Sayfası |
| :---: | :---: |
| <img src="./images/login.png" width="430" style="border-radius: 12px;"/> | <img src="./images/register.png" width="430" style="border-radius: 12px;"/> |

---

### Etkinlik Detay & Oturma Planı

<div align="center">
  <img src="./images/event_detail_top.png" alt="Etkinlik Detay Sayfası" width="860" style="border-radius: 14px;"/>
  <br/><sub>Etkinlik detay sayfası — yüksek çözünürlüklü afiş, açıklama ve kurallar</sub>
</div>

<br/>

<div align="center">
  <img src="./images/event_detail_map.png" alt="Oturma Planı ve Mekan Haritası" width="860" style="border-radius: 14px;"/>
  <br/><sub>Stadyum/Mekan oturma planı önizlemesi ve entegre Google Maps görünümü</sub>
</div>

---

### Bilet Seçimi (Kategori & Koltuk Seçimi)

| Kategori / Bilet Türü Seçimi | Numaralı Koltuk Seçimi (Matris) |
| :---: | :---: |
| <img src="./images/checkout_category.png" width="430" style="border-radius: 10px;"/> | <img src="./images/checkout_seat.png" width="430" style="border-radius: 10px;"/> |

---

### Dijital E-Bilet (Mail)

<div align="center">
  <img src="./images/ticket_pdf.png" alt="E-Bilet Çıktısı" width="560" style="border-radius: 14px; border: 1px solid #2d2d4e;"/>
  <br/><sub>Ödeme tamamlandıktan sonra oluşturulan QR kodlu HTML/PDF E-Bilet formatı</sub>
</div>

---

### Organizatör Paneli

<div align="center">
  <img src="./images/organizer_dashboard.png" alt="Organizatör Paneli Gelir Raporu" width="860" style="border-radius: 14px;"/>
  <br/><sub>Organizatörlere özel detaylı gelir grafiği ve istatistik paneli</sub>
</div>

---

### Admin Paneli

<div align="center">
  <img src="./images/admin_revenue.png" alt="Admin Paneli Gelir Raporu" width="860" style="border-radius: 14px;"/>
  <br/><sub>Admin Paneli — Platform geneli gelir özeti ve organizatör dağılımları</sub>
</div>

<br/>

<div align="center">
  <img src="./images/admin_sales.png" alt="Admin Satış Geçmişi" width="860" style="border-radius: 14px;"/>
  <br/><sub>Gelişmiş filtreleme ile detaylı bilet satış geçmişi tablosu</sub>
</div>

<br/>

<div align="center">
  <img src="./images/admin_events.png" alt="Admin Tüm Etkinlikler" width="860" style="border-radius: 14px;"/>
  <br/><sub>Platformdaki tüm etkinliklerin takibi, durum yönetimi ve aksiyonlar</sub>
</div>

---

## ✨ Temel Özellikler

### 🎫 Biletleme Sistemi
- **Ayakta Etkinlikler:** Miktar seçimi, kategori ve fiyat ayrımı (VIP, Bistro, Genel vb.)
- **Numaralı Koltuklu Etkinlikler:** İnteraktif koltuk matrisi (satır/sütun bazlı); her koltuk bağımsız fiyatlandırılabilir
- **Optimistik Kilit Mekanizması:** Koltuk seçildiği anda 5 dakika geçici rezervasyon; ödeme tamamlanmazsa otomatik serbest bırakılır
- **Promosyon Kodları:** Etkinlik bazında yüzdelik veya sabit indirim kodları; kullanım limiti ve tarih aralığı tanımlanabilir
- **Doğum Günü Kuponu:** `BDAY26` — %15 indirim, arka planda çalışan iş parçacığı ile otomatik gönderim
- **İade Sistemi:** Platform komisyonu hesaplanarak bilet iptali ve kısmi iade; iade geçmişi kayıt altında
- **İstek Listesi (Wishlist):** Kullanıcılar etkinlikleri favorilerine ekleyip takip edebilir

### 📧 E-posta Bildirimleri
| Olay | İçerik |
|---|---|
| Bilet Satın Alma | Kişiselleştirilmiş HTML mail + her bilet için ayrı QR kod |
| Doğum Günü | Tam sayfa HTML tebrik + `BDAY26` kupon kodu |
| Şifre Sıfırlama | 15 dakika geçerli JWT bağlantısı |
| Etkinlik İptali | Organizatör / admin tarafından iptal edildiğinde otomatik bildirim |
| İletişim Formu | Admin inbox'a gönderici bilgileriyle birlikte HTML mail |

### 📊 Analitik & Finans
- **%10 Platform Komisyonu** — her satıştan otomatik kesilir
- Organizatör başına net kazanç, etkinlik başına satış oranı
- Admin için platform geneli toplam gelir, en çok satan etkinlikler
- Refund breakdown: müşteriye iade, organizatöre tazminat, admin kesintisi

### 🗺️ Etkinlik Yönetimi
- **Etkinlik Oluşturma:** Başlık, kategori, tarih, konum, fiyat, kapasite, afiş yükleme, açıklama, lineup
- **Numaralı Koltuk Planı:** Zone bazlı blok ve satır/sütun konfigürasyonu
- **Tekrar Eden Etkinlikler:** Günlük / haftalık / aylık periyot ile parent-child seans yapısı
- **Onay Akışı:** Organizatör oluşturur → Admin onaylar/reddeder → Satışa açılır
- **Anlık Yönetim:** Yayındaki etkinliği durdurma, satışları kapatma, yayından kaldırma

### 🎪 Kullanıcı Deneyimi
- **Dark Mode Öncelikli** tasarım, purple-to-pink gradient renk paleti
- Tam **responsive** (mobil, tablet, masaüstü)
- Gerçek zamanlı bildirim sistemi (okunmamış sayaç, inbox görünümü)
- Adım adım checkout progress bar (Bilet → Kişisel Bilgi → Ödeme → Onay)
- Kapıda **QR Kamera Doğrulama** — organizatör kameradan okutup bileti geçerli/geçersiz yapabilir

---

## 📧 İletişim

**Eren Görkem Çolak**

[![GitHub](https://img.shields.io/badge/GitHub-gorkemcolakk-181717?style=flat-square&logo=github)](https://github.com/gorkemcolakk)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Eren_Görkem_Çolak-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/eren-g%C3%B6rkem-%C3%A7olak-06104b35a/)

---

<div align="center">

**Eventix Ticketing Platform** — © 2026

*Katılımcılar için eşsiz bir deneyim, organizatörler için maksimum kontrol.*

⭐ Bu projeyi beğendiysen yıldız vermeyi unutma!

</div>
