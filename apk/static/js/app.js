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
// HEADER STATS
// ═══════════════════════════════════════════════════════════════════════════
async function loadHeaderStats() {
  try {
    const resp = await fetch("/api/statistics");
    const data = await resp.json();

    if (!data.success) return;

    const stats = data.statistics;

    document.getElementById("badgeKasus").textContent =
      `${stats.total_cases} Kasus Terdata`;

    document.getElementById("badgePerkara").textContent =
      `${Object.keys(stats.case_types).length} Jenis Perkara`;

    document.getElementById("badgeTahun").textContent =
      `${stats.start_year}–${stats.end_year}`;
  } catch (err) {
    console.error("loadHeaderStats error:", err);
  }
}

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
// FORM KLASIFIKASI
// ═══════════════════════════════════════════════════════════════════════════

const moInput = document.getElementById("mo");

// Counter karakter MO
moInput.addEventListener("input", () => {
  document.getElementById("charCount").textContent =
    `${moInput.value.length} / 3000`;
});

// ═══════════════════════════════════════════════════════════════════════════
// INISIALISASI FORM
// ═══════════════════════════════════════════════════════════════════════════

async function initForm() {
  try {
    const resp = await fetch("/api/generate-lp");
    const data = await resp.json();

    if (data.success) {
      document.getElementById("noLp").value = data.no_lp;
    }

    // Set tanggal hari ini
    document.getElementById("tglLp").value = new Date()
      .toISOString()
      .split("T")[0];
  } catch (err) {
    console.error("Gagal generate nomor LP", err);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// VALIDASI FORM
// ═══════════════════════════════════════════════════════════════════════════
function validateForm() {
  const fields = {
    "Nomor LP": document.getElementById("noLp").value.trim(),
    "Tanggal Laporan": document.getElementById("tglLp").value,
    "Tempat Kejadian": document.getElementById("tkp").value.trim(),
    Desa: document.getElementById("desa").value,
    Pelapor: document.getElementById("pelapor").value.trim(),
    Terlapor: document.getElementById("terlapor").value.trim(),
    "Modus Operandi": document.getElementById("mo").value.trim(),
    Proses: document.getElementById("proses").value,
    Keterangan: document.getElementById("ket").value,
  };

  const empty = Object.entries(fields)
    .filter(([_, val]) => !val)
    .map(([key, _]) => key);

  if (empty.length > 0) {
    toast(`Field wajib belum diisi: ${empty.join(", ")}`, "err");
    return false;
  }
  return true;
}

// ═══════════════════════════════════════════════════════════════════════════
// PREDICT API
// ═══════════════════════════════════════════════════════════════════════════
async function predictCase() {
  try {
    const mo = document.getElementById("mo").value.trim();
    const barang_bukti = document.getElementById("barangBukti").value.trim();

    const resp = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mo, barang_bukti }),
    });

    const data = await resp.json();
    return data;
  } catch (err) {
    console.error("Predict error:", err);
    return { success: false, error: "Gagal terhubung ke server" };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// SIMPAN DATABASE
// ═══════════════════════════════════════════════════════════════════════════
async function saveCase(result) {
  const payload = {
    no_lp: document.getElementById("noLp").value.trim(),
    tgl_laporan: document.getElementById("tglLp").value,
    tkp: document.getElementById("tkp").value.trim(),
    desa: document.getElementById("desa").value,
    pelapor: document.getElementById("pelapor").value.trim(),
    terlapor: document.getElementById("terlapor").value.trim(),
    barang_bukti: document.getElementById("barangBukti").value.trim(),
    mo: document.getElementById("mo").value.trim(),
    proses: document.getElementById("proses").value,
    ket: document.getElementById("ket").value,
  };

  const resp = await fetch("/api/save-case", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return await resp.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// KLASIFIKASI UTAMA
// ═══════════════════════════════════════════════════════════════════════════
async function classifyCase() {
  if (!validateForm()) return;

  const btn = document.getElementById("btnKlasifikasi");

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Memproses...';

  try {
    const result = await predictCase();

    if (!result || !result.success) {
      toast(result?.error || "Gagal melakukan prediksi", "err");
      return;
    }

    renderResult(result);

    const saveResp = await saveCase(result);
    console.log("SAVE RESPONSE:", saveResp);

    if (saveResp.success) {
      toast("Data berhasil disimpan", "ok");
      loadHistory(1);
      loadHeaderStats();
      loadStats(true);
    } else {
      toast("Gagal menyimpan data: " + (saveResp.error || ""), "err");
    }
  } catch (err) {
    console.error(err);
    toast("Gagal terhubung ke server", "err");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🔍 Proses & Simpan Kasus";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// TAMPILKAN HASIL
// ═══════════════════════════════════════════════════════════════════════════
function renderResult(result) {
  document.getElementById("emptyState").style.display = "none";

  const box = document.getElementById("resultBox");
  box.style.display = "block";

  const color = COLORS[result.prediction] || "#888";
  box.style.borderColor = color;

  // Label Prediksi
  document.getElementById("predictionLabel").innerHTML = `
    <div style="
      background:${color}22;
      border:2px solid ${color};
      color:${color};
      border-radius:10px;
      padding:16px 20px;
      font-size:1.3em;
      font-weight:bold;
      text-align:center;
    ">
      ${result.prediction}
    </div>
  `;

  // Confidence
  const confVal =
    typeof result.confidence === "number"
      ? result.confidence.toFixed(2)
      : result.confidence;
  document.getElementById("confidenceText").textContent =
    `Confidence: ${confVal}%`;

  // Method Badge
  const badge = document.getElementById("methodBadge");
  badge.textContent =
    result.method === "naive-bayes" ? "🤖 Naive Bayes" : "📏 Rule Based";
  badge.className =
    "method-badge " +
    (result.method === "naive-bayes" ? "method-nb" : "method-rule");

  // Confidence Bars (top 5)
  const scores = result.scores || {};
  const sortedScores = Object.entries(scores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  let bars = "";
  sortedScores.forEach(([perkara, score]) => {
    const barColor = COLORS[perkara] || "#888";
    bars += `
      <div class="bar-label">
        <span>${perkara}</span>
        <span>${score}%</span>
      </div>
      <div class="conf-track">
        <div
          class="conf-fill"
          style="width:${score}%; background:${barColor}"
        >
          ${score > 12 ? score + "%" : ""}
        </div>
      </div>
    `;
  });

  document.getElementById("confidenceBars").innerHTML = bars;

  // Semua kelas
  let grid = "";
  Object.entries(scores)
    .sort((a, b) => b[1] - a[1])
    .forEach(([perkara, score]) => {
      grid += `
        <div class="score-item">
          <span style="color:${COLORS[perkara] || "#888"}">${perkara}</span>
          <span class="score-val">${score}%</span>
        </div>
      `;
    });

  document.getElementById("scoreGrid").innerHTML = grid;

  // Rekomendasi
  document.getElementById("recBox").innerHTML = `
    <strong>💡 Rekomendasi Penanganan</strong><br>
    ${RECS[result.prediction] || "Lakukan penyelidikan sesuai SOP."}
  `;
}

// ═══════════════════════════════════════════════════════════════════════════
// RESET FORM
// ═══════════════════════════════════════════════════════════════════════════
function resetForm() {
  ["tkp", "pelapor", "terlapor", "mo", "barangBukti"].forEach((id) => {
    document.getElementById(id).value = "";
  });

  document.getElementById("desa").selectedIndex = 0;
  document.getElementById("proses").selectedIndex = 0;
  document.getElementById("ket").selectedIndex = 0;

  document.getElementById("charCount").textContent = "0 / 3000";

  document.getElementById("resultBox").style.display = "none";
  document.getElementById("emptyState").style.display = "block";

  initForm();
}

// ═══════════════════════════════════════════════════════════════════════════
// STATISTIK
// ═══════════════════════════════════════════════════════════════════════════
let chartInstances = {};

async function loadStats(force = false) {
  if (chartsBuilt && !force) return;

  try {
    const resp = await fetch("/api/statistics");
    const data = await resp.json();

    if (!data.success) {
      console.error("Gagal memuat statistik:", data.error);
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

    // 🔥 Perbaikan: destroy chart lama sebelum buat baru
    ["perkaraChart", "topPerkaraChart", "trendChart"].forEach((id) => {
      const canvas = document.getElementById(id);
      if (canvas && chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
      }
    });

    // Doughnut Chart
    chartInstances["perkaraChart"] = new Chart(
      document.getElementById("perkaraChart"),
      {
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
              labels: { color: "#ccc", padding: 12 },
            },
          },
        },
      },
    );

    // Top 5 Perkara
    chartInstances["topPerkaraChart"] = new Chart(
      document.getElementById("topPerkaraChart"),
      {
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
          plugins: { legend: { display: false } },
        },
      },
    );

    // Tren Perkara per Tahun
    const years = Object.keys(stats.trend_data).sort(
      (a, b) => parseInt(a) - parseInt(b),
    );
    const topCases = labels.slice(0, 5);

    chartInstances["trendChart"] = new Chart(
      document.getElementById("trendChart"),
      {
        type: "line",
        data: {
          labels: years,
          datasets: topCases.map((perkara) => ({
            label: perkara,
            data: years.map((tahun) => stats.trend_data[tahun]?.[perkara] || 0),
            borderColor: COLORS[perkara] || "#888",
            backgroundColor: (COLORS[perkara] || "#888") + "33",
            tension: 0.4,
            fill: true,
          })),
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: "#ccc" } } },
          scales: {
            x: { ticks: { color: "#ccc" } },
            y: { ticks: { color: "#ccc" } },
          },
        },
      },
    );

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
    const tbody = document.getElementById("historyBody");
    tbody.innerHTML = `
      <tr>
        <td colspan="14" style="text-align:center;color:#555;padding:30px">
          <span class="spinner"></span> Memuat riwayat…
        </td>
      </tr>
    `;

    const resp = await fetch(`/api/history?page=${page}`);
    const data = await resp.json();

    if (!data.success) {
      tbody.innerHTML = `
        <tr>
          <td colspan="14" style="text-align:center;color:#ff6b6b;padding:30px">
            ❌ Gagal memuat riwayat: ${data.error || "Unknown error"}
          </td>
        </tr>
      `;
      return;
    }

    const rows = data.history || [];
    const pages = data.pages || 1;

    const totalEl = document.getElementById("historyTotal");
    if (totalEl) totalEl.textContent = data.total ?? rows.length;

    if (!rows.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="14" style="text-align:center;color:#555;padding:28px">
            Belum ada riwayat klasifikasi
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = rows
        .map(
          (r, index) => `
            <tr>
              <td>${(page - 1) * 20 + index + 1}</td>
              <td>${r.no_lp || "-"}</td>
              <td>${r.tgl_laporan || "-"}</td>
              <td>
                <span class="tag" style="background:${COLORS[r.prediction] || "#888"}22;color:${COLORS[r.prediction] || "#888"};border:1px solid ${COLORS[r.prediction] || "#888"}">
                  ${r.prediction || "-"}
                </span>
              </td>
              <td>${r.pelapor || "-"}</td>
              <td>${r.terlapor || "-"}</td>
              <td>${r.tkp || "-"}</td>
              <td>${r.desa || "-"}</td>
              <td style="max-width:150px;white-space:normal;font-size:0.85em;">${r.barang_bukti || "-"}</td>
              <td style="max-width:250px;white-space:normal;font-size:0.85em;">${r.mo || "-"}</td>
              <td>${r.proses || "-"}</td>
              <td>${r.ket || "-"}</td>
              <td><strong>${r.confidence ? r.confidence.toFixed(2) + "%" : "0%"}</strong></td>
              <td>
                <div style="display:flex;gap:5px">
                  <button class="btn btn-secondary" onclick="viewRecord(${r.id})" style="padding:4px 8px;font-size:0.8em;">Lihat</button>
                  <button class="btn btn-danger" onclick="deleteRecord(${r.id})" style="padding:4px 8px;font-size:0.8em;">Hapus</button>
                </div>
              </td>
            </tr>
          `,
        )
        .join("");
    }

    // Pagination
    const pag = document.getElementById("pagination");
    pag.innerHTML = "";
    if (pages > 1) {
      for (let i = 1; i <= pages; i++) {
        const b = document.createElement("button");
        b.className = "page-btn" + (i === page ? " active" : "");
        b.textContent = i;
        b.onclick = () => loadHistory(i);
        pag.appendChild(b);
      }
    }
  } catch (err) {
    console.error("loadHistory error:", err);
    document.getElementById("historyBody").innerHTML = `
      <tr>
        <td colspan="14" style="text-align:center;color:#ff6b6b;padding:30px">
          ❌ Gagal memuat riwayat
        </td>
      </tr>
    `;
  }
}

