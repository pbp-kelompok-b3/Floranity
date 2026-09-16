# Floranity

Floranity dirancang bagi para penggemar tanaman hias yang ingin mempraktikkan perawatan tanaman yang penuh perhatian dan berkelanjutan. Pada intinya, Floranity bertujuan untuk mengurangi hilangnya tanaman, menghemat air, serta menumbuhkan hubungan yang lebih mendalam dan menenangkan antara manusia dan ruang hijau yang mereka ciptakan.

## Anggota Kelompok - B03
* Aksara Putra Fachruddin (2506597284)
* Rama Sanjaya (2506604421)
* Syabil Wafi Ahdi (2506657371)
* Fatih Naufal Habibilah (2506586394)

## Latar Belakang Masalah
Setiap jenis tanaman memiliki rutinitas perawatan masing-masing. Memastikan tanaman mendapatkan akses ke perawatan terbaik menjadi salah satu faktor utama dalam tumbuh kembang tanaman. Namun, sebagian dari mereka memerlukan metode dan rutinitas yang lebih kompleks dibandingkan yang lainnya. Dalam upaya memberikan penanganan terbaik, sering kali dilakukan kesalahan yang terkait dengan inefisiensi seperti pemberian pupuk yang tidak tepat, siklus penyiraman yang salah, dan kendala lainnya.

## Solusi yang Diberikan
Floranity hadir sebagai platform perawatan tanaman hias pintar dan wadah komunitas bagi para pecinta tanaman. Floranity menyediakan berbagai fitur utama, antara lain:
* **Penjadwalan Perawatan secara Dinamis:** Menyesuaikan pengingat penyiraman dan pemupukan secara otomatis berdasarkan data cuaca mikro lokal untuk mencegah *overwatering* maupun kekeringan.
* **Komunitas Berbagi Tanaman:** Menyediakan ruang bagi para penggiat tanaman untuk saling berbagi informasi, pengalaman, serta panduan dalam merawat tanaman.

## API yang Digunakan
* **OpenWeather API** - [https://openweathermap.org/api](https://openweathermap.org/api)  
  Digunakan untuk mengambil data cuaca lokal (suhu, kelembapan, curah hujan) berdasarkan lokasi pengguna. Data ini menjadi dasar bagi sistem untuk menyesuaikan rekomendasi jadwal penyiraman secara dinamis, misalnya menunda notifikasi siram saat curah hujan tinggi, atau meningkatkan frekuensi siram saat cuaca panas dan kering.

* **Perenual API** - [https://perenual.com/docs/api](https://perenual.com/docs/api)  
  Digunakan sebagai basis data utama katalog tanaman hias. API ini menyediakan informasi spesifik spesies, seperti nama ilmiah, karakteristik pertumbuhan, tingkat kebutuhan air (*frequent, moderate, minimum*), serta kebutuhan sinar matahari yang digunakan oleh Floranity untuk memberikan panduan perawatan dasar setiap tanaman.

* **Google OAuth 2.0 & Google People API** - [https://developers.google.com/identity](https://developers.google.com/identity)  
  Digunakan untuk mekanisme autentikasi akun pengguna serta mengambil data profil awal (nama tampilan dan foto profil) secara otomatis saat pertama kali melakukan pendaftaran.

## Target Pengguna
Floranity menyasar penggemar tanaman hias mulai dari pemula yang membutuhkan panduan perawatan dasar, *hobbyist* berpengalaman yang ingin mendokumentasikan koleksinya dan berdiskusi teknik lanjutan, hingga pengguna yang peduli terhadap isu biodiversitas urban di lingkungan tempat tinggalnya.

## Daftar Modul

### 1. Koleksi dan Katalog Tanaman (PiC: Rama)
Menyediakan fungsi **CRUD** (*Create, Read, Update, Delete*) untuk tanaman yang dimiliki atau dirawat pengguna. Fitur ini mencakup penambahan tanaman ke koleksi pribadi lengkap dengan jurnal pertumbuhan berupa foto dan catatan berkala, pengeditan info, serta penghapusan tanaman dari koleksi. Koleksi ini terfilter berdasarkan sesi login sehingga hanya dapat diakses oleh pemiliknya. API yang digunakan adalah **Perenual API** (*endpoint species list & species details*) untuk mengambil data referensi spesies seperti nama, kebutuhan cahaya, tingkat kesulitan, dan kebutuhan air.

### 2. Jadwal dan Log Perawatan (PiC: Syabil)
Menyediakan fungsi **CRUD** untuk catatan aktivitas perawatan (seperti menyiram, memupuk, dan memangkas) per tanaman, dengan jadwal rekomendasi yang disesuaikan secara otomatis berdasarkan kondisi cuaca terkini. API yang digunakan adalah **OpenWeather API** untuk mengambil data suhu, kelembapan, dan curah hujan berdasarkan lokasi pengguna.

### 3. Forum dan Observasi Komunitas (PiC: Aksa)
Menyediakan fungsi **CRUD** untuk *post* diskusi atau *showcase* beserta komentarnya, mencakup tips perawatan, teknik *wiring* dan *pruning* bonsai, serta hasil rawatan. API yang digunakan adalah **iNaturalist API** untuk mengambil data observasi biodiversitas dari lokasi sekitar pengguna, sehingga forum dapat menampilkan spesies teramati di area yang sama untuk memperkuat tema biodiversitas urban.

### 4. Autentikasi dan Profil Pengguna via Google OAuth (PiC: Fatih)
Menyediakan fungsi **CRUD** untuk entitas Profil Pengguna yang terhubung *one-to-one* dengan akun Django. Pengguna dapat login dan mendaftar menggunakan Google OAuth. Saat pertama kali login, sistem akan membuat profil baru (*Create*) secara otomatis dengan nama tampilan dan foto profil yang diambil dari akun Google pengguna lewat **Google People API**. Pengguna dapat melihat profil miliknya serta profil publik anggota lain (*Read*), mengedit bio, foto profil, atau preferensi tampilan (*Update*), serta menghapus atau menonaktifkan akunnya (*Delete*).

## Komponen-Komponen Website

* **Dashboard Pengguna:** Ringkasan koleksi tanaman, pengingat perawatan terdekat, dan notifikasi berbasis cuaca terkini.
* **Halaman Detail Tanaman:** Profil lengkap satu tanaman, mencakup spesies, riwayat perawatan, galeri jurnal pertumbuhan kronologis, dan rekomendasi perawatan aktif.
* **Kalender Perawatan:** Tampilan kalender interaktif jadwal siram dan pupuk untuk seluruh koleksi tanaman pengguna.
* **Forum Komunitas:** Ruang diskusi berbentuk *thread* dengan kategori (perawatan, *showcase*, tanya jawab), lengkap dengan fitur komentar dan *like*.
* **Katalog Panduan Spesies:** Basis data spesies tanaman hias dan bonsai yang dapat dicari dan difilter berdasarkan kebutuhan cahaya, air, dan tingkat kesulitan yang bersumber dari Perenual API.

## Tautan Desain Figma
[Link Figma](https://www.figma.com/design/qbUWPRG2hfBVHtiduK0h2W/Floranity---UI-UX?node-id=0-1&t=jYRySARAl85jCrX0-1)
