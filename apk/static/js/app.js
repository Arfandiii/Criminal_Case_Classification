// ═══════════════════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════════════════
const COLORS = {
  Pencurian: "#ff6b6b",
  Penganiayaan: "#feca57",
  Penipuan: "#48dbfb",
  Perusakan: "#ff9ff3",
  Narkoba: "#54a0ff",
  Penggelapan: "#a29bfe",
  Pengeroyokan: "#00d2d3",
  KDRT: "#ff6348",
  Tipiring: "#5f27cd",
};
const RECS = {
  Pencurian:
    "Lakukan penyelidikan TKP, periksa CCTV, lacak barang bukti. Perhatikan modus spesifik (motor/rumah/toko).",
  Penganiayaan:
    "Segera lakukan visum et repertum, kumpulkan saksi, dokumentasikan luka. Perhatikan motif (hutang/cekcok/cemburu).",
  Penipuan:
    "Kumpulkan bukti transfer/screenshot, lacak rekening pelaku, verifikasi janji yang tidak ditepati.",
  Perusakan:
    "Dokumentasikan kerusakan dengan foto, estimasi nilai kerugian, selidiki motif (dendam/sengketa).",
  Narkoba:
    "Amankan barang bukti sesuai prosedur rantai, kirim ke lab, petakan jaringan distribusi.",
  Penggelapan:
    "Kumpulkan dokumen perjanjian/sewa, lakukan audit keuangan, lacak keberadaan barang/uang.",
  Pengeroyokan:
    "Identifikasi seluruh pelaku, lakukan visum, kumpulkan saksi mata, telusuri motif geng/dendam.",
  KDRT: "Pastikan keselamatan korban, lakukan visum, koordinasi P2TP2A, terapkan UU PKDRT No.23/2004.",
  Tipiring:
    "Proses sesuai prosedur tipiring, koordinasi dengan kejaksaan untuk P-21.",
};

// ═══════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════
let chartsBuilt = false;

document.getElementById("tabBar").addEventListener("click", (e) => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  const name = tab.dataset.tab;

  document
    .querySelectorAll(".tab")
    .forEach((t) => t.classList.remove("active"));
  document
    .querySelectorAll(".tab-content")
    .forEach((t) => t.classList.remove("active"));

  tab.classList.add("active");
  document.getElementById("tab-" + name).classList.add("active");

  if (name === "statistik") loadStats();
  if (name === "riwayat") loadHistory(1);
});

