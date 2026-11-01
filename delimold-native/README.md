# DELIMOLD Native Python

Paket desktop Windows tanpa browser dan tanpa instalasi pada komputer pengguna. Satu direktori program diletakkan di share TENDERLOIN. Supervisor membuka aplikasi utama dari komputer TENDERLOIN, sementara Engineer membuka file yang sama melalui `Buka-Engineer.bat`.

## Paket yang dihasilkan

Workflow Windows x86 membangun satu folder `TENDERLOIN` berisi executable native dan runtime Python yang dibutuhkan, seed checkpoint v12, serta tiga launcher:

- `Buka-DELIMOLD.bat` — mode utama TENDERLOIN.
- `Buka-Engineer.bat` — mode Engineer yang tersambung ke TENDERLOIN.
- `Atur-Lokasi-DELIMOLD.bat` — jendela untuk memilih database lokal dan folder publikasi SALAK.

Engineer tidak perlu menerima atau mengekstrak program terpisah. Mereka menjalankan file dari share. Proses client berjalan di komputer Engineer dan menghubungi API aplikasi TENDERLOIN pada port 8766; semua data utama tetap di database SQLite lokal TENDERLOIN. Layanan ini bukan web browser atau web server.

## Pemilihan lokasi

Saat pertama dijalankan di TENDERLOIN, wizard meminta:

- File database SQLite pada profil/disk lokal TENDERLOIN. Lokasi awalnya `%LOCALAPPDATA%\DELIMOLD\delimold.sqlite3`, supaya file database tidak masuk ke direktori share aplikasi.
- Folder App bersama di SALAK. Aplikasi membuat subfolder `published-python` dan menerbitkan snapshot `catalog.json` di sana.

Jalankan `Atur-Lokasi-DELIMOLD.bat` untuk mengubah lokasi kemudian. Akun proses TENDERLOIN harus dapat menulis ke folder publikasi SALAK. Jangan pilih path database UNC/share.

## Seed dan migrasi

Jika database baru masih kosong, seed `seed/catalog.js` checkpoint v12 akan dimuat otomatis. Aplikasi kemudian meminta pembuatan akun Supervisor pertama; tidak ada password bawaan. Seed berisi data master snapshot, bukan akun kantor, proyek aktif, atau pembelian live. Database lama tidak otomatis dikonversi.

## Jaringan dan platform lama

Engineer membutuhkan koneksi LAN ke nama komputer TENDERLOIN pada port 8766. Aturan firewall/jaringan harus sudah mengizinkan koneksi ini; program tidak mengubah kebijakan Windows atau meminta hak administrator. Python 3.8 x86 dipilih untuk dukungan mesin Windows lama. Paket perlu dibuka dan dijalankan langsung pada Windows 7 kantor sebelum penggunaan operasional karena runtime bundling modern belum diverifikasi pada komputer tersebut.
