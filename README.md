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

#### 🔧 Argumen Umum

```
python main.py --mode <mode> [opsi lainnya]
```

| Argumen        | Deskripsi                                                                    |
| -------------- | ---------------------------------------------------------------------------- |
| `--mode`       | Mode scraping yang diinginkan: `links`, `details`, atau `both`.              |
| `--start-page` | Halaman awal untuk mulai scraping (default: 1).                              |
| `--pages`      | Jumlah halaman yang ingin di-scrape mulai dari `--start-page`.               |
| `--delay-min`  | Delay minimum antar request (default: 1 detik).                              |
| `--delay-max`  | Delay maksimum antar request (default: 3 detik).                             |
| `--url`        | URL awal properti yang akan di-scrape.                                       |
| `--links-file` | Path ke file `.txt` berisi daftar URL properti (hanya untuk `details` mode). |

### 🔧🧪 Contoh Penggunaan

Link saja

```
python main.py --mode links --pages 10 --url "https://www.rumah123.com/jual/dki-jakarta/rumah/"
```

Detail dari File Link

```
python main.py --mode details --links-file "results/scraping_session_20250517_123456/property_links.txt"
```

Link dan Detail Sekaligus

```
python main.py --mode both --pages 5 --url "https://www.rumah123.com/jual/jawa-barat/rumah/"

```

## 📂 Output

Hasil scraping akan otomatis disimpan di direktori:
. results/scraping*session*<timestamp>/
Termasuk:

- property_links.txt
- rumah123_properties_final.csv
- property_specifications_summary.csv
- scraping.log

## ⚠️ Disclaimer

- Hanya untuk penggunaan edukatif/non-komersial.
- Harap hormati terms of service dari situs sumber (Rumah123).