// ═══════════════════════════════════════════════════════════════════════════
// CLASSIFY
// ═══════════════════════════════════════════════════════════════════════════
async function classifyCase() {
  const mo = document.getElementById("mo").value.trim();
  if (!mo) {
    toast("Kolom MO wajib diisi!", "err");
    return;
  }

  const btn = document.getElementById("btnKlasifikasi");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Memproses…';

  try {
    const resp = await fetch("/api/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mo,
        barang_bukti: document.getElementById("barangBukti").value,
        no_lp: document.getElementById("noLp").value,
        tkp: document.getElementById("tkp").value,
        pelapor: document.getElementById("pelapor").value,
        terlapor: document.getElementById("terlapor").value,
        proses: document.getElementById("proses").value,
        ket: document.getElementById("ket").value,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      toast(data.error || "Terjadi kesalahan", "err");
      return;
    }

    // Flask kita mengembalikan {prediction, confidence, scores, method}
    const result = data.success ? data.result : data;
    renderResult(result);
    toast("Klasifikasi berhasil: " + result.prediction, "ok");
  } catch (err) {
    toast("Gagal terhubung ke server", "err");
    console.error(err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🔍 Klasifikasikan";
  }
}

function renderResult(r) {
  document.getElementById("emptyState").style.display = "none";
  const box = document.getElementById("resultBox");
  box.style.display = "block";

  const color = COLORS[r.prediction] || "#888";
  box.style.borderColor = color;

  // Label utama
  document.getElementById("predictionLabel").innerHTML =
    `<div style="background:${color}22;border:2px solid ${color};color:${color};border-radius:10px;padding:16px 20px">${r.prediction}</div>`;

  document.getElementById("confidenceText").textContent =
    `Confidence: ${r.confidence}%`;

  const mb = document.getElementById("methodBadge");
  mb.textContent =
    r.method === "naive-bayes" ? "🤖 Naive Bayes" : "📏 Rule-Based";
  mb.className =
    "method-badge " +
    (r.method === "naive-bayes" ? "method-nb" : "method-rule");

  // Confidence bars (top 5)
  const scores = r.scores || {};
  let bars = "";
  Object.entries(scores)
    .slice(0, 5)
    .forEach(([p, s]) => {
      const c = COLORS[p] || "#888";
      bars += `
        <div class="bar-label"><span>${p}</span><span>${s}%</span></div>
        <div class="conf-track">
            <div class="conf-fill" style="width:${s}%;background:${c}">${s > 12 ? s + "%" : ""}</div>
        </div>`;
    });
  document.getElementById("confidenceBars").innerHTML = bars;

  // Score grid (semua kelas)
  let grid = "";
  Object.entries(scores).forEach(([p, s]) => {
    grid += `<div class="score-item">
        <span style="color:${COLORS[p] || "#888"}">${p}</span>
        <span class="score-val">${s}%</span>
        </div>`;
  });
  document.getElementById("scoreGrid").innerHTML = grid;

  // Rekomendasi
  document.getElementById("recBox").innerHTML =
    `<strong>💡 Rekomendasi Penanganan</strong>${RECS[r.prediction] || "Lakukan penyelidikan sesuai SOP."}`;
}

function resetForm() {
  ["noLp", "tkp", "pelapor", "terlapor", "mo", "barangBukti"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  document.getElementById("proses").selectedIndex = 0;
  document.getElementById("ket").selectedIndex = 0;
  document.getElementById("resultBox").style.display = "none";
  document.getElementById("emptyState").style.display = "block";
}

async function loadHeaderStats() {
  try {
    const resp = await fetch("/api/statistics");
    const data = await resp.json();

    if (!data.success) return;

    const stats = data.statistics;

    document.getElementById("badgeKasus").textContent =
      `📁 ${stats.total_cases} Kasus Terdata`;

    document.getElementById("badgePerkara").textContent =
      `🗂️ ${Object.keys(stats.case_types).length} Jenis Perkara`;

    document.getElementById("badgeTahun").textContent =
      `📅 ${stats.start_year}–${stats.end_year}`;
  } catch (err) {
    console.error(err);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// STATISTIK
// ═══════════════════════════════════════════════════════════════════════════
async function loadStats() {
  if (chartsBuilt) return;

  try {
    const resp = await fetch("/api/statistics");
    const data = await resp.json();

    if (!data.success) {
      console.error("Gagal memuat statistik");
      return;
    }

    const stats = data.statistics;

    // Statistik ringkas
    document.getElementById("totalKasus").textContent =
      stats.total_cases.toLocaleString();

    document.getElementById("totalJenisPerkara").textContent = Object.keys(
      stats.case_types,
    ).length;

    document.getElementById("jumlahTahun").textContent = stats.total_years;

    // Data chart
    const sortedCases = Object.entries(stats.case_types).sort(
      (a, b) => b[1] - a[1],
    );

    const labels = sortedCases.map((item) => item[0]);
    const values = sortedCases.map((item) => item[1]);
    const colors = labels.map((label) => COLORS[label] || "#888");

    // Doughnut Chart
    new Chart(document.getElementById("perkaraChart"), {
      type: "doughnut",
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderWidth: 2,
            borderColor: "#16213e",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: "#ccc",
              padding: 12,
            },
          },
        },
      },
    });

    // Top 5 Perkara
    new Chart(document.getElementById("topPerkaraChart"), {
      type: "bar",
      data: {
        labels: labels.slice(0, 5),
        datasets: [
          {
            label: "Kasus",
            data: values.slice(0, 5),
            backgroundColor: colors.slice(0, 5),
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
        },
      },
    });

    // Tren Perkara per Tahun
    const years = Object.keys(stats.trend_data);
    const topCases = labels.slice(0, 5);

    new Chart(document.getElementById("trendChart"), {
      type: "line",
      data: {
        labels: years,
        datasets: topCases.map((perkara) => ({
          label: perkara,
          data: years.map((tahun) => stats.trend_data[tahun]?.[perkara] || 0),
          borderColor: COLORS[perkara] || "#888",
          tension: 0.4,
          fill: false,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
      },
    });

    chartsBuilt = true;
  } catch (err) {
    console.error("Gagal memuat statistik:", err);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// HISTORY
// ═══════════════════════════════════════════════════════════════════════════
async function loadHistory(page = 1) {
  try {
    const resp = await fetch(`/api/history?page=${page}`);
    const data = await resp.json();

    // Support both {success, history} and {data, total, pages} response shapes
    const rows = data.history || data.data || [];
    const pages = data.pages || 1;

    const tbody = document.getElementById("historyBody");
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="6" style="text-align:center;color:#555;padding:28px">Belum ada riwayat klasifikasi</td></tr>';
    } else {
      tbody.innerHTML = rows
        .map(
          (r) => `
            <tr>
            <td style="white-space:nowrap">${r.waktu || r.time || "-"}</td>
            <td>${r.no_lp || "-"}</td>
            <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                title="${(r.mo || "").replace(/"/g, "&quot;")}">${r.mo ? r.mo.substring(0, 70) + (r.mo.length > 70 ? "…" : "") : "-"}</td>
            <td><span class="tag tag-${r.prediksi || r.prediction}">${r.prediksi || r.prediction || "-"}</span></td>
            <td>${r.confidence}%</td>
            <td>
                <div style="display:flex;gap:5px">
                <button class="btn btn-secondary" style="padding:4px 10px;font-size:.78em" onclick="viewRecord(${r.id})">👁️</button>
                <button class="btn btn-danger"    style="padding:4px 10px;font-size:.78em" onclick="deleteRecord(${r.id})">🗑️</button>
                </div>
            </td>
            </tr>`,
        )
        .join("");
    }

    // Pagination
    const pag = document.getElementById("pagination");
    pag.innerHTML = "";
    for (let i = 1; i <= pages; i++) {
      const b = document.createElement("button");
      b.className = "page-btn" + (i === page ? " active" : "");
      b.textContent = i;
      b.onclick = () => loadHistory(i);
      pag.appendChild(b);
    }
  } catch (err) {
    console.error("loadHistory error:", err);
  }
}

async function viewRecord(id) {
  try {
    const resp = await fetch(`/api/history?page=1`);
    const data = await resp.json();
    const rows = data.history || data.data || [];
    const rec = rows.find((r) => r.id === id);
    if (!rec) return;

    document.getElementById("mo").value = rec.mo || "";
    document.getElementById("noLp").value = rec.no_lp || "";
    document.getElementById("tkp").value = rec.tkp || "";
    document.getElementById("pelapor").value = rec.pelapor || "";
    document.getElementById("terlapor").value = rec.terlapor || "";
    document.getElementById("barangBukti").value = rec.barang_bukti || "";

    // Pindah ke tab klasifikasi
    document
      .querySelectorAll(".tab")
      .forEach((t) => t.classList.remove("active"));
    document
      .querySelectorAll(".tab-content")
      .forEach((t) => t.classList.remove("active"));
    document.querySelector('[data-tab="klasifikasi"]').classList.add("active");
    document.getElementById("tab-klasifikasi").classList.add("active");

    renderResult({
      prediction: rec.prediksi || rec.prediction,
      confidence: rec.confidence,
      scores: rec.scores || {},
      method: "naive-bayes",
    });
  } catch (err) {
    console.error(err);
  }
}

async function deleteRecord(id) {
  if (!confirm("Hapus record ini?")) return;
  await fetch(`/api/history/${id}`, { method: "DELETE" });
  loadHistory(1);
  toast("Record dihapus", "ok");
}

async function clearHistory() {
  if (!confirm("Hapus SEMUA riwayat? Tindakan ini tidak dapat dibatalkan."))
    return;
  await fetch("/api/history/clear", { method: "DELETE" });
  loadHistory(1);
  toast("Semua riwayat dihapus", "ok");
}

function exportCSV() {
  window.location.href = "/api/export";
}

// ═══════════════════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════════════════
let toastTimer;
function toast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = (type === "ok" ? "✅ " : "❌ ") + msg;
  el.className = "show toast-" + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.className = "";
  }, 3200);
}

// ═══════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  loadHeaderStats();
  loadHistory(1);
});