// 🔥 Perbaikan: fetch detail by ID, tidak fetch semua history
async function viewRecord(id) {
  try {
    const resp = await fetch(`/api/history/${id}`);
    const data = await resp.json();

    if (!data.success || !data.data) {
      toast("Record tidak ditemukan", "err");
      return;
    }

    const rec = data.data;

    // Isi form
    document.getElementById("mo").value = rec.mo || "";
    document.getElementById("noLp").value = rec.no_lp || "";
    document.getElementById("tglLp").value = rec.tgl_laporan || "";
    document.getElementById("tkp").value = rec.tkp || "";
    document.getElementById("desa").value = rec.desa || "";
    document.getElementById("pelapor").value = rec.pelapor || "";
    document.getElementById("terlapor").value = rec.terlapor || "";
    document.getElementById("barangBukti").value = rec.barang_bukti || "";
    document.getElementById("proses").value = rec.proses || "";
    document.getElementById("ket").value = rec.ket || "";

    document.getElementById("charCount").textContent =
      `${(rec.mo || "").length} / 3000`;

    // Pindah ke tab klasifikasi
    document
      .querySelectorAll(".tab")
      .forEach((t) => t.classList.remove("active"));
    document
      .querySelectorAll(".tab-content")
      .forEach((t) => t.classList.remove("active"));
    document.querySelector('[data-tab="klasifikasi"]').classList.add("active");
    document.getElementById("tab-klasifikasi").classList.add("active");

    // Render hasil
    renderResult({
      prediction: rec.prediction,
      confidence: rec.confidence,
      scores: rec.scores || {},
      method: "naive-bayes",
    });
  } catch (err) {
    console.error("viewRecord error:", err);
    toast("Gagal memuat record", "err");
  }
}

async function deleteRecord(id) {
  if (!confirm("Hapus record ini?")) return;
  try {
    const resp = await fetch(`/api/history/${id}`, { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
      loadHistory(1);
      loadHeaderStats();
      loadStats(true);
      toast("Record dihapus", "ok");
    } else {
      toast("Gagal menghapus: " + (data.error || ""), "err");
    }
  } catch (err) {
    toast("Gagal menghapus record", "err");
  }
}

async function clearHistory() {
  if (!confirm("Hapus SEMUA riwayat? Tindakan ini tidak dapat dibatalkan."))
    return;
  try {
    const resp = await fetch("/api/history/clear", { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
      loadHistory(1);
      loadHeaderStats();
      loadStats(true);
      toast("Semua riwayat dihapus", "ok");
    } else {
      toast("Gagal menghapus: " + (data.error || ""), "err");
    }
  } catch (err) {
    toast("Gagal menghapus riwayat", "err");
  }
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
  initForm();
  loadHeaderStats();
  loadHistory(1);

  // 🔥 Perbaikan: auto-load stats jika tab statistik aktif secara default
  const statTab = document.getElementById("tab-statistik");
  if (statTab && statTab.classList.contains("active")) {
    loadStats();
  }
});
