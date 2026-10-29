# Verifikasi paket arsitektur

Dasar: DELIMOLD-Patch-Cetak-Kategori.zip. Verifikasi memakai data sintetis dan direktori sementara, tidak memindahkan data kantor.

| Pemeriksaan | Hasil |
|---|---|
| Build server dan alat setup dari source | Lulus |
| 66 pemeriksaan integrasi pada Node 12.22.12 Linux | Lulus |
| Login salah/benar, peran, token formulir, logout dan pembatalan sesi | Lulus |
| Penolakan data privat/akun/unduhan privat untuk engineer dan viewer | Lulus |
| CRUD proyek/dokumen, referensi, supplier/PO dan lampiran privat | Lulus |
| Unggahan lampiran lewat form multipart/iframe dengan pemeriksaan origin | Lulus |
| Penyimpanan katalog lama, konflik revisi dan kategori RLT | Lulus |
| Gambar SVG, JPEG API, PNG di disk dan ekspor Excel berisi gambar | Lulus |
| Migrasi salinan katalog dan penolakan menimpa tujuan | Lulus |
| SALAK read-only, kolom publik, revisi sama tidak mengubah footer | Lulus |
| Kegagalan pengiriman dan pemulihan antrean setelah jalur tersedia | Lulus dengan simulasi folder tidak tersedia |
| Sintaks dashboard, login, portal sebagai ECMAScript 3 | Lulus |
| DOM/XHR: koneksi dashboard, kategori, footer WIB, tab sesuai peran, formulir proyek | Lulus pada jsdom (Node 24); bukan browser asli |
| Tampilan visual Chromium | Belum diuji; browser pengujian tidak tersedia |
| Windows 7, IE8 asli, runtime Windows lama, firewall, UNC/SMB dan ACL | Perlu uji di kantor |

Node 12 Linux dan pemeriksaan ES3 tidak menjamin semua perilaku browser/Windows. Gunakan folder baru dan runtime Windows dari paket yang sebelumnya berfungsi. Sebelum mengganti instalasi lama, cocokkan jumlah data, kategori, gambar, impor Excel, cetak, izin supervisor/engineer, dan waktu footer pada dua komputer.

Tidak ada perhitungan total pembelian, impor otomatis data privat/development, pemasangan Windows service, pengaturan ACL, HTTPS, rotasi backup atau pembersihan paket lama otomatis dalam rilis ini. Data modul baru dikelola melalui formulir dan lampiran. Ketergantungan jaringan TENDERLOIN → SALAK masih harus dibuktikan di kantor.
