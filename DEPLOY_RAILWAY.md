# Deploy ke Railway

## 1. Struktur repo yang dibutuhkan

`app.py` membaca file model dan data lewat `PROJECT_ROOT` (folder **induk** dari `apk/`).
Jadi struktur repo Git Anda harus seperti ini (root repo = `Criminal_Case_Classification`):

```
Criminal_Case_Classification/      ← root repo Git
├── apk/
│   ├── app.py
│   ├── templates/index.html
│   └── static/
│       ├── js/app.js
│       └── css/style.css
├── data/
│   ├── raw/kamuskatabaku.xlsx
│   ├── processed/data_kriminal_processed.csv
│   └── models/comparison_2feat_tuned/
│       ├── model_80_20_final.pkl
│       ├── vectorizer_mo_80_20_final.pkl
│       └── vectorizer_bb_80_20_final.pkl
├── requirements.txt
├── Procfile
├── runtime.txt
└── .gitignore
```

**Penting:** taruh `requirements.txt`, `Procfile`, `runtime.txt`, `.gitignore` di **root** repo (sejajar dengan `apk/` dan `data/`), bukan di dalam `apk/`.

## 2. Push ke GitHub

```bash
cd "Criminal_Case_Classification"
git init
git add .
git commit -m "Deploy siap Railway"
git branch -M main
git remote add origin https://github.com/USERNAME/NAMA_REPO.git
git push -u origin main
```

Kalau file model `.pkl` totalnya besar (>100MB per file), GitHub akan menolak push biasa — pakai [Git LFS](https://git-lfs.github.com/) untuk file di `data/models/`.

## 3. Deploy di Railway

1. Buka [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pilih repo Anda.
2. Railway otomatis mendeteksi `requirements.txt` dan `Procfile` (via Nixpacks) — tidak perlu setting Root Directory karena `Procfile` sudah `cd apk` sendiri.
3. Setelah build selesai, buka tab **Settings → Networking** → klik **Generate Domain** untuk dapat URL publik.

## 4. Tambahkan Volume untuk `kasus.db` (supaya data tidak hilang tiap redeploy)

1. Di project Railway → tab **Volumes** → **New Volume**.
2. Mount path: `/app/apk` (folder tempat `kasus.db` dibuat).
3. Redeploy service. Sekarang `kasus.db` akan tetap ada meski Anda push update kode baru.

## 5. Set environment variable (opsional tapi disarankan)

Di tab **Variables**, tambahkan:

```
FLASK_DEBUG=false
```

Supaya mode debug Flask mati di production (lebih aman — debug mode aktif = orang bisa lihat traceback + eksekusi kode lewat debugger).

## 6. Test

Buka domain yang di-generate Railway, coba submit form klasifikasi kasus seperti biasa. Cek log di tab **Deployments → View Logs** kalau ada error — akan muncul pesan yang sama seperti di terminal lokal Anda (`✅ Model + vectorizer (split 80_20) loaded...`).
