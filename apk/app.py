import sqlite3
import joblib
import pandas as pd
import os
import io
import tempfile
from datetime import datetime
import re
import string
import traceback
from scipy.sparse import hstack

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_file
)

# ── NLP Libraries (lazy init) ──
try:
    import nltk
    from nltk.corpus import stopwords
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    print("⚠️ NLTK/Sastrawi tidak tersedia, fallback ke preprocessing dasar")

app = Flask(__name__)

# =====================================================
# PATH & MODEL CONFIG
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "data_kriminal_processed.csv")

# Model split terpilih: 80:20 (sesuai hasil training di train_all_splits.ipynb)
MODEL_DIR = os.path.join(PROJECT_ROOT, "data", "models", "comparison_2feat_tuned")
SPLIT_NAME = "80_20"
MODEL_PATH = os.path.join(MODEL_DIR, f"model_{SPLIT_NAME}_final.pkl")
VEC_MO_PATH = os.path.join(MODEL_DIR, f"vectorizer_mo_{SPLIT_NAME}_final.pkl")
VEC_BB_PATH = os.path.join(MODEL_DIR, f"vectorizer_bb_{SPLIT_NAME}_final.pkl")

# Load model (MultinomialNB dilatih di atas fitur gabungan hstack([TF-IDF(MO), TF-IDF(BB)]))
model = None
vec_mo = None
vec_bb = None
try:
    if os.path.exists(MODEL_PATH) and os.path.exists(VEC_MO_PATH) and os.path.exists(VEC_BB_PATH):
        model = joblib.load(MODEL_PATH)
        vec_mo = joblib.load(VEC_MO_PATH)
        vec_bb = joblib.load(VEC_BB_PATH)
        print(f"✅ Model + vectorizer (split {SPLIT_NAME}) loaded dari {MODEL_DIR}")
    else:
        missing = [p for p in (MODEL_PATH, VEC_MO_PATH, VEC_BB_PATH) if not os.path.exists(p)]
        print(f"⚠️ File model tidak lengkap, tidak ditemukan: {missing}")
except Exception as e:
    print(f"❌ Error loading model: {e}")

# =====================================================
# NLP RESOURCES (load once)
# =====================================================
_stop_words = None
_stemmer = None
_kamus_dict = None
_KATA_DASAR = None


def _init_nlp_resources():
    """Inisialisasi stopwords, stemmer, dan kamus normalisasi."""
    global _stop_words, _stemmer, _kamus_dict, _KATA_DASAR

    if not NLP_AVAILABLE:
        return

    # --- Stopwords ---
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)

    stop_words = set(stopwords.words('indonesian'))
    important_words = {
        'korban', 'pelaku', 'tersangka', 'terlapor',
        'penganiayaan', 'pencurian', 'pemerkosaan', 'kekerasan'
    }
    _stop_words = stop_words - important_words

    # --- Stemmer ---
    factory = StemmerFactory()
    _stemmer = factory.create_stemmer()

    # --- Kata dasar yang tidak di-stem ---
    _KATA_DASAR = {
        'pelaku', 'petugas', 'tersangka', 'terlapor', 'pemilik',
        'penjual', 'menguras', 'pembeli', 'penumpang', 'perusakan',
        'pengemudi', 'penghuni', 'pengunjung', 'kiriman', 'tabungan',
        'masakan', 'bawaan', 'titipan', 'pakaian', 'laporan',
        'tertuduh', 'terdakwa', 'keseluruhan', 'kebanyakan', 'belur'
    }

    # --- Kamus Normalisasi ---
    kamus_path = os.path.join(PROJECT_ROOT, "data", "raw", "kamuskatabaku.xlsx")
    if os.path.exists(kamus_path):
        try:
            kamus_df = pd.read_excel(kamus_path)
            kamus_df = kamus_df[kamus_df['tidak_baku'] != 'tidak_baku'].reset_index(drop=True)
            kamus_df['tidak_baku'] = (
                kamus_df['tidak_baku']
                .astype(str)
                .str.lower()
                .str.strip()
            )
            kamus_df['kata_baku'] = (
                kamus_df['kata_baku']
                .astype(str)
                .str.lower()
                .str.strip()
            )
            _kamus_dict = dict(zip(kamus_df['tidak_baku'], kamus_df['kata_baku']))
            print(f"✅ Kamus normalisasi loaded: {len(_kamus_dict)} entri")
        except Exception as e:
            print(f"⚠️ Error loading kamus: {e}")
            _kamus_dict = {}
    else:
        print(f"⚠️ Kamus tidak ditemukan: {kamus_path}")
        _kamus_dict = {}


