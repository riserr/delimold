# DELIMOLD Native Python

Paket Windows portable tanpa browser dan tanpa instalasi. Program dijalankan di komputer TENDERLOIN dengan klik ganda `TENDERLOIN\APLIKASI\DELIMOLD.exe`; tidak ada file BAT di paket.

## Susunan folder paket

```text
TENDERLOIN/
├── APLIKASI/
│   ├── DELIMOLD.exe   # aplikasi yang dibuka pengguna
│   ├── config.json    # konfigurasi awal
│   ├── app/           # source Python DELIMOLD, untuk dibedah/dipelajari
│   │   ├── main.py
│   │   ├── domain/
│   │   ├── application/
│   │   ├── adapters/
│   │   └── data/seed/catalog.json
│   └── RUNTIME/       # Python runtime dan berkas pendukung portable
└── DATABASE/
    ├── README.txt
    └── delimold.sqlite3  # database utama; dibuat saat aplikasi pertama kali dibuka
```

Pengguna membuka `TENDERLOIN\APLIKASI\DELIMOLD.exe`. Pertahankan folder `APLIKASI`, `APLIKASI\RUNTIME`, dan `DATABASE` tetap utuh. Folder `app` berisi source Python yang mudah diperiksa; EXE menjalankan hasil build dari source tersebut dan tidak membaca file `.py` saat dibuka. `RUNTIME` menyediakan komponen portable agar komputer tidak perlu memasang apa pun. Database kerja berada di `TENDERLOIN\DATABASE\delimold.sqlite3`, terpisah dari aplikasi agar pembaruan folder `APLIKASI` tidak menghapus akun dan data. Adapter konfigurasi menghitung root paket dari lokasi aplikasi, menyimpan path relatif di `%LOCALAPPDATA%\DELIMOLD\config.json`, lalu menyelesaikannya saat startup. Karena itu paket dapat dipindahkan bersama folder `APLIKASI` dan `DATABASE`. Konfigurasi pribadi tetap di `%LOCALAPPDATA%`.

## Lokasi data

Saat pertama dibuka, DELIMOLD meminta pengguna memilih folder `published` yang sudah ada di SALAK sebelum membuka database. Pilihan disimpan di `%LOCALAPPDATA%\\DELIMOLD\\config.json` dan dipakai kembali pada pembukaan berikutnya. DELIMOLD tidak membuat folder publikasi di SALAK; snapshot baca-saja ditulis langsung ke folder `published` yang dipilih. Database kerja berada di `TENDERLOIN\\DATABASE\\delimold.sqlite3`.

Setelah login Supervisor, pilih `Atur lokasi data` di sidebar. Pengaturan ditampilkan di area isi aplikasi; header, sidebar, dan footer tetap terlihat. Gunakan tombol `Kembali ke data` atau pilih tab lain untuk kembali.
Saat lokasi database diganti dari dalam aplikasi, database aktif disalin menggunakan backup SQLite, koneksi aplikasi dialihkan ke file baru, lalu konfigurasi disimpan. File tujuan yang sudah ada ditolak agar tidak tertimpa. Jika publikasi SALAK gagal, konfigurasi lokal tetap tersimpan dan pesan kegagalannya ditampilkan pada halaman pengaturan.

Revisi snapshot yang perlu diterbitkan dicatat lebih dulu di SQLite. Jika SALAK sedang tidak tersedia, DELIMOLD mencoba publikasi lagi otomatis setiap dua menit dan saat aplikasi dibuka kembali. Penyimpanan data lokal tidak menunggu SALAK tersedia.

Jika aplikasi gagal mulai, rincian startup dicatat ke `%LOCALAPPDATA%\DELIMOLD\startup.log`.

## Data dan publikasi

Database aplikasi memakai seed checkpoint v12 jika masih kosong. Seed berisi 869 cetakan, 108 container, dan 89 pattern; akun, project aktif, dan pembelian live tidak termasuk. Simpan data lama sebelum mengganti program.

Aplikasi bekerja lokal di TENDERLOIN tanpa server jaringan atau port. Setelah perubahan tersimpan ke SQLite, use case menyiapkan snapshot publik yang hanya berisi cetakan, pattern, container, sticker, dan pattern art. Adapter SALAK menulis berkas JSON tersebut secara atomik ke folder publikasi. Komputer Engineer cukup membuka snapshot SALAK dengan paket Viewer.

## Susunan kode

