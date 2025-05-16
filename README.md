# 🏠 House Property Data Scraper

Scraper untuk mengambil data properti (rumah) dari situs [Rumah123.com](https://www.rumah123.com/), ditujukan untuk keperluan riset dan edukasi.

## 🔗 Repositori
https://github.com/MuhammadRizki8/house-property-data-scraper

## 📦 Teknologi
- Python 3
- Requests
- BeautifulSoup
- Pandas
- Logging

## ⚙️ Instalasi & Menjalankan

### 1. Clone dan Masuk ke Direktori
```bash
git clone https://github.com/MuhammadRizki8/house-property-data-scraper
cd house-property-data-scraper
```
### 2. Buat dan Aktifkan Virtual Environment
```
python -m venv venv
```
aktifkan venv
```
source venv/bin/activate       # Linux/macOS
```
atau
```
venv\Scripts\activate          # Windows
```
### 3. Install Dependensi
```
pip install -r requirements.txt
```
### 4. Jalankan Scraper
```
python main.py
```

### 🔧 Opsi Tambahan
```
python main.py --pages 3 --delay-min 1 --delay-max 3 --url "https://www.rumah123.com/jual/jawa-barat/rumah/"
```
- --pages: jumlah halaman yang ingin di-scrape (default: 1, perhalaman ada sekitar 20 data)
- --delay-min / --delay-max: delay antar request (dalam detik)
- --url: URL awal yang ingin di-scrape

## 📂 Output
Hasil scraping akan otomatis disimpan di direktori:
. results/scraping_session_<timestamp>/
Termasuk:
- property_links.txt
- rumah123_properties_final.csv
- property_specifications_summary.csv
- scraping.log

## ⚠️ Disclaimer
- Hanya untuk penggunaan edukatif/non-komersial.
- Harap hormati terms of service dari situs sumber (Rumah123).
