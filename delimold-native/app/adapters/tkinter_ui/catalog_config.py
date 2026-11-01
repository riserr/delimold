"""Shared labels and field definitions for native catalog screens."""

TABS = {
    "molds": "Data Cetakan",
    "containers": "Data Container",
    "patterns": "Data Pattern",
    "stickers": "Data Sticker",
    "projects": "Development Project",
    "purchases": "Pembelian Mold",
    "accounts": "Management Akun",
    "history": "Riwayat perubahan",
}

FIELDS = {
    "molds": [("spec", "Kode spek"), ("category", "Kategori"), ("size", "Size cetakan"), ("serial", "Nomor cetakan"),
              ("patternId", "Pattern *"), ("containerId", "Container"), ("spacer", "Spacer (mm)"),
              ("cure", "Tipe masak"), ("mtype", "Tipe cetakan"), ("role", "Ukuran"),
              ("mainId", "Acuan Main / Sharing"), ("owner", "Pemilik"),
              ("bladder", "Bladder"), ("brands", "Merek (pisahkan koma)"), ("status", "Status"), ("statusReason", "Alasan status"), ("note", "Catatan")],
    "containers": [("code", "Kode container"), ("serial", "Nomor container"), ("od", "OD sector (mm)"),
                   ("sw", "SW sector (mm)"), ("spacers", "Spacer (JSON)"), ("status", "Status")],
    "patterns": [("code", "Kode pattern"), ("name", "Nama pattern"), ("land", "Land ratio"),
                 ("status", "Status")],
    "stickers": [("name", "Nama sticker"), ("status", "Status")],
    "projects": [("projectId", "ID project"), ("name", "Nama project"), ("spec", "Kode spek"),
                 ("description", "Deskripsi"), ("moldNumbers", "Nomor cetakan"), ("status", "Status"),
                 ("designStart", "Mulai desain"), ("designEnd", "Selesai desain"),
                 ("layoutStart", "Mulai layout"), ("layoutEnd", "Selesai layout"),
                 ("markingStart", "Mulai marking"), ("markingEnd", "Selesai marking"),
                 ("targetDays", "Target pengerjaan (hari)")],
    "purchases": [("date", "Tanggal pembelian *"), ("poReceivedDate", "PO diterima (YYYY-MM-DD)"),
                   ("spec", "Kode spek *"), ("size", "Size ban *"), ("pattern", "Kode pattern"),
                   ("moldNumber", "Nomor mold"), ("quantity", "Jumlah mold *"), ("supplier", "Supplier"),
                   ("currency", "Mata uang *"), ("price", "Harga satuan *"), ("status", "Status"),
                   ("note", "Keterangan")],
}

FILTER_FIELDS = {
    "molds": (("spec", "Kode spek"), ("size", "Size cetakan"), ("patternId", "Pattern"),
              ("cure", "Tipe masak"), ("mtype", "Tipe cetakan"), ("owner", "Pemilik"), ("status", "Status")),
    "containers": (("code", "Kode container"), ("serial", "Nomor container"), ("status", "Status")),
    "patterns": (("code", "Kode pattern"), ("name", "Nama pattern"), ("status", "Status")),
    "stickers": (("name", "Nama sticker"), ("status", "Status")),
    "projects": (("spec", "Kode spek"), ("name", "Nama project"), ("status", "Status")),
    "purchases": (("spec", "Kode spek"), ("supplier", "Supplier"), ("status", "Status")),
    "accounts": (("role", "Peran"), ("enabled", "Status akun")),
    "history": (("action", "Aktivitas"), ("collection", "Jenis data")),
}
