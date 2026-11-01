# Build DELIMOLD Native untuk Windows x86

Paket ini memuat source terbaru dan database awal tanpa akun/record. Untuk menghasilkan program `.exe`, jalankan langkah berikut pada Windows x86 dengan Python 3.8 x86.

1. Buka Command Prompt pada folder `TENDERLOIN\APLIKASI`.
2. Pasang dependency build dengan `python -m pip install -r requirements-build.txt`.
3. Build aplikasi dengan:

   ```bat
   python -m PyInstaller --noconfirm --clean --onedir --windowed --contents-directory RUNTIME --name DELIMOLD --distpath build\dist --workpath build\work --specpath build app\main.py
   ```

4. Salin katalog seed ke folder di samping executable:

   ```bat
   mkdir build\dist\DELIMOLD\app\data\seed
   copy app\data\seed\catalog.json build\dist\DELIMOLD\app\data\seed\catalog.json
   ```

5. Salin isi `build\dist\DELIMOLD` ke `TENDERLOIN\APLIKASI`. Letakkan database awal dari `TENDERLOIN\DATABASE\delimold.sqlite3` pada folder `TENDERLOIN\DATABASE` di paket.

Saat dijalankan, aplikasi membuat akun Supervisor pertama terlebih dahulu; sesudah login, katalog seed dimuat. Pengaturan lokasi publikasi SALAK dilakukan dari menu Atur lokasi data.

Build ini belum dapat dijalankan dari Linux. Uji akhir executable pada Windows 7/TENDERLOIN dan share SALAK tetap diperlukan.
