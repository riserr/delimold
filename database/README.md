# Struktur database DELIMOLD

Skema awal SQLite untuk dasar coding, bukan migrasi aplikasi lama. Jalankan masing-masing SQL sekali pada database lokal **yang baru dan kosong**; jangan jalankan ke data produksi. Pilihan SQLite masih perlu dicocokkan dengan paket aplikasi dan komputer kantor. Tidak ada data perusahaan, akun bawaan, password atau database berisi data di repository.

| File skema | Database tujuan | Isi |
|---|---|---|
| `schema/operational.sql` | TENDERLOIN: `data/operational/operational.db` | Cetakan, pattern, sticker, container, development, audit dan antrean publikasi |
| `schema/private.sql` | TENDERLOIN: `data/private/private.db` | Supplier, PO, harga, lampiran dan audit privat |
| `schema/identity.sql` | TENDERLOIN: `data/identity/identity.db` | Akun, peran, izin dan sesi; hanya peran/izin yang diisi awal |
| `schema/viewer.sql` | SALAK: paket di `published/` | Salinan operasional dan metadata waktu footer |

## Kontrak implementasi

- Hanya layanan lokal host yang membuka file database. Client tidak membuka SQLite melalui UNC. Aktifkan `PRAGMA foreign_keys = ON` pada **setiap koneksi**. Pisahkan izin OS untuk layanan operasional, privat, identitas dan penerbit.
- ID berupa UUID yang dibuat layanan. Kolom lintas database (`*_external_id`, actor/user ID) diperiksa layanan; bukan foreign key SQLite. Arsipkan record bersejarah agar referensi privat tetap tersedia.
- `revision`, `updated_at`, `updated_by`, audit dan antrean wajib ditulis oleh layanan dalam transaksi yang sama. Update memakai `WHERE id = ? AND revision = ?`, menambah revision; nol record berubah berarti konflik. Tidak ada trigger sinkronisasi otomatis dalam versi ini.
- Harga memakai integer berskala: `unit_price_scaled / 10^money_scale`; diskon/pajak adalah jumlah total per baris, dengan skala dan mata uang PO. Contoh skala 2: 12345 = 123.45. Layanan menghitung dengan aritmetika desimal/integer, memeriksa overflow dan tidak menjumlahkan mata uang berbeda. Quantity awal berupa jumlah set/unit utuh.
- Dimensi dalam mm; land ratio dalam persen 0–100. Nilai teknis seperti `SEGMENTED`, `AIRBAG`, `MAIN`, `SHARING`, `PLUG`, `PLAT` perlu dipetakan dari data lama sebelum impor. Aturan Main/Sharing dan spacer diuji. Dokumen development mempunyai file versi berurutan; versi terbaru ditentukan dari `version_number` terbesar.
- Waktu menggunakan UTC ISO 8601 dengan format seragam; UI menampilkan WIB. Path file relatif terhadap root yang sesuai dan wajib divalidasi layanan, termasuk larangan traversal serta file di luar root.
- Server wajib memeriksa izin setiap request. Skema role tidak dengan sendirinya mengamankan API. Hash password memakai pustaka teruji; sesi menyimpan hash token, bukan token mentah. Superuser pertama disiapkan secara lokal oleh pemilik, tanpa kredensial bawaan. SALAK tidak menerima database identitas ini.

## Kontrak publikasi TENDERLOIN → SALAK

1. Simpan perubahan operasional yang boleh diterbitkan beserta audit dan baris `publication_outbox` dalam satu transaksi. Perubahan development/privat tidak membuat antrean. Antrean mencatat status pengiriman, bukan isi privat.
2. Bangun snapshot konsisten dari sembilan view `publish_*` yang kolomnya eksplisit. Jangan memakai `SELECT *` dari database utama. Snapshot boleh membawa record arsip untuk menjaga relasi; tampilan default menyaring `archived_at IS NULL`.
3. Buat database viewer baru dari `viewer.sql`; masukkan hanya kolom view dan gambar terkait. Siapkan seluruh paket di `incoming/`, cek foreign key, file serta revisi sebelum aktivasi. Paket awal diterbitkan saat setup.
4. Aktifkan paket lengkap secara atomik menggunakan direktori versi dan pergantian penunjuk paket aktif. Jangan menimpa file database yang sedang dibaca. Isi `published_at` pada aktivasi sukses; footer yang sudah ada memakai nilai ini. Implementasi aktivasi di Windows masih harus diuji.
5. Penerima menolak revisi lebih lama; pengiriman ID/revisi yang sama menjadi no-op dan tidak mengubah waktu footer. Tandai antrean published setelah konfirmasi penerimaan. Jika gagal/crash, pertahankan paket lama dan retry antrean; tidak menerbitkan ulang rutin tanpa perubahan.

Pengirim jaringan, login, aktivasi paket, UI, dan migrasi data belum diimplementasikan. Tabel viewer bukan mekanisme read-only: layanan pembaca harus membuka database dengan mode read-only dan tidak menyediakan API mutasi. Akun penerbit memiliki izin terpisah untuk mengganti paket.

## Pemeriksaan

Dari root repository, jalankan `python -m unittest discover -s tests -v`. Pengujian menggunakan database sementara di memori, tanpa mengubah data kantor.
