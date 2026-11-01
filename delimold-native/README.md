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

Pengguna membuka `TENDERLOIN\APLIKASI\DELIMOLD.exe`. Pertahankan folder `APLIKASI`, `APLIKASI\RUNTIME`, dan `DATABASE` tetap utuh. Folder `app` berisi source Python yang mudah diperiksa; EXE menjalankan hasil build dari source tersebut dan tidak membaca file `.py` saat dibuka. `RUNTIME` menyediakan komponen portable agar komputer tidak perlu memasang apa pun. Database kerja berada di `TENDERLOIN\DATABASE\delimold.sqlite3`, terpisah dari aplikasi agar pembaruan folder `APLIKASI` tidak menghapus akun dan data. Path database disimpan relatif terhadap root TENDERLOIN. Konfigurasi pribadi tetap disimpan di `%LOCALAPPDATA%\DELIMOLD\config.json`.

## Lokasi data

Saat pertama dibuka, wizard native meminta lokasi database di folder `TENDERLOIN\DATABASE` dan folder App bersama di SALAK. Database dibuat sebagai `TENDERLOIN\DATABASE\delimold.sqlite3`. Database lama dari lokasi default `%LOCALAPPDATA%\DELIMOLD\delimold.sqlite3` dipindahkan dengan aman saat pembaruan pertama. Snapshot baca-saja diterbitkan ke subfolder `published-python` yang dibuat di lokasi SALAK pilihan.

Setelah login Supervisor, pilih `Atur lokasi data` di sidebar untuk membuka layar pengaturan yang sama lagi.
Pengaturan dari dalam aplikasi ditampilkan di jendela utama yang sama. Simpan atau tutup layar pengaturan untuk kembali ke aplikasi.

Jika aplikasi gagal mulai, rincian startup dicatat ke `%LOCALAPPDATA%\DELIMOLD\startup.log`.

## Data dan publikasi

Database aplikasi memakai seed checkpoint v12 jika masih kosong. Seed berisi 869 cetakan, 108 container, dan 89 pattern; akun, project aktif, dan pembelian live tidak termasuk. Simpan data lama sebelum mengganti program.

Aplikasi bekerja lokal di TENDERLOIN tanpa server jaringan atau port. Setelah perubahan tersimpan ke SQLite, use case menyiapkan snapshot publik yang hanya berisi cetakan, pattern, container, sticker, dan pattern art. Adapter SALAK menulis berkas JSON tersebut secara atomik ke folder publikasi. Komputer Engineer cukup membuka snapshot SALAK dengan paket Viewer.

## Susunan kode

```text
app/
├── main.py                         # composition root dan entry point
├── domain/                         # model, aturan peran, dan error bisnis
├── application/                    # use case dan kontrak outbound (ports)
├── adapters/
│   ├── sqlite_repository.py        # adapter database TENDERLOIN
│   ├── salak_publisher.py          # adapter baca/tulis snapshot JSON
│   ├── configuration.py            # adapter konfigurasi dan path
│   ├── excel_adapter.py            # adapter impor/ekspor Excel
│   ├── pdf_adapter.py              # adapter cetak PDF
│   └── tkinter_ui/                 # adapter UI Tkinter
└── data/seed/catalog.json          # seed aplikasi dalam JSON murni
```

Aturan dependensi mengarah ke dalam: domain tidak mengenal Tkinter atau SQLite; use case menyatakan kontrak repository, seed reader, publisher, dan exporter melalui tipe port di `application/ports.py`; adapter mengimplementasikan port tersebut. `main.py` hanya merakit adapter, use case, konfigurasi, dan UI. Use case mengatur inisialisasi katalog; seed reader menangani pembacaan JSON. Snapshot disaring di use case; publisher hanya menulis objek yang diterimanya.

Daftar utama dimuat per halaman dari SQLite. Pencarian, filter, dan ringkasan dihitung melalui indeks katalog di database. Ekspor Excel atau PDF mengambil seluruh hasil terfilter hanya ketika pengguna meminta ekspor/cetak.

## Kompatibilitas

Paket dibangun dengan Python 3.8 32-bit dan runtime portable. Kompatibilitas Windows 7 perlu dikonfirmasi dengan menjalankan langsung pada komputer TENDERLOIN.
