# FastCapture 📷

Aplikasi screenshot desktop Windows dengan performa tinggi, visual utilitas klasik yang tegas (*crisp, sharp high-contrast, professional desktop utility look* - bukan tampilan AI/neon modern yang generik), fitur lengkap persis **FastStone Capture**, dan dapat langsung dikompilasi menjadi **file `.exe` mandiri (standalone)**.

---

## Fitur Utama

### 1. Bilah Tangkap Melayang (Floating Toolbar)
- **Always-on-Top & Draggable**: Bilah ringkas yang bisa digeser bebas ke sudut layar mana saja.
- **Tombol Mode Tangkap Lengkap**:
  - 🖥️ **Capture Active Window** (`Alt + PrintScreen`): Menangkap jendela aktif di latar depan secara presisi.
  - 🎯 **Capture Window / Object** (`Shift + PrintScreen`): Mendeteksi kontrol antarmuka/jendela di bawah kursor dengan bingkai merah tebal otomatis.
  - 📐 **Capture Rectangular Region** (`Ctrl + PrintScreen`): Layar dibekukan dengan **Sniper Crosshair** dan **Loupe Magnifier 8x** yang menampilkan info koordinat `(X, Y)`, warna `HEX/RGB`, dan dimensi `W x H`.
  - ✍️ **Capture Freehand Region** (`Ctrl + Shift + PrintScreen`): Tangkapan area bebas (lasso) dengan potongan transparan.
  - 🌐 **Capture Full Screen** (`PrintScreen`): Tangkap seluruh layar monitor (mendukung multi-monitor).
  - 💧 **Screen Color Picker** (`Ctrl + Alt + C`): Pipet pembesar untuk mengambil warna piksel apa pun di layar dan menyalin kode HEX langsung ke clipboard.
  - 📁 **Open Image File**: Buka file gambar langsung ke Studio Editor.
  - 🔄 **Output Destination Selector**: Pilihan tujuan output langsung (Editor, Clipboard, Auto-Save Folder, Save Dialog, Print).

### 2. Studio Editor & Anotasi Lengkap (FastStone Draw)
- **Anotasi Vektor**:
  - 🏹 **Panah (Arrow)**: Panah lurus dengan kepala segitiga tajam dan ukuran fleksibel.
  - 🔢 **Step Badge Stamp (1, 2, 3...)**: Stempel nomor urut tutorial yang otomatis bertambah setiap kali diklik.
  - ⬛ **Bentuk Geometri**: Kotak, Persegi membulat (*Rounded Rect*), dan Lingkaran/Elips.
  - 🖍️ **Highlighter Pen**: Stabilo semi-transparan (kuning, hijau, oranye, cyan) untuk teks dokumen.
  - 🌫️ **Blur & Pixelate (Sensor / Redaksi)**: Efek sensor mozaik atau blur untuk menyembunyikan data pribadi / password.
  - 🔤 **Teks & Label**: Kotak teks dengan latar belakang solid.
  - ✏️ **Pen & Line**: Coretan bebas halus dan garis lurus.
- **Manipulasi Gambar**:
  - ✂️ **Crop**: Pemotong gambar interaktif dengan konfirmasi enter/esc.
  - 📐 **Resize**: Ubah ukuran dimensi gambar/kanvas dengan kunci rasio aspek.
  - 🔄 **Rotate & Flip**: Putar 90° CW, 90° CCW, Balik Horizontal/Vertikal.
  - 🖼️ **Drop Shadow & Border**: Efek bayangan khas FastStone dan bingkai warna solid.
- **Navigasi & Ekspor**:
  - 🔍 **Zoom & Pan**: Zoom 10% - 1000% (Ctrl + Scroll / Fit / 100%), geser kanvas dengan Alt/Spacebar + Drag.
  - ↩️ **Undo / Redo** tak terbatas.
  - 💾 **Simpan Format**: PNG, JPG, BMP, WEBP, dan PDF Document.

### 3. Global Hotkeys & System Tray
- Tombol pintas global Windows yang dapat dikustomisasi di menu **Settings**.
- Ikon System Tray di taskbar dengan menu klik kanan cepat dan mode minimize latar belakang.

---

## Cara Menjalankan

### Melalui Python:
```bash
python app/main.py
```

### Melalui File Kompilasi `.exe`:
Jalankan file yang berada di:
```
dist/FastCapture/FastCapture.exe
```

---

## Cara Mengompilasi Ulang ke `.exe` (Windows):
```bash
python build_exe.py
```
Hasil build akan dibuat otomatis di folder `dist/` (`SanCapture_Setup.exe` dan `SanCapture.exe`).

---

## Versi macOS (`.dmg`):

SanCapture mendukung penuh sistem operasi **macOS (Intel & Apple Silicon M1/M2/M3/M4)**.

### Cara Build `.dmg` di Mac:
Jalankan salah satu perintah berikut di terminal Mac:
```bash
# Opsi 1: Menggunakan shell script otomatis
chmod +x build_dmg.sh
./build_dmg.sh

# Opsi 2: Menggunakan Python builder
python3 build_mac.py
```
File installer **`SanCapture.dmg`** dengan shortcut drag-and-drop ke `/Applications` akan otomatis tercipta di folder `dist/SanCapture.dmg`.

### Cara Build `.dmg` Otomatis via GitHub Actions (Dari Windows):
Karena binary Mach-O macOS memerlukan kernel macOS, proyek ini telah dilengkapi dengan workflow CI/CD GitHub Actions:
1. Push repository ini ke GitHub.
2. Buka tab **Actions** di GitHub repository Anda.
3. Jalankan workflow **"Build macOS DMG Package"** (atau buat Git Tag `v1.0.0`).
4. Unduh file **`SanCapture.dmg`** dari bagian **Artifacts** atau **Releases**.
