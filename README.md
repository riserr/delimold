# DELIMOLD — Rancangan Inti

29 Oktober 2026 • Rancangan tujuan; aplikasi dan data belum dimigrasikan.

## 1. Penempatan sistem

**TENDERLOIN menjadi sumber utama seluruh data dan file DELIMOLD. SALAK menyimpan tampilan serta salinan operasional read-only untuk departemen lain.** Drive D komputer supervisor tidak lagi menjadi sumber data aktif setelah migrasi diverifikasi.

| Komputer | Fungsi |
|---|---|
| TENDERLOIN | Menjalankan layanan aplikasi; menyimpan data cetakan, pattern, sticker, container, development project, dan pembelian privat |
| SALAK | Menyajikan aplikasi baca, salinan data operasional dan gambar yang diizinkan; BAT membuka aplikasi SALAK |
| STRAWBERRY, BLUEBERRY / PC engineer | Mengakses aplikasi utama TENDERLOIN |
| PC PPC, Produksi / departemen lain | Mengakses tampilan baca SALAK tanpa koneksi ke TENDERLOIN |

Alur engineer: **browser → aplikasi TENDERLOIN → database utama**. Alur departemen lain: **BAT → browser → aplikasi baca SALAK → salinan lokal SALAK**. BAT hanya membuka URL, tanpa password. Semua tautan data/gambar pada tampilan SALAK harus dilayani dari SALAK, bukan TENDERLOIN.

Sinkronisasi satu arah: **TENDERLOIN → SALAK**, dipicu perubahan data yang boleh dipublikasikan. Syarat implementasi: jalur pengiriman ini diizinkan jaringan; belum diverifikasi. Jika diblokir, perlu bantuan IT. SALAK menjalankan layanan baca; izin layanan, firewall, URL/port dan mulai otomatis perlu diperiksa tanpa mengasumsikan hak administrator. Internet tidak diperlukan. Saat TENDERLOIN mati, SALAK tetap dapat menyajikan salinan terakhir selama layanan SALAK menyala.

## 2. Hak akses

| Modul / tindakan | Supervisor (Superuser) | Engineer | PPC / Produksi / Viewer |
|---|---|---|---|
| Cetakan, pattern, sticker, container | Penuh | Tambah/edit/hapus | Baca/cetak |
| Development project & dokumen teknik | Penuh | Tambah/edit/hapus | Tidak ada |
| Pembelian, harga, supplier & lampiran | Penuh | Tidak ada | Tidak ada |
| Akun, peran, konfigurasi, pemulihan | Penuh | Tidak ada | Tidak ada |

Akun utama berada di TENDERLOIN. SALAK hanya melayani Viewer; bila memerlukan login, gunakan autentikasi lokal SALAK/Windows agar tidak bergantung pada koneksi pengguna ke TENDERLOIN. Jangan menyalin password, sesi atau akun Superuser ke SALAK. Hak akses mengikuti akun, bukan lokasi BAT. Hapus yang merusak relasi ditolak; data bersejarah diarsipkan.

Tab pembelian hanya muncul untuk supervisor. Server juga wajib memeriksa izin pada API, pencarian, ekspor, dan unduhan; menyembunyikan tab saja tidak cukup. Akun memakai hash password dan sesi kedaluwarsa; tidak ada password di BAT/HTML. Superuser aplikasi bukan administrator Windows.

## 3. Struktur folder

Path berikut relatif terhadap folder instalasi `DELIMOLD`; drive ditentukan saat pemasangan.

| Folder | Isi |
|---|---|
| `app/` | Halaman, CSS, JavaScript, komponen dan modul tampilan |
| `server/` | Login, pemeriksaan izin, aturan bisnis, akses database/file |
| `config/` | Konfigurasi dan rahasia server, tidak disajikan ke browser |
| `data/operational/` | Database cetakan dan development project |
| `data/private/` | Database supplier, pesanan dan harga |
| `data/identity/` | Akun, peran dan sesi |
| `files/pattern/` | SVG dan preview pattern |
| `files/sticker/` | Gambar sticker |
| `files/development/` | Dokumen dan lampiran proyek |
| `files/private/` | Penawaran, PO dan lampiran pembelian |
| `sync/` | Antrean publikasi, paket sementara dan status pengiriman ke SALAK |
| `logs/` | Riwayat perubahan dan aktivitas sesuai izin |
| `backups/` | Backup lokal dengan akses terbatas |

**Folder instalasi/data tidak dijadikan share umum.** Pengguna membaca dan mengubah data melalui layanan aplikasi. Folder privat, identitas, konfigurasi dan backup dilindungi izin Windows; hak edit data tidak memberikan hak mengubah kode. Pemisahan database di atas bersifat rancangan; format fisik disesuaikan setelah kode aplikasi diperiksa.

Di SALAK, folder `DELIMOLD-Viewer/` berisi:

| Folder/file | Isi |
|---|---|
| `DELIMOLD.bat` | Membuka URL aplikasi baca SALAK |
| `app/`, `server/` | Tampilan dan layanan baca; tidak menyediakan API edit pengguna |
| `published/` | Paket aktif: data operasional, gambar pattern/sticker, metadata sinkronisasi |
| `incoming/` | Paket sementara; tidak dapat dibaca pengguna sebelum validasi selesai |
| `config/`, `logs/` | Pengaturan layanan, izin penerimaan dan riwayat sinkronisasi |

