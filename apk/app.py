import pandas as pd

from flask import (
    Flask,
    render_template,
    jsonify
)

app = Flask(__name__)

DATA_PATH = "../data/processed/data_kriminal_processed.csv"


@app.route("/")
def index():
    

    return render_template("index.html")


@app.route("/api/statistics")
def statistics():

    # =====================================================
    # LOAD DATA
    # =====================================================
    df = pd.read_csv(DATA_PATH)

    # =====================================================
    # TOTAL KASUS
    # =====================================================
    total_cases = len(df)

    # =====================================================
    # DISTRIBUSI JENIS PERKARA
    # =====================================================
    case_types = (
        df["PERKARA"]
        .value_counts()
        .to_dict()
    )

    # =====================================================
    # AMBIL TAHUN DARI TGL_LAPORAN
    # Contoh:
    # "1 Januari 2021" -> 2021
    # "10 Februari 2022" -> 2022
    # =====================================================
    df["TAHUN"] = (
        df["TGL_LAPORAN"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    df["TAHUN"] = pd.to_numeric(
        df["TAHUN"],
        errors="coerce"
    )
    
    years = sorted(
        df["TAHUN"]
        .dropna()
        .unique()
    )

    start_year = int(years[0])
    end_year = int(years[-1])

    # =====================================================
    # TREND PER TAHUN
    # =====================================================
    trend_data = {}

    for tahun in sorted(
        df["TAHUN"]
        .dropna()
        .unique()
    ):

        subset = df[df["TAHUN"] == tahun]

        trend_data[str(int(tahun))] = (
            subset["PERKARA"]
            .value_counts()
            .to_dict()
        )

    # =====================================================
    # RESPONSE JSON
    # =====================================================
    return jsonify({
        "success": True,
        "statistics": {
            "total_cases": total_cases,
            "case_types": case_types,
            "trend_data": trend_data,
            "total_years": len(trend_data),
            "start_year": start_year,
            "end_year": end_year,
        }
    })


if __name__ == "__main__":
    app.run(debug=True)