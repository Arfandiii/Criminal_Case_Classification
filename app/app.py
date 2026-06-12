from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# Rule-based classifier rules (sama seperti di JavaScript)
classifier_rules = {
    "Narkoba": {
        "keywords": [
            "sabu", "ganja", "narkotika", "ekstasi", "pil", "hisap", "bong",
            "transaksi narkoba", "mengkonsumsi", "menimbang sabu", "paket sabu",
            "klip plastik", "timbangan digital", "petugas menyamar", "digeledah",
            "gerak-gerik mencurigakan", "disembunyikan di"
        ],
        "weight": 3.0,
        "color": "#54a0ff",
        "barang_bukti": ["sabu", "ganja", "ekstasi", "pil", "hisap", "bong", "timbangan digital", "klip"],
        "recommendation": "Rekomendasi: Amankan barang bukti dengan prosedur rantai, lakukan pemeriksaan lab, periksa jaringan distribusi."
    },
    "KDRT": {
        "keywords": [
            "istri", "suami", "kekerasan dalam rumah tangga", "menjambak rambut",
            "membenturkan kepala", "menampar pipi", "menendang kaki", "buku nikah",
            "di depan anak", "pertengkaran rumah tangga", "kekerasan fisik terhadap istri",
            "mengancam akan membunuh anak", "mengurung korban", "menahan kartu atm"
        ],
        "weight": 3.0,
        "color": "#ff6348",
        "barang_bukti": ["buku nikah", "visum", "hasil pemeriksaan medis"],
        "recommendation": "Rekomendasi: Pastikan keselamatan korban, lakukan visum, koordinasi dengan P2TP2A, terapkan UU PKDRT No. 23/2004."
    },
    "Pengeroyokan": {
        "keywords": [
            "dikeroyok", "bersama-sama", "dihajar", "dikeroyok oleh", "kawan-kawan",
            "teman-temannya", "sekelompok", "massa", "dikeroyok menggunakan",
            "dipukuli secara bersama-sama", "mengeroyok"
        ],
        "weight": 3.0,
        "color": "#00d2d3",
        "barang_bukti": ["pakaian korban", "visum"],
        "recommendation": "Rekomendasi: Identifikasi seluruh pelaku, lakukan visum, kumpulkan saksi mata, periksa motif geng/dendam."
    },
    "Penggelapan": {
        "keywords": [
            "menyewa", "tidak mengembalikan", "tidak disetorkan", "digunakan untuk kepentingan pribadi",
            "menghilang", "uang hasil penjualan", "tidak diberikan", "menggadaikan",
            "tanpa izin", "audit keuangan", "menitipkan", "dijual", "kwitansi sewa", "faktur pembelian"
        ],
        "weight": 2.5,
        "color": "#5f27cd",
        "barang_bukti": ["audit keuangan", "faktur", "kwitansi sewa", "surat penitipan"],
        "recommendation": "Rekomendasi: Kumpulkan dokumen perjanjian/sewa, periksa audit keuangan, lacak keberadaan barang/uang."
    },
    "Penipuan": {
        "keywords": [
            "menghilang", "fiktif", "menjanjikan", "tidak", "meminjam", "menawarkan",
            "tidak pernah", "black market", "bisnis", "modus penggandaan uang",
            "arisan bodong", "janji", "tidak ditepati", "menipu", "berpura-pura",
            "menjual", "screenshot percakapan", "bukti transfer", "surat perjanjian", "kwitansi"
        ],
        "weight": 2.5,
        "color": "#48dbfb",
        "barang_bukti": ["screenshot", "bukti transfer", "kwitansi", "surat perjanjian"],
        "recommendation": "Rekomendasi: Kumpulkan bukti transfer/screenshot, lacak rekening pelaku, periksa keberadaan barang/jasa yang dijanjikan."
    },
    "Perusakan": {
        "keywords": [
            "merusak", "melempar", "pecah", "memecahkan", "menggores bodi", "merusak pintu",
            "merusak pagar", "merusak kaca", "menyiramkan", "menebang pohon", "merusak tanaman",
            "merusak peralatan", "memotong kabel", "menyobek ban", "mengisi racun"
        ],
        "weight": 2.5,
        "color": "#ff9ff3",
        "barang_bukti": ["pecahan", "foto kerusakan", "batu"],
        "recommendation": "Rekomendasi: Dokumentasikan kerusakan dengan foto, estimasi nilai kerugian, periksa motif (dendam/sengketa/cemburu)."
    },
    "Penganiayaan": {
        "keywords": [
            "memukul", "menendang", "menampar", "melempar", "mendorong", "menganiaya",
            "memukul wajah", "memukul punggung", "menonjok", "melempar asbak",
            "melempar korban", "hasil visum", "tipiring sidang", "luka robek",
            "luka memar", "cekcok mulut"
        ],
        "weight": 2.0,
        "color": "#feca57",
        "barang_bukti": ["visum", "asbak", "helm"],
        "recommendation": "Rekomendasi: Segera lakukan visum et repertum, kumpulkan saksi, dokumentasikan luka korban. Perhatikan motif (hutang/cekcok/cemburu)."
    },
    "Pencurian": {
        "keywords": [
            "mengambil", "membawa lari", "mencuri", "merusak kunci", "motor",
            "memanjat pagar", "mencongkel jendela", "masuk", "menguras isi laci",
            "merusak gembok", "menggasak", "pencurian dengan pemberatan", "merusak pintu"
        ],
        "weight": 2.0,
        "color": "#ff6b6b",
        "barang_bukti": ["motor", "hp", "laptop", "perhiasan", "uang tunai", "tabung gas"],
        "recommendation": "Rekomendasi: Lakukan penyelidikan TKP, periksa CCTV, lacak barang bukti. Perhatikan modus spesifik (pencurian motor/rumah/toko)."
    },
    "Tipiring": {
        "keywords": ["tipiring sidang", "tipiring"],
        "weight": 3.0,
        "color": "#a29bfe",
        "barang_bukti": [],
        "recommendation": "Rekomendasi: Proses sesuai prosedur tipiring, koordinasi dengan kejaksaan untuk P-21."
    }
}