Hanya proses penerbit yang diberi izin memperbarui salinan; PPC/Produksi tidak memiliki izin tulis. SALAK tidak menyimpan development, pembelian, supplier, harga, lampiran privat atau database identitas TENDERLOIN.

## 4. Struktur data dan relasi utama

Semua tabel memakai ID internal stabil; kode/nama boleh berubah tanpa memutus relasi. `1:N` berarti satu record memiliki banyak record terkait.

| Data / tabel | Relasi dan aturan |
|---|---|
| `patterns`, `categories`, `mold_specs` | Pattern 1:N spek; kategori 1:N spek; spek menyimpan kode, size, pattern |
| `mold_units`, `mold_brands` | Spek 1:N unit cetakan; unit 1:N merek; nomor cetakan unik per spek |
| `container_models`, `container_units`, `container_spacers` | Model 1:N unit container dan 1:N spacer; cetakan menunjuk model dan spacer yang sesuai |
| Main / Sharing pada `mold_units` | Main Segmented 1:N Sharing; Sharing menunjuk satu Main; tanpa siklus |
| `stickers` | Katalog mandiri dengan kode unik; belum direlasikan ke cetakan |
| `projects`, `project_documents`, `document_files`, `project_mold_links` | Proyek 1:N dokumen; dokumen 1:N file/revisi; tabel penghubung mengaitkan proyek dengan spek/unit cetakan |
| `suppliers`, `purchase_orders`, `purchase_order_items` | Supplier 1:N PO; PO 1:N item; harga dan mata uang disimpan pada transaksi |
| `order_item_mold_links`, `private_attachments` | Item pembelian dihubungkan ke unit yang diterima; PO 1:N lampiran privat |
| `users`, `roles`, `user_roles`, `sessions`, `audit_events` | Akun, peran, sesi serta siapa mengubah apa dan kapan |
| `publication_outbox` (TENDERLOIN) | Antrean tahan restart: publication_id, source_revision, status, attempts, last_error |
| `publication_meta` (SALAK) | publication_id, source_revision, source_updated_at, published_at; metadata paket aktif |

Pembelian dapat mengacu ke ID spek/unit operasional; referensi lintas database diperiksa server. Harga/supplier tidak disalin ke data operasional. Pesanan baru boleh belum memiliki unit cetakan; transaksi pembelian dan repair dibedakan.

Aturan cetakan dipertahankan: Airbag tidak memakai bladder; Container Dipakai hanya muncul pada Total Set. Struktur detail development disesuaikan dengan dokumen kerja sebelum impor.

### Publikasi saat ada perubahan

- Sesudah tambah/edit/hapus operasional berhasil disimpan, antrekan publikasi secara konsisten dengan transaksi. Tidak ada pengiriman rutin jika tidak ada perubahan; perubahan privat/development tidak memicu publikasi SALAK.
- Publikasikan hanya tabel, kolom dan gambar yang diizinkan dari cetakan, kategori, merek, container, pattern dan sticker; pertahankan ID serta relasinya. Jangan menyalin seluruh database utama karena berisi development.
- Salinan mencerminkan perubahan, pengarsipan/penghapusan dan penggantian gambar. Paket data, gambar dan metadata divalidasi lalu diaktifkan sekaligus; pengguna tidak melihat paket setengah selesai.
- Jika gagal, paket lama tetap aktif dan antrean mencoba kembali saat koneksi tersedia. Pengiriman ulang tidak menggandakan data; revisi lama tidak boleh menimpa revisi baru.
- Gunakan **footer “Terakhir diperbarui” yang sudah ada**: tampilkan `published_at` dalam WIB, yaitu waktu paket berhasil diaktifkan di SALAK. Jangan memakai waktu membuka/refresh halaman atau waktu percobaan pengiriman yang gagal.

## 5. Penamaan dan penyimpanan

- Pattern: `KU-257.svg` dan `KU-257-preview.png`.
- Sticker: `ST-001.jpg`; gunakan kode sticker, bukan nama lengkap.
- Tanpa tambahan PAT/STK atau r001; gambar pattern/sticker baru menggantikan sebelumnya. Revisi dokumen development dikelola terpisah.
- Path file disimpan relatif; kode unik dan nama file harus valid. Perubahan kode memperbarui nama file serta referensinya bersama.
- Simpan memeriksa versi record agar edit antar pengguna tidak saling menimpa. Putus koneksi tidak membuat database kosong pengganti.

## 6. Migrasi dan pemeriksaan wajib

1. Backup sumber SALAK, TENDERLOIN dan drive D; petakan file, kode serta relasinya.
2. Salin ke TENDERLOIN, cocokkan jumlah data dan lampiran, lalu uji aplikasi.
3. Uji akun supervisor, engineer dan viewer, termasuk penolakan akses privat melalui URL langsung; uji edit bersamaan dan pemulihan backup.
4. Publikasikan salinan awal ke SALAK dan arahkan BAT ke aplikasi baca SALAK. Uji perubahan, hapus, gambar, putus jaringan, pengiriman ulang dan waktu footer; pastikan tidak ada data privat ikut terkirim.
5. Hentikan pemakaian sumber lama setelah verifikasi; hapus sumber lama hanya setelah persetujuan pemilik.

Sediakan backup berkala **di media/perangkat terpisah** dengan izin setara sumber; backup pada TENDERLOIN saja tidak melindungi dari kerusakan perangkat. Sumber utama tetap di TENDERLOIN; salinan SALAK bukan pengganti backup. Kompatibilitas browser kantor, termasuk IE8 bila masih wajib, perlu diuji; akses privat memakai browser yang didukung.
