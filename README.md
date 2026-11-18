# MyQuakeQuake — QuakeReady Seismic Data Observatory

Aplikasi Streamlit untuk eksplorasi katalog gempa BMKG 1998–2024 dan penyajian hasil penelitian Hybrid ST-GNN dari Google Colab. Susunan proyek dipisah menjadi `core/`, `modules/`, `assets/`, `data/`, dan `test/`.

## Struktur folder

```text
MyQuakeQuake/
├── assets/style.css
├── core/
│   ├── analysis.py
│   ├── data_preprocessing.py
│   ├── data_storage.py
│   ├── data_validation.py
│   └── visualization.py
├── data/
│   ├── BMKG_Clean_Final.csv
│   ├── QuakeReady_Historis_1998_2024.csv
│   ├── QuakeReady_Klasifikasi_Tahunan_1998_2024.csv
│   └── STGNN_Analysis_2025.csv
├── modules/
│   ├── data_library.py
│   ├── earthquake_explorer.py
│   ├── knowledge_center.py
│   ├── outlook_2025.py
│   ├── overview.py
│   ├── seismic_map.py
│   ├── statistical_atlas.py
│   └── stgnn_research.py
├── test/
│   ├── test_core.py
│   ├── test_dataset_store.py
│   └── test_snapshot.py
├── .streamlit/config.toml
├── app.py
├── README.md
├── requirements.txt
└── pytest.ini
```

## Delapan halaman dan seluruh fitur utama

1. **Overview** — ringkasan data, kartu statistik, tren historis, magnitudo/kedalaman, hotspot, konteks notebook, akses cepat, dan unggah katalog.
2. **Earthquake Explorer** — filter tahun, tanggal, magnitudo, kedalaman, jenis magnitudo, sumber, koordinat, pencarian ID/grid, tabel kejadian, pemilihan baris, peta kejadian terpilih, interpretasi otomatis, dan ekspor CSV.
3. **Seismic Map** — peta Folium, grid 1° × 1°, hotspot historis, cluster embedding, kelas aktivitas tahunan, heatmap, marker episenter, pencarian radius Haversine, daftar kejadian terdekat, serta interpretasi filter.
4. **Statistical Atlas** — tren tahunan, distribusi magnitudo/kedalaman, pola bulanan, jam UTC, globe ortografik interaktif, perbandingan periode, interpretasi, dan ekspor.
5. **ST-GNN Research** — peringkat hotspot historis, interpretasi embedding cluster, distribusi kelas per tahun, serta evaluasi model test 2021–2024 dari notebook.
6. **Knowledge Center** — tujuh topik edukasi dan literasi data gempa; tanpa kuis/gamifikasi.
7. **2025 Outlook** — peta, tabel, dan peringkat proyeksi ST-GNN 2025; bukan kejadian aktual atau peringatan dini.
8. **Data Library** — upload empat CSV, validasi, penyimpanan permanen, registry SHA-256, status dataset, penggantian atomik, hapus dengan konfirmasi, koneksi antardataset, dan audit konsistensi.

## Dataset

Empat CSV penelitian disertakan di folder `data/`. File dapat diganti melalui Data Library setelah hasil Google Colab diperbarui:
- `BMKG_Clean_Final.csv` — katalog kejadian.
- `QuakeReady_Historis_1998_2024.csv` — ringkasan historis 810 grid.
- `QuakeReady_Klasifikasi_Tahunan_1998_2024.csv` — kelas aktivitas tahunan.
- `STGNN_Analysis_2025.csv` — keluaran proyeksi 2025 (opsional).

## Menjalankan di Windows

1. Ekstrak ZIP ke folder permanen.
2. Pastikan Python 3.11 atau 3.12 tersedia.
3. Klik dua kali `jalankan_windows.bat`.

Alternatif PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Buka `http://localhost:8501`.

## Pengujian

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```

## Prinsip interpretasi

- Website membaca CSV hasil preprocessing dan keluaran model; tidak melatih ulang ST-GNN.
- Tidak ada data kejadian gempa sintetis.
- Pratinjau notebook hanya memuat sepuluh grid yang tercatat, bukan katalog nasional lengkap.
- Kelas aktivitas 0/1/2 mengikuti aturan notebook: 0 kejadian, 1–12 kejadian, dan ≥13 kejadian per grid per tahun; bukan klasifikasi risiko resmi.
- ID cluster K-Means menunjukkan kemiripan embedding, bukan urutan bahaya.
- Hotspot historis 1998–2024 berbeda dari proyeksi model 2025.
- Proyeksi tidak menentukan tanggal, lokasi, atau magnitudo gempa berikutnya dan bukan peringatan dini.
- Jumlah kejadian tercatat perlu dibaca bersama cakupan, kelengkapan, dan perubahan kemampuan pencatatan.

## Penyimpanan dataset

Pada instalasi lokal, file disimpan ke folder `data/`. Metadata registry mencatat jumlah baris valid, ukuran file, waktu simpan UTC, dan SHA-256. Upload divalidasi sebelum file lama diganti secara atomik. File tetap tersedia setelah pindah halaman, refresh, dan restart lokal selama folder proyek dipertahankan.

Pada hosting dengan filesystem sementara, gunakan volume persisten atau object storage/database. Disk lokal tidak menjamin file bertahan setelah redeployment cloud.

## Pengembangan dan kontribusi

Pelajari fungsi setiap modul, lakukan perubahan yang dapat dijelaskan, dan catat pengujian yang benar-benar dijalankan. Jika kode atau desain dari proyek acuan digunakan, jelaskan sumber dan kontribusinya secara jujur sesuai aturan institusi.