def classify_text(mo_text, barang_bukti_text=""):
    """Fungsi klasifikasi teks MO"""
    if not mo_text or mo_text.strip() == "":
        return {
            "prediction": "Tidak dapat diklasifikasikan",
            "confidence": 0,
            "scores": {}
        }
    
    mo = mo_text.lower()
    bb = barang_bukti_text.lower() if barang_bukti_text else ""
    scores = {}
    
    for perkara, rule in classifier_rules.items():
        score = 0
        # Hitung skor berdasarkan keyword
        for keyword in rule["keywords"]:
            pattern = re.compile(re.escape(keyword.lower()), re.IGNORECASE)
            matches = len(pattern.findall(mo))
            score += matches * rule["weight"]
        
        # Bonus dari barang bukti
        for bb_keyword in rule.get("barang_bukti", []):
            if bb_keyword.lower() in bb:
                score += 1.5
        
        scores[perkara] = score
    
    # Normalisasi skor
    total_score = sum(scores.values())
    normalized_scores = {}
    
    if total_score > 0:
        for k, v in scores.items():
            normalized_scores[k] = round((v / total_score) * 100, 1)
    else:
        for k in scores.keys():
            normalized_scores[k] = 0
    
    # Sort berdasarkan skor
    sorted_scores = dict(sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True))
    prediction = list(sorted_scores.keys())[0] if list(sorted_scores.values())[0] > 0 else "Tidak dapat diklasifikasikan"
    confidence = sorted_scores[prediction] if prediction in sorted_scores else 0
    
    return {
        "prediction": prediction,
        "confidence": confidence,
        "scores": sorted_scores,
        "recommendation": classifier_rules.get(prediction, {}).get("recommendation", "Lakukan penyelidikan sesuai SOP."),
        "color": classifier_rules.get(prediction, {}).get("color", "#666666")
    }

# Data statistik (sama seperti di HTML)
statistics = {
    "total_cases": 1050,
    "case_types": {
        "Pencurian": 280,
        "Penganiayaan": 205,
        "Penipuan": 149,
        "Perusakan": 125,
        "Narkoba": 86,
        "Penggelapan": 84,
        "Pengeroyokan": 68,
        "KDRT": 52,
        "Tipiring": 1
    },
    "trend_data": {
        "2021": {"Pencurian": 120, "Penganiayaan": 80, "Penipuan": 50, "Perusakan": 40, "Narkoba": 25},
        "2022": {"Pencurian": 90, "Penganiayaan": 65, "Penipuan": 45, "Perusakan": 35, "Narkoba": 30},
        "2023": {"Pencurian": 55, "Penganiayaan": 45, "Penipuan": 40, "Perusakan": 35, "Narkoba": 25},
        "2024": {"Pencurian": 15, "Penganiayaan": 15, "Penipuan": 14, "Perusakan": 15, "Narkoba": 6}
    }
}

# Penyimpanan sementara untuk history (di memori)
case_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/classify', methods=['POST'])
def classify():
    """Endpoint untuk klasifikasi kasus"""
    try:
        data = request.json
        mo = data.get('mo', '')
        barang_bukti = data.get('barang_bukti', '')
        
        result = classify_text(mo, barang_bukti)
        
        # Simpan ke history
        history_item = {
            "id": len(case_history) + 1,
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "no_lp": data.get('no_lp', ''),
            "tkp": data.get('tkp', ''),
            "pelapor": data.get('pelapor', ''),
            "terlapor": data.get('terlapor', ''),
            "mo": mo[:100] + ('...' if len(mo) > 100 else ''),
            "mo_full": mo,
            "barang_bukti": barang_bukti,
            "proses": data.get('proses', ''),
            "ket": data.get('ket', ''),
            "prediction": result['prediction'],
            "confidence": result['confidence']
        }
        case_history.insert(0, history_item)
        
        # Hanya simpan 50 history terakhir
        while len(case_history) > 50:
            case_history.pop()
        
        return jsonify({
            "success": True,
            "result": result,
            "history_id": history_item['id']
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/history', methods=['GET'])
def get_history():
    """Endpoint untuk mengambil riwayat klasifikasi"""
    return jsonify({
        "success": True,
        "history": case_history
    })

@app.route('/api/history/<int:history_id>', methods=['GET'])
def get_history_detail(history_id):
    """Endpoint untuk detail riwayat tertentu"""
    item = next((h for h in case_history if h['id'] == history_id), None)
    if item:
        return jsonify({"success": True, "item": item})
    return jsonify({"success": False, "error": "History not found"}), 404

@app.route('/api/history/clear', methods=['DELETE'])
def clear_history():
    """Endpoint untuk menghapus semua riwayat"""
    case_history.clear()
    return jsonify({"success": True, "message": "History cleared"})

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Endpoint untuk mengambil data statistik"""
    return jsonify({
        "success": True,
        "statistics": statistics
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)