# DELIMOLD — TENDERLOIN & SALAK

Pengembangan dari **DELIMOLD-Patch-Cetak-Kategori.zip**. Fitur kategori, cetakan, container, pattern, sticker, impor/ekspor Excel dan cetak/PDF dipertahankan. Data operasional tetap memakai `catalog.js` berisi JSON; tidak memakai SQLite.

## Penempatan dan hak akses

| Lokasi / akun | Fungsi |
|---|---|
| TENDERLOIN | Layanan utama, semua data operasional, development, pembelian privat dan akun |
| Supervisor / SUPERUSER | Kelola seluruh modul dan akun melalui browser |
| Engineer / ENGINEER | Kelola operasional dan development melalui browser; tanpa akses pembelian/akun |
| SALAK | Layanan baca dengan paket operasional terakhir yang berhasil diterima |
| PPC / Produksi | Buka `http://SALAK:8765` melalui BAT; tanpa koneksi ke TENDERLOIN |

SALAK memberi akses baca operasional kepada pengguna jaringan yang dapat menjangkau layanannya; tidak meminta akun TENDERLOIN. Semua perubahan SALAK ditolak server. Data pembelian, dokumen development, password, sesi, serta audit internal tidak diterbitkan ke SALAK. Tab pembelian dan pengelolaan akun hanya diberikan kepada supervisor pada Workspace.

## Struktur penyimpanan

| Folder di TENDERLOIN | Isi |
|---|---|
| `Aplikasi/` | Server siap jalan dan tampilan; `Source/` berisi sumber pengembangan |
| `config/server.json` | Mode, alamat layanan, host yang diizinkan, target publikasi |
| `data/operational/catalog.js` | Koleksi cetakan lama dan revisinya |
| `data/development/development.json` | Proyek, dokumen/revisi, relasi dan metadata lampiran |
| `data/private/private.json` | Supplier, PO, item/harga serta metadata lampiran privat |
| `data/identity/users.json` | Akun, peran dan hash password; tidak disajikan lewat web |
| `files/pattern/`, `files/sticker/` | `KU-257.svg`, `KU-257-preview.png`, `ST-001.jpg` |
| `files/development/`, `files/private/` | Lampiran memakai ID internal agar nama tidak bertabrakan |
| `logs/auth.jsonl` | Login, kegagalan login dan logout tanpa password/token |
| `backups/` | Tempat backup terkontrol; tetap sediakan salinan di perangkat terpisah |

SALAK menyimpan `Aplikasi/`, `config/server.json`, dan `published/`. Setiap paket berada di `published/packages/<id>/`; `published/current.json` menunjuk paket aktif. Gambar operasional disertakan dalam JSON paket dan dilayani API SALAK, sehingga tidak ada tautan gambar ke TENDERLOIN. SALAK tidak membutuhkan folder data privat/identitas utama.

## Cara memasang paket uji

1. **Gunakan folder baru**, jangan menimpa instalasi/data yang sedang dipakai. Salin folder `Aplikasi/Runtime` dari paket Windows lama yang sudah berjalan; paket pembaruan ini tidak mengganti runtime tersebut.
2. Di TENDERLOIN, jalankan `Siapkan-TENDERLOIN.bat`. Tarik file **`Database/catalog.js` lama** ke `Migrasi-Catalog.bat`. Migrasi menyalin dan memvalidasi sumber, menolak tujuan yang sudah terisi, dan tidak menghapus sumber lama.
3. Jalankan `Setup-Supervisor.bat` di TENDERLOIN untuk membuat akun pertama dan password minimal 12 karakter. Tidak ada akun/password bawaan. Supervisor membuat akun engineer melalui **Workspace → Akun & peran**.
4. Di SALAK, gunakan folder paket terpisah dan jalankan `Siapkan-SALAK.bat`. Sediakan jalur folder `published` yang **dapat ditulis dari TENDERLOIN**. Isi `publishTarget` pada konfigurasi TENDERLOIN dengan UNC sebenarnya, misalnya `\\SALAK\DELIMOLD-Publish\published`. Contoh ini bukan lokasi kantor yang sudah diverifikasi.
5. Jalankan `Jalankan-Layanan.bat` di TENDERLOIN. Paket pertama dikirim ke SALAK. Lalu jalankan layanan SALAK. Engineer memakai `Buka-DELIMOLD.bat`; PPC/Produksi memakai `Buka-Baca-Saja.bat` atau `Buka-IE8.bat`. Layanan harus tetap berjalan pada kedua host; mulai otomatis Windows belum dipasang.
6. Uji login/izin, data lama, kategori, Excel, gambar, cetak dan sinkronisasi sebelum berpindah operasional. SALAK tetap membaca paket terakhir bila TENDERLOIN mati. Hentikan pemakaian sumber lama hanya setelah cocok; jangan menghapus sumber lama sebelum backup dan verifikasi.

Port bawaan 8765. Jika memakai IP/alias lain, sesuaikan `hosts` dan URL BAT; host yang tidak terdaftar ditolak. Firewall dan jalur TENDERLOIN → SALAK harus diizinkan kantor. Paket tidak mengubah firewall/izin Windows secara otomatis. Jalankan proses dengan akun Windows yang sesuai; batasi folder `data/private`, `data/identity`, konfigurasi dan backup dari akses file engineer. Akses aplikasi melalui browser saja. Superuser aplikasi tidak mengubah izin Windows.

Login memakai password hash PBKDF2, cookie HttpOnly, sesi 8 jam, pemeriksaan perubahan peran/status, pembatasan percobaan dan token formulir. Logout, akun nonaktif atau perubahan akun membatalkan sesi. Restart layanan meminta login ulang. Koneksi bawaan HTTP LAN; gunakan hanya jalur kantor yang disetujui. Bila perlu enkripsi transport, terminasi HTTPS perlu disiapkan di jaringan kantor.

## Data dan sinkronisasi

Lihat [struktur data](docs/DATA.md). Penyimpanan memeriksa revisi dan memakai penguncian serta penggantian file sementara. `.bak` menyimpan kondisi sebelum perubahan. Backup lengkap database dan lampiran dilakukan **saat layanan dihentikan**, lalu diuji pemulihannya.

Revisi operasional yang berhasil tersimpan menjadi antrean tahan restart: pengirim membandingkannya dengan revisi paket SALAK. Perubahan operasional memicu publikasi langsung; pemeriksaan ulang setiap 15 detik hanya mengirim bila ada revisi tertunda. Perubahan development/privat tidak memicu publikasi. Kegagalan jaringan mempertahankan paket lama. Revisi lebih lama ditolak, revisi sama tidak diterbitkan ulang. Footer yang sudah ada menunjukkan **waktu publikasi berhasil**, bukan waktu refresh. File paket lama dipertahankan untuk pemulihan; pembersihan retensi dilakukan terkontrol saat layanan dihentikan.

## Validasi dan pengembangan

Di `Aplikasi/Source`: `npm ci` lalu `npm run build` (hanya komputer pengembang). Pengguna Windows tidak menjalankan npm. Jalankan `node tests/architecture.test.js` dari root untuk pengujian integrasi pada folder sementara.

Target backend tetap Node 12/ES2019 dan tampilan ES3. Pengujian Linux dengan Node 12.22.12 bukan bukti kompatibilitas Windows 7, IE8, SMB/UNC atau ACL kantor. Paket ini memerlukan uji penerimaan di komputer kantor sebelum menggantikan versi lama. Lihat [hasil verifikasi](docs/VERIFIKASI.md).
