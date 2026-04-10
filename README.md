<div align="center">
  <img src="https://img.icons8.com/color/120/000000/ticket.png" alt="Eventix Logo" width="100"/>
  <h1>🎫 Eventix - Yeni Nesil Akıllı Biletleme ve Etkinlik Yönetim Platformu</h1>
  <p>Minimalist tasarım, kusursuz kullanıcı deneyimi ve gelişmiş yönetim araçlarıyla donatılmış, güvenilir dijital biletleme ekosistemi.</p>

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

## 🌟 Vizyon ve Genel Bakış

**Eventix**, sıradan bir bilet alma sitesinin ötesinde; hem katılımcılar hem de organizatörler için tasarlanmış **premium bir deneyim merkezidir**. Canlı konserlerden workshop etkinliklerine kadar geniş bir yelpazede hizmet verir. Modern, göz yormayan karanlık teması (Dark Mode) ve akıcı arayüzü sayesinde kullanıcıyı yormaz, doğrudan hedefe ulaştırır.

Temel hedefimiz; etkinlik düzenleyicilerine (Organizatör ve Admin) finansal kontrolü tam şeffaflıkla sunarken, kullanıcılara "tek tıkla" koltuğunu seçip biletine anında e-posta üzerinden **dijital E-Bilet (PDF benzeri mail barkodu)** formatında kavuşabileceği modern bir altyapı sağlamaktır.

---

## 🔥 Öne Çıkan Özellikler ve Kullanıcı Deneyimi

### 1. Görsel ve Etkileşimli Etkinlik Detayları
Kullanıcılar bir etkinliğe tıkladığında; yüksek çözünürlüklü afişler, etkinliğin oturma planının **harita üzerindeki görselleştirilmiş krokisi** (Seating Layout) ve etkinliğin tam lokasyonunu gösteren entegre Google Harita görünümü ile karşılaşır. Etkinlikle ilgili tüm dinamik veriler (kalan bilet sayısı, kapasite, bilet fiyatı) anlık olarak güncellenir.

<div align="center">
  <img src="./images/event_detail.png" alt="Etkinlik Detay Sayfası" width="700"/>
</div>

### 2. Adım Adım Güvenli Bilet ve Koltuk Seçimi
Karmaşık bilet alım süreçlerini rafa kaldıran Eventix, kullanıcıyı adım adım yönlendiren güvenli bir rezervasyon/ödeme akışı sunar:
- **Kategori Seçimi:** VIP, BİSTRO veya GENEL gibi farklı alanlar, anlık boş koltuk kapasiteleriyle birlikte net olarak sunulur.
- **İnteraktif Koltuk Seçimi (Matris):** Seçilen kategoriye özel (A-E sıraları, 1-10 numaralı koltuklar gibi) etkileşimli bir grid yapısı üzerinden istenilen nokta tıklanarak anında rezerve edilebilir.

| Kategori ve Fiyat Seçimi | Dinamik Koltuk Seçimi |
| :---: | :---: |
| <img src="./images/category_select.png" width="400"/> | <img src="./images/seat_select.png" width="400"/> |

### 3. Anında Dijital Teslimat: Mail Üzerinden QR E-Bilet
Ödeme işlemi başarıyla tamamlandığı saniye, arka planda çalışan sistem bilet sahibine özel, şifrelenmiş benzersiz bir **QR Kod** üretir. 

Bu QR kod, satın alınan koltuk numarası, saat ve konum bilgileriyle birlikte şık ve resmi bir **E-Ticket (Dijital Bilet)** şablonu halinde kullanıcının direkt e-posta kutusuna gönderilir. Katılımcıların etkinlik girişlerinde hiçbir kağıda ihtiyaç duymadan sadece telefonlarındaki e-postayı ve QR kodu görevliye okutması yeterlidir.

<div align="center">
  <img src="./images/mail_ticket.png" alt="Mail ile Gelen Dijital QR Bilet" width="500"/>
</div>

### 4. Şeffaf, Kapsamlı Yönetim ve Finans Paneli (Admin)
Bir dijital platformun kalbi arka kapısındaki (backend) veri yönetimidir. Eventix, yetkilendirilmiş kullanıcılara muazzam bir finansal analiz paneli sunar:
- **Platform Gelir Dağılımı (Revenue):** Sistemin toplam elde ettiği brüt kazanç, platformun organizatörlerden otomatik olarak tahsil ettiği komisyon (Platform Commission - %10) ve organizatörün cebine geçecek net kazanç (Earnings Payouts) hatasız şekilde hesaplanır.
- **Detaylı Etkinlik ve Organizatör Dökümü:** Hangi organizatörün ne kadar bilet sattığı (kota/satış oranları), komisyon kesintileri sonrasındaki net hakedişleri ve aktif etkinliklerin anlık satış raporları tek bir ekrandan, dinamik algoritmalarla yönetilir.

<div align="center">
  <img src="./images/admin_dashboard.png" alt="Admin Finans ve Yönetim Paneli" width="700"/>
</div>

---

## 🛠️ Teknik Altyapı ve Güvenlik Vizyonu

- **Cloud Veritabanı Mimarisi (Turso / SQLite):** Yüksek sunucu maliyetleri yaratmayan, dağıtık ve çok hızlı **Turso Cloud** teknolojisiyle veri okuma/yazma süreleri minimize edilmiştir.
- **Güvenlik Çemberi:** Uygulama şifre hashleme, güvenli JWT tabanlı Authorization (yetkilendirme), kötü amaçlı istekleri engelleyen Rate-Limiting ve QR kod içeriklerini koruyan **HMAC SHA-256** veri şifrelemesi gibi sıkı siber güvenlik standartlarıyla korunmaktadır.
- **Otomatik Mail Sunucusu (SMTP):** Sorunsuz ve sıfır gecikmeli bilet/bildirim e-postaları gönderebilmek adına özel bir asenkron SMTP iletişim altyapısı kurulmuş, biletlerin spama düşmeden "Inbox"a ulaşması hedeflenmiştir.

---

<div align="center">
  <p><i>Katılımcılar için eşsiz bir deneyim, organizatörler için maksimum karlılık kontrolü.</i></p>
  <b>Eventix Projesi © 2026</b>
</div>
