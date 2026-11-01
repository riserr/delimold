# DELIMOLD Native Python

Paket Windows portable tanpa browser dan tanpa instalasi. Untuk tahap ini program dijalankan langsung di komputer TENDERLOIN dengan klik ganda `TENDERLOIN\DELIMOLD.exe`; tidak ada file BAT di paket.

## Lokasi data

Saat pertama dibuka, wizard native meminta file database lokal TENDERLOIN dan folder App bersama di SALAK. Database awal diarahkan ke `%LOCALAPPDATA%\DELIMOLD\delimold.sqlite3`. Snapshot baca-saja diterbitkan ke subfolder `published-python` yang dibuat di lokasi SALAK pilihan.

Setelah login Supervisor, pilih `Atur lokasi data` di sidebar untuk membuka layar pengaturan yang sama lagi.

Jika aplikasi gagal mulai, rincian startup dicatat ke `%LOCALAPPDATA%\DELIMOLD\startup.log`.

## Data dan jaringan

Database aplikasi memakai seed checkpoint v12 jika masih kosong. Seed berisi 869 cetakan, 108 container, dan 89 pattern; akun, project aktif, dan pembelian live tidak termasuk. Simpan data lama sebelum mengganti program.

Aplikasi utama menyediakan layanan LAN pada port 8766 untuk mode client. Windows Engineer belum menjadi fokus paket ini; fokus tahap ini adalah memastikan aplikasi utama terbuka di TENDERLOIN.

## Kompatibilitas

Paket dibangun dengan Python 3.8 32-bit dan runtime portable. Kompatibilitas Windows 7 perlu dikonfirmasi dengan menjalankan langsung pada komputer TENDERLOIN.
