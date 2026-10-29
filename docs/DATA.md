# Struktur data yang diterapkan

Setiap file data memakai `revision`, `updatedAt`, `collections`, dan `events` (audit), kecuali identitas yang mempunyai `users` dan audit sendiri. ID stabil, nama/kode untuk tampilan. Koleksi operasional lama tetap kompatibel; normalisasi tabel SQL sebelumnya tidak digunakan.

| Penyimpanan / koleksi | Kolom inti dan relasi |
|---|---|
| Operasional: `patterns` | ID → code, name, land, hasArt, status. Satu pattern dipakai banyak cetakan |
| `pattern_art` | ID sama dengan pattern → svg, preview JPEG; API lama tetap menyajikan JPEG untuk browser |
| `molds` | spec, category, size, patternId, serial, cure, mtype, owner, bladder, status, note, role, mainId, containerId, spacer, brands[] |
| `containers` | code, serial, od, sw, spacers[{size,od}], status; cetakan menunjuk ID container sesuai model lama |
| `stickers` | code, name, img, status; brands[].stickerId mengikuti relasi yang sudah ada pada aplikasi |
| `molds.brands[]` | brand, insert PLUG/PLAT, stickerId; jumlah merek mengikuti aplikasi lama |
| Development: `projects` | code unik, title, owner, status, notes |
| `documents` | projectId → projects, code, title, version, moldId opsional → molds, notes; project+code+version unik |
| `attachments` | documentId → documents, name, storedName internal, size |
| Privat: `suppliers` | code unik, name, contact, email, phone, notes |
| `orders` | number unik, supplierId → suppliers, date, currency, status, notes |
| `items` | orderId → orders, line unik per PO, moldId opsional → molds, description, transaction PURCHASE/REPAIR/MODIFICATION, quantity, unitPrice, discount, tax |
| `attachments` | orderId → orders, name, storedName internal, size |
| Identitas: `users` | ID → login unik, name, role SUPERUSER/ENGINEER/VIEWER, enabled, revision, credential{salt,hash} |
| Sesi | Disimpan di memori server, hanya hash token; kedaluwarsa, token formulir, ID dan revisi akun. Tidak disalin ke SALAK |
| SALAK: `catalog.js` | Proyeksi kolom operasional yang diizinkan; events/deleted kosong; revision, updatedAt dan publishedAt |
| SALAK: `manifest.json` / `current.json` | packageId, sourceRevision, sourceUpdatedAt, publishedAt, schemaVersion |

`quantity` berupa teks integer positif untuk jumlah set/unit. Harga/diskon/pajak berupa **teks desimal**, maksimal empat angka desimal; format ini menghindari perubahan nilai karena floating point. Sistem menyimpan nilai baris; belum menghitung total/kurs lintas mata uang. Satu PO satu mata uang. Lampiran operasional baru maksimal 8 MB; format berbahaya tidak diunduh inline.

Relasi modul diperiksa server pada setiap simpan. Hapus supplier/PO/proyek/dokumen yang masih dirujuk ditolak; cetakan yang dirujuk development/pembelian tidak boleh dihapus, gunakan Nonaktif. Riwayat perubahan dicatat pada file modul masing-masing. Development dan pembelian belum mengimpor otomatis spreadsheet lama: gunakan formulir atau pemetaan lanjutan yang ditinjau dahulu.

Satu simpan mengubah revisi seluruh file modul, sehingga dua pengguna yang mengedit salinan lama mendapat konflik. Penyimpanan antar file bukan transaksi lintas database. Dokumen memakai versi berurutan yang diisi engineer; setiap versi dapat memiliki beberapa lampiran. Pembelian baru boleh tidak memiliki ID cetakan sebelum cetakan diterima.

Gambar utama ditulis dengan kode: `files/pattern/KU-257.svg`, `KU-257-preview.png`, `files/sticker/ST-001.jpg`; preview PNG dikonversi dari JPEG untuk penyimpanan, sementara katalog/API tetap memakai JPEG agar perilaku UI lama dipertahankan. Nama kode Windows yang tidak sah ditolak. Snapshot lama tetap menyertakan gambar lamanya sendiri. Berkas gambar kanonis yang tidak dirujuk lagi setelah rename/hapus bisa tetap ada; pembersihan dilakukan setelah backup, tidak menghapus otomatis.

Tidak ada database, password, data supplier/harga, dokumen perusahaan atau runtime Windows di GitHub. Folder Source menyediakan kode; bundle siap jalan tersedia pada paket pembaruan.
