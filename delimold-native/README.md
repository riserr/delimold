# DELIMOLD Native Python

Desktop rewrite of DELIMOLD v12. The user interface is a native Tk window. The app does not use a browser or a local web page.

## Runtime roles

- **TENDERLOIN** runs the master GUI, keeps the SQLite database, and publishes read-only snapshots to SALAK.
- **Engineer PCs** run the native GUI client and connect to the TENDERLOIN API on port 8766.
- **SALAK** runs the native read-only viewer against `published-python/catalog.json`.
- The three packages use the same Windows executable with different `config.json` files. Only the TENDERLOIN package contains the migration seed.

## Build a Windows portable package

The target is 32-bit Windows 7 and 64-bit Windows 7. Build the Windows package on a Windows host with 32-bit Python 3.8.10 and the pinned packages in `requirements-build.txt`. PyInstaller is not a cross-compiler.

```bat
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DELIMOLD main.py
```

The workflow assembles three folders (`TENDERLOIN`, `ENGINEER`, and `SALAK`). Each folder contains a ready-to-run `App\DELIMOLD.exe`, its bundled Python runtime and libraries, and a role-specific `config.json`. Extract the matching folder on each computer and double-click `App\DELIMOLD.exe`; no browser or Python installation is used. The TENDERLOIN folder alone contains `seed\catalog.js` when the private migration seed is present at build time.

The executable uses only the standard library plus bundled `openpyxl` and `reportlab`. Nothing is installed on target computers. The Python runtime and supporting DLLs are packaged with the app.

## First run

On TENDERLOIN, the first run imports `seed/catalog.js` into `Database/delimold.sqlite3` if the database is empty, then prompts for the first Supervisor account. There is no built-in password. Keep the SQLite database on TENDERLOIN's local drive, not on the SALAK share.

The TENDERLOIN service is started by the same native app process. Engineer client computers use the `client` config. SALAK uses the `viewer` config and only reads `published-python\catalog.json`. Set `publish_path` to the matching folder on the SALAK share before using the example config. The packaged private bundle uses a new folder so an existing v12 `published` snapshot is preserved. No browser is launched in any role.

## Notes

- A Windows firewall or network policy must already allow engineer clients to reach TENDERLOIN on port 8766. This port keeps the Python desktop app separate from the v12 server on port 8765. The app does not change Windows security settings or require administrator rights.
- SALAK publication requires the TENDERLOIN Windows account to have write access to the configured share path. The example config leaves the share unset. The packaged private bundle writes to a new `App\published-python` folder; existing `App\published` is not changed.
- The SQLite database is created separately by this app and seeded only when empty. Keep an existing `Database`, `files`, and `published` directory when copying the new `App` files over an installation. The checkpoint seed has 869 molds, 108 containers, and 89 patterns; it does not contain live accounts, projects, or purchases.
- Excel import/export and PDF output use `openpyxl` and `reportlab`, bundled into the executable during the Windows build.

## Windows 7 note

Python 3.8 is used because it is the final Python series supporting Windows 7. PyInstaller's official support target is newer Windows, so the generated package still needs a launch check on the actual Windows 7 x86 and x64 computers before replacing the current app.

