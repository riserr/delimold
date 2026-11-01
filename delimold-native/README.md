# DELIMOLD Native Python

Paket Windows portable tanpa browser dan tanpa instalasi. Program dijalankan di komputer TENDERLOIN dengan klik ganda `TENDERLOIN\APLIKASI\DELIMOLD.exe`; tidak ada file BAT di paket.

## Susunan folder paket

```text
TENDERLOIN/
└── APLIKASI/
    ├── DELIMOLD.exe   # aplikasi yang dibuka pengguna
    ├── config.json    # pengaturan TENDERLOIN
    ├── seed/          # katalog data awal JSON
    └── RUNTIME/       # Python runtime dan berkas pendukung portable
```

Pengguna membuka `TENDERLOIN\APLIKASI\DELIMOLD.exe`. Pertahankan folder `APLIKASI` dan subfolder `APLIKASI\RUNTIME` tetap utuh. `APLIKASI` memuat program, konfigurasi, dan data awal; `RUNTIME` menyediakan komponen Python agar komputer tidak perlu memasang apa pun. Database kerja tetap disimpan terpisah di `%LOCALAPPDATA%\DELIMOLD\delimold.sqlite3`.

## Lokasi data

Saat pertama dibuka, wizard native meminta file database lokal TENDERLOIN dan folder App bersama di SALAK. Database awal diarahkan ke `%LOCALAPPDATA%\DELIMOLD\delimold.sqlite3`. Snapshot baca-saja diterbitkan ke subfolder `published-python` yang dibuat di lokasi SALAK pilihan.

Setelah login Supervisor, pilih `Atur lokasi data` di sidebar untuk membuka layar pengaturan yang sama lagi.

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

Aturan dependensi mengarah ke dalam: domain tidak mengenal Tkinter atau SQLite; use case bergantung pada kontrak di `application/ports.py`; `main.py` merakit SQLite, publisher, use case, dan UI. Snapshot disaring di use case; publisher hanya menulis objek yang diterimanya.

Daftar utama dimuat per halaman dari SQLite. Pencarian, filter, dan ringkasan dihitung melalui indeks katalog di database. Ekspor Excel atau PDF mengambil seluruh hasil terfilter hanya ketika pengguna meminta ekspor/cetak.

## Kompatibilitas

Paket dibangun dengan Python 3.8 32-bit dan runtime portable. Kompatibilitas Windows 7 perlu dikonfirmasi dengan menjalankan langsung pada komputer TENDERLOIN.
