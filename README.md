# Floranity

Floranity dirancang bagi para penggemar tanaman hias yang ingin mempraktikkan perawatan tanaman yang penuh perhatian dan berkelanjutan. Pada intinya, Floranity bertujuan untuk mengurangi hilangnya tanaman, menghemat air, serta menumbuhkan hubungan yang lebih mendalam dan menenangkan antara manusia dan ruang hijau yang mereka ciptakan.

## Tautan Deployment PWS
[Link PWS](https://pws.cs.ui.ac.id/rama.sanjaya/floranity)

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

Untuk mengaktifkan sinkronisasi penuh pada jadwal penyiraman, atur `PERENUAL_API_KEY` dan `OPENWEATHER_API_KEY` di environment atau file `.env`. Jika OpenWeather belum dikonfigurasi, jadwal memakai Open-Meteo sebagai sumber prakiraan cuaca tanpa kunci API. Data kebutuhan air yang sudah tersimpan di koleksi tetap digunakan saat Perenual tidak tersedia.

## Target Pengguna
Floranity menyasar penggemar tanaman hias mulai dari pemula yang membutuhkan panduan perawatan dasar, *hobbyist* berpengalaman yang ingin mendokumentasikan koleksinya dan berdiskusi teknik lanjutan, hingga pengguna yang peduli terhadap isu biodiversitas urban di lingkungan tempat tinggalnya.

## Daftar Modul

### 1. Koleksi dan Katalog Tanaman (PiC: Rama)
Menyediakan fungsi **CRUD** (*Create, Read, Update, Delete*) untuk tanaman yang dimiliki atau dirawat pengguna. Fitur ini mencakup penambahan tanaman ke koleksi pribadi lengkap dengan jurnal pertumbuhan berupa foto dan catatan berkala, pengeditan info, serta penghapusan tanaman dari koleksi. Koleksi ini terfilter berdasarkan sesi login sehingga hanya dapat diakses oleh pemiliknya. API yang digunakan adalah **Perenual API** (*endpoint species list & species details*) untuk mengambil data referensi spesies seperti nama, kebutuhan cahaya, tingkat kesulitan, dan kebutuhan air.

### 2. Jadwal dan Log Perawatan (PiC: Syabil)
Menyediakan jadwal penyiraman tujuh hari untuk tanaman dalam koleksi pengguna. Rekomendasi memakai kebutuhan air spesies dari **Perenual API** (atau data panduan yang tersimpan), riwayat penyiraman, dan prakiraan hujan serta suhu dari **OpenWeather API**. Pengguna dapat memasukkan kota atau mengizinkan geolokasi browser untuk mengambil prakiraan yang lebih akurat. Filter tanaman, status, pencarian, dan rentang tanggal membantu menemukan pengingat tertentu. Beberapa pengingat dapat diselesaikan, diarsipkan, atau dipulihkan sekaligus; penyiraman yang ditandai selesai otomatis dicatat ke jurnal perawatan.

### 3. Forum dan Observasi Komunitas (PiC: Aksa)
Menyediakan fungsi **CRUD** untuk *post* diskusi atau *showcase* beserta komentarnya, mencakup tips perawatan, teknik *wiring* dan *pruning* bonsai, serta hasil rawatan. API yang digunakan adalah **iNaturalist API** untuk mengambil data observasi biodiversitas dari lokasi sekitar pengguna, sehingga forum dapat menampilkan spesies teramati di area yang sama untuk memperkuat tema biodiversitas urban.

### 4. Autentikasi dan Profil Pengguna (PiC: Fatih)
Menyediakan fungsi CRUD untuk entitas Profil Pengguna yang terhubung one-to-one dengan akun Django. Pengguna dapat mendaftar (sign up) dan masuk (login) menggunakan sistem Django Authentication bawaan (username/email dan password). Saat pendaftaran akun berhasil, sistem secara otomatis membuat profil pengguna baru (_Create_) yang terhubung dengan akun Django tersebut. Pengguna dapat melihat profil miliknya serta profil publik anggota lain (_Read_), mengedit informasi pribadi seperti bio, foto profil, atau preferensi tampilan (Update), serta menghapus atau menonaktifkan akunnya (_Delete_).

## Komponen-Komponen Website

* **Dashboard Pengguna:** Ringkasan koleksi tanaman, pengingat perawatan terdekat, dan notifikasi berbasis cuaca terkini.
* **Halaman Detail Tanaman:** Profil lengkap satu tanaman, mencakup spesies, riwayat perawatan, galeri jurnal pertumbuhan kronologis, dan rekomendasi perawatan aktif.
* **Kalender Perawatan:** Tampilan kalender interaktif jadwal siram dan pupuk untuk seluruh koleksi tanaman pengguna.
* **Forum Komunitas:** Ruang diskusi berbentuk *thread* dengan kategori (perawatan, *showcase*, tanya jawab), lengkap dengan fitur komentar dan *like*.
* **Katalog Panduan Spesies:** Basis data spesies tanaman hias dan bonsai yang dapat dicari dan difilter berdasarkan kebutuhan cahaya, air, dan tingkat kesulitan yang bersumber dari Perenual API.

## Tautan Desain Figma
[Link Figma](https://www.figma.com/design/qbUWPRG2hfBVHtiduK0h2W/Floranity---UI-UX?node-id=0-1&t=jYRySARAl85jCrX0-1)



## Panduan Instalasi dan Setup Lokal

Ikuti langkah-langkah berikut untuk menjalankan Floranity di lingkungan lokal:

1. **Clone Repositori:**
   ```bash
   git clone https://github.com/pbp-kelompok-b3/floranity.git
   cd floranity
   ```

2. **Buat dan Aktifkan Virtual Environment:**
   * Di Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * Di Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Konfigurasi Environment Variable:**
   Salin `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
   Sesuaikan variabel yang diperlukan (misalnya `SECRET_KEY`, `PRODUCTION=False`).

5. **Jalankan Migrasi Database:**
   ```bash
   python manage.py migrate
   ```

6. **Jalankan Server Pengembang:**
   ```bash
   python manage.py runserver
   ```
   Aplikasi dapat diakses melalui peramban di `http://127.0.0.1:8000/`.

7. **Menjalankan Pengujian Unit (*Unit Tests*):**
   ```bash
   python manage.py test
   ```

---

## AI Disclosure & Transparansi Penggunaan AI

Pengembangan platform Floranity memanfaatkan *Artificial Intelligence* (AI) seperti **GitHub Copilot**, **ChatGPT (GPT-4o)**, dan **Claude 3.5 Sonnet** secara bertanggung jawab dengan pendekatan *Human-in-the-Loop*. AI berperan semata-mata sebagai akselerator penulisan *boilerplate code* dan referensi skema awal, sedangkan perancangan arsitektur, penegakan keamanan, mitigasi celah, dan validasi data ditangani secara manual oleh pengembang.

Laporan komprehensif mengenai strategi prompt, keterbatasan kritis AI (seperti celah otorisasi BOLA, XSS, open redirect, dan ketiadaan caching), serta perbaikan manual yang dilakukan untuk setiap modul dapat dibaca secara lengkap pada dokumen:
👉 **[Laporan Lengkap AI Disclosure (AI_DISCLOSURE.md)](AI_DISCLOSURE.md)**


## API Akun untuk Checkpoint 1

API akun memakai Django REST Framework dengan `serializers.py`, function-based view `@api_view`, dan `api_urls.py`. Semua endpoint akun berada di prefix `/api/v1/akun/`. Data profil dikirim langsung sebagai objek JSON, tanpa pembungkus tambahan; error validasi berisi pesan per field.

| Method | Endpoint | Akses | Respons sukses |
| --- | --- | --- | --- |
| GET | `/api/v1/akun/csrf/` | Publik | 200, `csrfToken` dan cookie `csrftoken` |
| POST | `/api/v1/akun/register/` | Publik + CSRF | 201, akun dan profil baru |
| POST | `/api/v1/akun/login/` | Publik + CSRF | 200, profil pribadi dan cookie session |
| GET | `/api/v1/akun/me/` | Login | 200, profil pribadi |
| PUT / PATCH | `/api/v1/akun/me/` | Login + CSRF | 200, profil setelah diperbarui |
| DELETE | `/api/v1/akun/me/` | Login + CSRF | 204, akun dihapus |
| GET | `/api/v1/akun/profiles/<user_id>/` | Publik | 200, profil publik anggota aktif |
| POST | `/api/v1/akun/logout/` | Login + CSRF | 204, session diakhiri |

### Autentikasi dan input

Autentikasi memakai `SessionAuthentication`, sehingga login web dan API menggunakan session Django yang sama. Pengguna yang belum login mendapat JSON dengan status 403 saat membuka endpoint privat. Login juga dapat dilakukan lewat halaman web `/login/` atau halaman browsable API `/api-auth/login/`.

Untuk request programatis, panggil endpoint `csrf/` terlebih dahulu, simpan cookie dari server, dan kirim nilai `csrfToken` dalam header `X-CSRFToken` pada POST, PUT, PATCH, dan DELETE. Setelah login, token CSRF dirotasi; ambil token baru melalui `csrf/` atau baca cookie `csrftoken` terbaru. Tidak perlu header token/Bearer.

- Pendaftaran menerima JSON `username`, `password1`, dan `password2`. Akun belum otomatis login setelah pendaftaran.
- Login menerima JSON `username` dan `password`.
- PUT/PATCH menerima `display_name`, `bio`, `remove_photo`, serta file `photo` bila diunggah. Gunakan `multipart/form-data` untuk foto; tanpa foto dapat memakai JSON. PUT mewajibkan nama tampilan; PATCH mempertahankan field yang tidak dikirim.
- DELETE menerima JSON `confirmation` yang harus sama dengan nama tampilan. Aturan penghapusan mengikuti `AccountRemovalForm` pada web saat ini.

Profil publik hanya memuat `id`, `user_id`, `display_name`, `bio`, `avatar_url`, `initials`, dan `joined_at`. Profil pribadi menambahkan `username` dan `email`. Pembaruan serta penghapusan selalu memilih akun dari session pemilik; ID pemilik yang dikirim client tidak dapat digunakan untuk mengubah akun orang lain.

Validasi pendaftaran, profil, foto, dan penghapusan menggunakan form Django yang sama dengan halaman web. Foto JPEG/PNG/WebP maksimal 5 MB diolah menjadi JPEG persegi 512 × 512; bio maksimal 500 karakter. Upload foto baru bersamaan dengan `remove_photo=true` ditolak. Profil pengguna yang tidak ditemukan atau tidak aktif menghasilkan 404.

### Menjalankan dan memeriksa API

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py test akun
python manage.py runserver 127.0.0.1:8000
```

Saat server lokal berjalan, buka `http://127.0.0.1:8000/api/v1/akun/csrf/` untuk memeriksa respons JSON/browsable API. Pengujian akun mencakup regresi web dan API: session bersama, CSRF termasuk request anonim, privasi profil publik, kepemilikan data, validasi form, pemrosesan foto, serta penghapusan akun. Verifikasi HTTP lokal juga dilakukan untuk seluruh alur akun. API pada PWS perlu mengikuti proses deployment kelompok; hasil pengujian lokal tidak berarti PWS sudah diperbarui.

Penambahan API akun dan pengujiannya dibantu OpenAI Codex. Referensi teknis: [DRF function-based views](https://www.django-rest-framework.org/api-guide/views/#function-based-views), [ModelSerializer](https://www.django-rest-framework.org/api-guide/serializers/#modelserializer), dan [SessionAuthentication serta CSRF](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).
