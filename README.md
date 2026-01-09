# Air Quality Dashboard — Public View

Dashboard ini menyajikan **analisis dan visualisasi kualitas udara** berdasarkan **dataset internal pengukuran stasiun**.  
Aplikasi dibuat sebagai media eksplorasi data untuk memahami **pola, tren, dan perbandingan kualitas udara antar stasiun dan waktu**

---

## Tujuan Dashboard
Dashboard ini bertujuan untuk:
- Membandingkan kualitas udara antar stasiun pengukuran
- Menganalisis tren polutan dari waktu ke waktu
- Mengidentifikasi stasiun yang relatif lebih bersih atau lebih tercemar
- Memahami pola harian dan musiman polusi udara

Dashboard ini cocok digunakan sebagai **alat eksplorasi data** dan **pendukung analisis**, bukan sebagai standar penilaian absolut kualitas udara.

---

## Fitur Utama
- **Filter Interaktif**
  - Pemilihan stasiun
  - Rentang tanggal
  - Jenis polutan (PM2.5, PM10, SO2, NO2, CO, O3)
- **Key Metrics (KPI)**
  - Nilai terbaru
  - Rata-rata periode terpilih
  - Nilai minimum dan maksimum
  - Status relatif berdasarkan perbandingan internal
- **Visualisasi Data**
  - Grafik tren polutan
  - Pola harian (rata-rata per jam)
  - Distribusi kategori relatif
  - Heatmap (bulan vs jam)
  - Ranking stasiun berdasarkan rata-rata polutan

---

## Cara Menjalankan Dashboard Secara Lokal (Instruksi Setup)
Ikuti langkah-langkah berikut untuk menjalankan dashboard:

### 1. Persiapan Environment
Disarankan untuk menggunakan virtual environment agar tidak mengganggu library global:
```
python -m venv venv
``` 

### 2. Instalasi Library
Instal semua library yang dibutuhkan berdasarkan file requirements.txt:
```
pip install -r requirements.txt
```
### 3. aktifkan env
aktifkan env sebelumm menjalankan sistem ;
```
.\.venv\Scripts\Activate.ps1
```

### 4. Menjalankan Aplikasi
perintah berikut untuk membuka sistem:
```
streamlit run dashboard/dashboard.py
```