_init_nlp_resources()

# =====================================================
# DATABASE
# =====================================================

DB_PATH = os.path.join(BASE_DIR, "kasus.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kasus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_laporan TEXT,
            tgl_laporan TEXT,
            perkara TEXT,
            pelapor TEXT,
            terlapor TEXT,
            tkp TEXT,
            desa TEXT,
            barang_bukti TEXT,
            mo TEXT,
            mo_final_text TEXT,
            bb_final_text TEXT,
            proses TEXT,
            ket TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrasi ringan: tambahkan kolom bb_final_text jika DB lama belum punya
    cursor.execute("PRAGMA table_info(kasus)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "bb_final_text" not in existing_cols:
        cursor.execute("ALTER TABLE kasus ADD COLUMN bb_final_text TEXT")

    conn.commit()
    conn.close()

init_db()

# =====================================================
# HELPER ROMAWI BULAN
# =====================================================

ROMAWI = {
    1: "I", 2: "II", 3: "III", 4: "IV",
    5: "V", 6: "VI", 7: "VII", 8: "VIII",
    9: "IX", 10: "X", 11: "XI", 12: "XII"
}

# =====================================================
# HOME
# =====================================================

@app.route("/")
def index():
    return render_template("index.html")

# =====================================================
# PREPROCESSING TEXT (mirrors training pipeline)
# =====================================================

def preprocess(text):
    """
    Pipeline preprocessing lengkap:
    1. Cleaning        – hapus angka, tanda baca, karakter aneh
    2. Case Folding    – lowercase
    3. Normalisasi     – tidak baku → baku (via kamus)
    4. Tokenisasi      – split unigram
    5. Stopword Removal– hapus stopword + kata ≤2 huruf
    6. Stemming        – Sastrawi (kecuali KATA_DASAR)
    """
    if not text or pd.isna(text) or str(text).strip() == "":
        return ""

    text = str(text)

    # 1. Cleaning
    text = re.sub(r'\d+', ' ', text)
    text = re.sub(rf"[{re.escape(string.punctuation)}]", " ", text)
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    # 2. Case Folding
    text = text.lower().strip()

    # 3. Normalisasi
    if _kamus_dict and text:
        words = text.split()
        words = [_kamus_dict.get(word, word) for word in words]
        text = ' '.join(words)

    # 4. Tokenisasi
    tokens = text.split()
    if not tokens:
        return ""

    # 5. Stopword Removal
    if _stop_words is not None:
        tokens = [w for w in tokens if w not in _stop_words and len(w) > 2]

    # 6. Stemming
    if _stemmer is not None and _KATA_DASAR is not None:
        stemmed = []
        for token in tokens:
            if token in _KATA_DASAR:
                stemmed.append(token)
            else:
                stemmed.append(_stemmer.stem(token))
        tokens = stemmed

    return ' '.join(tokens)

# =====================================================
# PREDICT API
# =====================================================

@app.route("/api/predict", methods=["POST"])
def predict():
    if model is None or vec_mo is None or vec_bb is None:
        return jsonify({
            "success": False,
            "error": "Model ML belum tersedia. Hubungi admin."
        }), 503

    try:
        data = request.get_json()
        if not data or "mo" not in data:
            return jsonify({
                "success": False,
                "error": "Field 'mo' wajib diisi"
            }), 400

        mo = data.get("mo", "")
        barang_bukti = data.get("barang_bukti", "")
        clean_mo = preprocess(mo)
        clean_bb = preprocess(barang_bukti)

        if not clean_mo:
            return jsonify({
                "success": False,
                "error": "MO tidak valid setelah preprocessing"
            }), 400

        X_mo = vec_mo.transform([clean_mo])
        X_bb = vec_bb.transform([clean_bb])
        X = hstack([X_mo, X_bb])

        pred = model.predict(X)[0]
        proba = model.predict_proba(X)[0]
        classes = model.classes_

        scores = {
            classes[i]: round(float(proba[i]) * 100, 2)
            for i in range(len(classes))
        }

        return jsonify({
            "success": True,
            "prediction": pred,
            "confidence": max(scores.values()),
            "scores": scores,
            "method": "naive-bayes"
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =====================================================
# GENERATE NOMOR LP (ANTI RACE CONDITION)
# =====================================================

@app.route("/api/generate-lp")
def generate_lp():
    conn = get_db()
    cursor = conn.cursor()

    # Gunakan lastrowid untuk anti-race condition
    cursor.execute("INSERT INTO kasus (no_laporan) VALUES (?)", ("TEMP",))
    new_id = cursor.lastrowid
    cursor.execute("DELETE FROM kasus WHERE id = ?", (new_id,))
    conn.commit()
    conn.close()

    now = datetime.now()
    bulan_romawi = ROMAWI.get(now.month, "I")
    tahun = now.year

    no_lp = (
        f"LP/B/{new_id:02d}/"
        f"{bulan_romawi}/"
        f"{tahun}/"
        f"Kalbar/Res Mpw/Sek Sui Pinyuh"
    )

    return jsonify({
        "success": True,
        "no_lp": no_lp
    })

# =====================================================
# SIMPAN KASUS
# =====================================================

@app.route("/api/save-case", methods=["POST"])
def save_case():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Data JSON tidak valid"
            }), 400

        # barang_bukti tidak wajib
        required = ["no_lp", "tgl_laporan", "tkp", "desa", 
                   "pelapor", "terlapor", "mo", "proses", "ket"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Field wajib kurang: {', '.join(missing)}"
            }), 400

        mo = data.get("mo", "")
        barang_bukti_in = data.get("barang_bukti", "")
        clean_mo = preprocess(mo)
        clean_bb = preprocess(barang_bukti_in)

        prediction = "Unknown"
        confidence = 0.0
        scores = {}

        if model is not None and vec_mo is not None and vec_bb is not None and clean_mo:
            try:
                X_mo = vec_mo.transform([clean_mo])
                X_bb = vec_bb.transform([clean_bb])
                X = hstack([X_mo, X_bb])

                pred = model.predict(X)[0]
                proba = model.predict_proba(X)[0]
                classes = model.classes_
                scores = {
                    classes[i]: round(float(proba[i]) * 100, 2)
                    for i in range(len(classes))
                }
                prediction = pred
                confidence = float(max(proba)) * 100
            except Exception as e:
                print(f"Prediksi error: {e}")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO kasus (
                no_laporan, tgl_laporan, perkara, pelapor, terlapor,
                tkp, desa, barang_bukti, mo, mo_final_text, bb_final_text,
                proses, ket, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["no_lp"],
            data["tgl_laporan"],
            prediction,
            data["pelapor"],
            data["terlapor"],
            data["tkp"],
            data["desa"],
            barang_bukti_in,
            data["mo"],
            clean_mo,
            clean_bb,
            data["proses"],
            data["ket"],
            confidence
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "scores": scores
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =====================================================
# STATISTIK (DARI DATA TRAINING CSV — BUKAN DATABASE)
# =====================================================

@app.route("/api/statistics")
def statistics():
    try:
        # Selalu baca dari DATA_PATH (CSV training), bukan dari database
        if not os.path.exists(DATA_PATH):
            return jsonify({
                "success": False,
                "error": f"File data tidak ditemukan: {DATA_PATH}"
            }), 404

        df = pd.read_csv(DATA_PATH)
        total_cases = len(df)

        # Distribusi perkara
        case_types = {}
        if "PERKARA" in df.columns:
            case_types = df["PERKARA"].value_counts().to_dict()

        # Ambil tahun dari kolom TGL_LAPORAN
        years = []
        start_year = datetime.now().year
        end_year = datetime.now().year
        trend_data = {}

        if "TGL_LAPORAN" in df.columns:
            df["TAHUN"] = df["TGL_LAPORAN"].astype(str).str.extract(r"(\d{4})")[0]
            df["TAHUN"] = pd.to_numeric(df["TAHUN"], errors="coerce")
            years = sorted(df["TAHUN"].dropna().unique().astype(int).tolist())
            start_year = years[0] if years else datetime.now().year
            end_year = years[-1] if years else datetime.now().year

            for tahun in years:
                subset = df[df["TAHUN"] == tahun]
                if "PERKARA" in subset.columns:
                    trend_data[str(tahun)] = subset["PERKARA"].value_counts().to_dict()

        return jsonify({
            "success": True,
            "statistics": {
                "total_cases": total_cases,
                "case_types": case_types,
                "trend_data": trend_data,
                "total_years": len(years),
                "start_year": start_year,
                "end_year": end_year
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =====================================================
# HISTORY (LIST + DETAIL)
# =====================================================

@app.route("/api/history")
def history():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 20

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM kasus WHERE no_laporan != 'TEMP'")
        total = cursor.fetchone()[0]
        pages = max(1, (total + per_page - 1) // per_page)

        offset = (page - 1) * per_page

        cursor.execute("""
            SELECT id, no_laporan, tgl_laporan, tkp, desa,
                   pelapor, terlapor, barang_bukti, mo,
                   proses, ket, perkara, confidence, created_at
            FROM kasus
            WHERE no_laporan != 'TEMP'
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "id": row["id"],
                "no_lp": row["no_laporan"],
                "tgl_laporan": row["tgl_laporan"],
                "pelapor": row["pelapor"],
                "terlapor": row["terlapor"],
                "tkp": row["tkp"],
                "desa": row["desa"],
                "barang_bukti": row["barang_bukti"],
                "mo": row["mo"],
                "proses": row["proses"],
                "ket": row["ket"],
                "prediction": row["perkara"],
                "confidence": row["confidence"],
                "waktu": row["created_at"]
            })

        return jsonify({
            "success": True,
            "history": history,
            "pages": pages,
            "total": total
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Endpoint detail by ID
@app.route("/api/history/<int:id>")
def get_history_detail(id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, no_laporan, tgl_laporan, tkp, desa,
                   pelapor, terlapor, barang_bukti, mo,
                   proses, ket, perkara, confidence, created_at
            FROM kasus
            WHERE id = ? AND no_laporan != 'TEMP'
        """, (id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({
                "success": False,
                "error": "Record tidak ditemukan"
            }), 404

        return jsonify({
            "success": True,
            "data": {
                "id": row["id"],
                "no_lp": row["no_laporan"],
                "tgl_laporan": row["tgl_laporan"],
                "pelapor": row["pelapor"],
                "terlapor": row["terlapor"],
                "tkp": row["tkp"],
                "desa": row["desa"],
                "barang_bukti": row["barang_bukti"],
                "mo": row["mo"],
                "proses": row["proses"],
                "ket": row["ket"],
                "prediction": row["perkara"],
                "confidence": row["confidence"],
                "waktu": row["created_at"]
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/history/<int:id>", methods=["DELETE"])
def delete_history(id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kasus WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history/clear", methods=["DELETE"])
def clear_history():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kasus WHERE no_laporan != 'TEMP'")
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# =====================================================
# EXPORT CSV (STREAMING, TIDAK MENINGGALKAN FILE)
# =====================================================

@app.route("/api/export")
def export_csv():
    try:
        conn = get_db()
        df = pd.read_sql_query(
            "SELECT * FROM kasus WHERE no_laporan != 'TEMP'", conn
        )
        conn.close()

        # Gunakan BytesIO, tidak meninggalkan file di disk
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)

        return send_file(
            output,
            mimetype="text/csv",
            as_attachment=True,
            download_name="history_kasus.csv"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)