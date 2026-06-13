import sqlite3
import joblib
import pandas as pd
import os
import io
import tempfile
from datetime import datetime
import re
import traceback

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_file
)

app = Flask(__name__)

# =====================================================
# PATH & MODEL CONFIG
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "data_kriminal_processed.csv")
MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "models", "model_pipeline.pkl")

# Load model
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"✅ Model loaded: {MODEL_PATH}")
    else:
        print(f"⚠️ Model not found at: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Error loading model: {e}")

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
            proses TEXT,
            ket TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
# PREPROCESSING TEXT
# =====================================================

def preprocess(text):
    if not text:
        return ""
    text = str(text).lower()
    # Jangan hapus angka (penting untuk tahun, plat, dsb)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# =====================================================
# PREDICT API
# =====================================================

@app.route("/api/predict", methods=["POST"])
def predict():
    if model is None:
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
        clean_mo = preprocess(mo)

        if not clean_mo:
            return jsonify({
                "success": False,
                "error": "MO tidak valid setelah preprocessing"
            }), 400

        pred = model.predict([clean_mo])[0]
        proba = model.predict_proba([clean_mo])[0]
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
        clean_mo = preprocess(mo)

        prediction = "Unknown"
        confidence = 0.0
        scores = {}

        if model is not None and clean_mo:
            try:
                pred = model.predict([clean_mo])[0]
                proba = model.predict_proba([clean_mo])[0]
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
                tkp, desa, barang_bukti, mo, mo_final_text,
                proses, ket, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["no_lp"],
            data["tgl_laporan"],
            prediction,
            data["pelapor"],
            data["terlapor"],
            data["tkp"],
            data["desa"],
            data.get("barang_bukti", ""),
            data["mo"],
            clean_mo,
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
    app.run(debug=True)