```text
app/
├── main.py                         # composition root dan entry point
├── domain/                         # model, aturan peran, dan error bisnis
├── application/                    # use case, DTO, dan kontrak outbound (ports)
│   ├── dto.py                      # request/result pada batas UI–use case
│   └── ports.py                    # kontrak adapter keluar
│   ├── use_cases.py                 # facade komposisi yang tipis
│   ├── account_use_cases.py         # setup, login, dan administrasi akun
│   ├── catalog_use_cases.py         # katalog, perubahan record, dan publikasi
│   ├── location_use_cases.py        # konfigurasi lokasi dan perpindahan database
│   └── transfer_use_cases.py        # alur Excel dan PDF
├── adapters/
│   ├── sqlite_repository.py        # adapter database TENDERLOIN
│   ├── salak_publisher.py          # adapter baca/tulis snapshot JSON
│   ├── configuration.py            # adapter konfigurasi dan path
│   ├── excel_adapter.py            # adapter impor/ekspor Excel
│   ├── pdf_adapter.py              # adapter cetak PDF
│   └── tkinter_ui/                 # adapter UI Tkinter
│       ├── app_window.py           # composition shell dan render katalog
│       ├── authentication.py        # login dan setup Supervisor
│       ├── navigation.py           # navigasi katalog dan pengaturan lokasi
│       ├── record_actions.py       # aksi akun dan record
│       └── error_presenter.py      # pemetaan error ke pesan pengguna
└── data/seed/catalog.json          # seed aplikasi dalam JSON murni
```

Aturan dependensi mengarah ke dalam: domain tidak mengenal Tkinter atau SQLite; use case menyatakan kontrak repository, penyimpanan konfigurasi, seed reader, publisher, dan exporter melalui tipe port di `application/ports.py`; adapter mengimplementasikan port tersebut. `application/dto.py` memuat request dan result bertipe untuk alur katalog, record, akun, transfer Excel/PDF, snapshot, dan pengaturan lokasi. UI mengubah input form menjadi DTO, lalu mengubah result DTO ke representasi tampilan; UI tidak mengimpor adapter penyimpanan. Use case dipisah menjadi layanan akun, katalog/publikasi, lokasi, dan transfer; `use_cases.py` hanya menjadi facade untuk komposisi layanan itu. `tkinter_ui/error_presenter.py` memetakan error aplikasi, validasi, file, dan error tak terduga ke pesan pengguna yang konsisten. `main.py` merakit adapter, use case, konfigurasi, dan UI. Adapter seed menangani pembacaan JSON; publisher hanya menulis snapshot yang disaring use case.

Validasi dibagi konsisten: `domain/validation.py` menjaga aturan bisnis record, akun, pembelian, dan perubahan status; use case memeriksa izin, dukungan alur, serta ketersediaan dependency; adapter memeriksa format input khusus UI seperti struktur template Excel dan path yang dipilih. Use case tetap memvalidasi data akhir sebelum repository menyimpan, sehingga pemeriksaan form/impor hanya membantu pengguna dan tidak menjadi satu-satunya penjaga aturan.

Resolusi path juga dipusatkan di `adapters/configuration.py`: default database, seed, lokasi database lama untuk migrasi, dan konversi path relatif/absolut. `main.py` dan UI memakai hasil resolusi tersebut dan tidak membentuk ulang default database atau fallback seed. Konfigurasi pilihan pengguna disimpan di `%LOCALAPPDATA%\DELIMOLD`; jika variabel itu tidak tersedia, aplikasi memakai `%USERPROFILE%\AppData\Local\DELIMOLD`. Setiap penyimpanan mempertahankan konfigurasi valid sebelumnya sebagai `config.json.bak`; jika file utama rusak atau hilang, aplikasi memuat dan memulihkan salinan tersebut. Jika file utama dan cadangan sama-sama rusak, aplikasi menampilkan error konfigurasi alih-alih diam-diam menghapus pilihan pengguna. Tanggung jawab UI dibagi ke mixin autentikasi, navigasi, aksi record, form, transfer data, dan layar katalog; `app_window.py` merakit mixin itu serta memegang shell/render dan siklus hidup aplikasi. Publikasi snapshot SALAK menulis berkas sementara di folder tujuan, mengganti `catalog.json` secara atomik, menserialkan publisher dalam proses, serta mencoba ulang operasi baca/ganti yang sesaat tertahan oleh Windows/SMB.

Pada pembukaan pertama, aplikasi meminta folder `published` di SALAK yang sudah ada. Jika pemilih dibatalkan, aplikasi berhenti sebelum membuka database. Sesudah lokasi disimpan, aplikasi membuka database dan meminta pembuatan akun Supervisor pertama; katalog awal dari `app/data/seed/catalog.json` dimuat setelah akun berhasil dibuat. File database awal yang dibagikan hanya berisi skema kosong, tanpa akun atau record.

Aturan import domain/application dan izin perubahan lokasi dijaga oleh pemeriksaan berbasis `unittest` dan pustaka standar Python. Jalankan `python -m unittest discover -s tests -v` sebelum perubahan dipaketkan.

Daftar utama dimuat per halaman dari SQLite. Pencarian, filter, dan ringkasan dihitung melalui indeks katalog di database. Ekspor Excel atau PDF mengambil seluruh hasil terfilter hanya ketika pengguna meminta ekspor/cetak.

## Kompatibilitas

Paket dibangun dengan Python 3.8 32-bit dan runtime portable. Kompatibilitas Windows 7 perlu dikonfirmasi dengan menjalankan langsung pada komputer TENDERLOIN.
