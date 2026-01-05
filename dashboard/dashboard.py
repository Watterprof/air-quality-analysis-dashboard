import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Air Quality Dashboard — Public View (Internal Dataset)",
    page_icon="🌫️",
    layout="wide",
)

# =========================================================
# STYLES (fix KPI text visibility + nicer cards)
# =========================================================
st.markdown(
    """
<style>
/* App background */
.stApp {
  background: radial-gradient(1000px 500px at 20% 0%, rgba(74, 144, 226, 0.18), transparent 55%),
              radial-gradient(900px 450px at 80% 10%, rgba(255, 64, 129, 0.12), transparent 55%),
              #0b0f16;
  color: #e9eef6;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
  border-right: 1px solid rgba(255,255,255,0.06);
}

/* Headings */
h1, h2, h3 {
  letter-spacing: 0.2px;
}

/* Card */
.card {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 18px 40px rgba(0,0,0,0.35);
}

/* KPI Title */
.kpi-title {
  font-size: 0.9rem;
  opacity: 0.9;
  margin-bottom: 6px;
}

/* KPI Value (fix white/too faint issue) */
.kpi-value {
  font-size: 2.0rem;
  font-weight: 800;
  color: #ffffff !important;
  text-shadow: 0 1px 0 rgba(0,0,0,0.35);
  line-height: 1.15;
}

/* KPI Sub */
.kpi-sub {
  font-size: 0.85rem;
  opacity: 0.85;
  margin-top: 6px;
}

/* Badge */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
  font-size: 0.85rem;
  opacity: 0.95;
}

/* Divider */
.hr {
  height: 1px;
  background: rgba(255,255,255,0.10);
  margin: 16px 0;
}

/* Small note */
.small-note {
  font-size: 0.85rem;
  opacity: 0.85;
}

/* Plotly tweak */
.js-plotly-plot .plotly .main-svg {
  border-radius: 16px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# DATA LOADING (robust path)
# =========================================================
@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # standardize columns
    df.columns = [c.strip() for c in df.columns]

    # required columns
    if "datetime" not in df.columns:
        raise ValueError("Kolom 'datetime' tidak ditemukan di CSV. Pastikan hasil cleaning sudah membuat kolom datetime.")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"])
    df = df.sort_values(["station", "datetime"]).reset_index(drop=True)

    return df


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "main_data.csv")

if not os.path.exists(DEFAULT_CSV):
    st.error(
        "File CSV tidak ditemukan.\n\n"
        "Pastikan file `main_data.csv` berada di folder yang sama dengan `dashboard.py`:\n"
        f"- {DEFAULT_CSV}"
    )
    st.stop()

df = load_data(DEFAULT_CSV)

# =========================================================
# CONSTANTS
# =========================================================
POLLUTANTS = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"]
UNIT_MAP = {
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "SO2": "µg/m³",
    "NO2": "µg/m³",
    "CO": "µg/m³",   # dataset kamu biasanya mg/m³ atau µg/m³, tapi kita jangan klaim eksternal
    "O3": "µg/m³",
}

GLOSSARY = {
    "PM2.5": "Partikel sangat halus (≤2.5 µm). Bisa masuk jauh ke paru-paru. Nilai lebih tinggi = umumnya kualitas udara lebih buruk.",
    "PM10":  "Partikel halus (≤10 µm). Lebih besar dari PM2.5. Nilai lebih tinggi = umumnya kualitas udara lebih buruk.",
    "SO2":   "Sulfur dioksida (gas). Umumnya dari pembakaran bahan bakar fosil/industri.",
    "NO2":   "Nitrogen dioksida (gas). Umumnya terkait emisi kendaraan/industri.",
    "CO":    "Karbon monoksida (gas). Umumnya dari pembakaran tidak sempurna.",
    "O3":    "Ozon di permukaan (gas). Terbentuk dari reaksi fotokimia (bukan ozon stratosfer).",
}

# NOTE: kategori ini dibuat INTERNAL (bukan AQI luar), hanya untuk memudahkan pembacaan dashboard.
# Kita pakai kuantil internal per polutan (berdasarkan seluruh dataset / filter terpilih).
CATEGORY_LABELS = ["Terbaik", "Lebih Baik", "Sedang", "Lebih Buruk", "Terburuk"]


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def format_num(x, decimals=1):
    x = safe_float(x)
    if np.isnan(x):
        return "—"
    return f"{x:.{decimals}f}"


def get_quantile_category(values: pd.Series, v: float) -> str:
    """Kategori INTERNAL berdasarkan kuantil (20%, 40%, 60%, 80%)."""
    values = values.dropna()
    if values.empty or np.isnan(v):
        return "—"
    qs = values.quantile([0.2, 0.4, 0.6, 0.8]).values
    if v <= qs[0]:
        return CATEGORY_LABELS[0]
    if v <= qs[1]:
        return CATEGORY_LABELS[1]
    if v <= qs[2]:
        return CATEGORY_LABELS[2]
    if v <= qs[3]:
        return CATEGORY_LABELS[3]
    return CATEGORY_LABELS[4]


def get_rank_info(mean_by_station: pd.Series, station_name: str):
    """Ranking INTERNAL: semakin kecil mean -> semakin baik."""
    s = mean_by_station.dropna().sort_values(ascending=True)
    if station_name not in s.index:
        return None
    rank = int(np.where(s.index == station_name)[0][0]) + 1
    total = len(s)
    percentile = 100 * (1 - (rank - 1) / max(total - 1, 1))  # rank 1 => 100%
    return rank, total, percentile


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
# 🌫️ Air Quality Dashboard — Public View  
<span class="small-note">Dashboard ini **murni berbasis dataset internal** (tanpa standar eksternal seperti WHO/EPA/IQAir).  
Semua label “baik/buruk” pada dashboard adalah **relatif antar stasiun di dataset ini**.</span>
""",
    unsafe_allow_html=True,
)
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =========================================================
# SIDEBAR FILTERS
# =========================================================
with st.sidebar:
    st.markdown("## ⚙️ Filter")

    stations = sorted(df["station"].dropna().unique().tolist())
    default_station = [stations[0]] if stations else []
    selected_stations = st.multiselect("Pilih stasiun", stations, default=default_station)

    min_dt = df["datetime"].min()
    max_dt = df["datetime"].max()
    date_range = st.date_input(
        "Rentang tanggal",
        value=(min_dt.date(), max_dt.date()),
        min_value=min_dt.date(),
        max_value=max_dt.date(),
    )

    pollutant = st.selectbox("Pilih polutan utama", POLLUTANTS, index=0)

    st.markdown("### 📈 Resolusi tren")
    resolution = st.radio("Resolusi tren", ["Harian", "Mingguan", "Bulanan"], index=0, label_visibility="collapsed")

    st.markdown("### ℹ️ Info Polutan")
    st.caption(GLOSSARY.get(pollutant, ""))

    with st.expander("📘 Kamus Polutan (klik)"):
        for k in POLLUTANTS:
            st.markdown(f"**{k}** — {GLOSSARY[k]}")

# guard empty station selection
if not selected_stations:
    st.warning("Pilih minimal 1 stasiun di sidebar.")
    st.stop()

start_date, end_date = date_range
start_ts = pd.to_datetime(start_date)
end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

dff = df[
    (df["station"].isin(selected_stations)) &
    (df["datetime"].between(start_ts, end_ts))
].copy()

if dff.empty:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

unit = UNIT_MAP.get(pollutant, "")

# =========================================================
# STATUS BASIS (average only by request)
# =========================================================
st.markdown(
    """
<div class="badge">✅ Status pada dashboard ini dihitung dari: <b>Rata-rata (periode terpilih)</b> &nbsp; • &nbsp; <span class="small-note">relatif antar stasiun</span></div>
""",
    unsafe_allow_html=True,
)

# =========================================================
# KPI ROW
# =========================================================
# For KPI, we use:
# - latest value per selected stations (mean of latest per station)
# - mean value over period (all rows)
# - min/max over period
# - relative rank based on station mean (if single station selected)
latest_per_station = (
    dff.sort_values("datetime")
       .groupby("station")[pollutant]
       .tail(1)
)
latest_value = latest_per_station.mean() if not latest_per_station.empty else np.nan
mean_value = dff[pollutant].mean()
min_value = dff[pollutant].min()
max_value = dff[pollutant].max()

# Relative status: if single station, rank vs all stations in same time range (internal)
rank_badge_text = None
status_label = None
status_note = None

# compute mean by station for this time filter (but across ALL stations available in df for fairness)
df_time = df[df["datetime"].between(start_ts, end_ts)].copy()
mean_by_station = df_time.groupby("station")[pollutant].mean()

if len(selected_stations) == 1:
    st_name = selected_stations[0]
    info = get_rank_info(mean_by_station, st_name)
    if info:
        r, total, pct = info
        # map rank to internal category label (quintiles by rank)
        # rank 1 best -> "Terbaik"
        frac = (r - 1) / max(total - 1, 1)  # 0..1
        bucket = int(np.floor(frac * 5))
        bucket = min(max(bucket, 0), 4)
        status_label = CATEGORY_LABELS[bucket]
        rank_badge_text = f"Peringkat {r}/{total} (≈{pct:.0f} persentil terbaik)"
        status_note = "Ini perbandingan relatif antar stasiun dalam dataset, bukan standar eksternal."
else:
    # if multiple stations selected, show category based on internal quantile of mean values
    # use mean across selected stations (their mean per station averaged)
    sel_mean = dff.groupby("station")[pollutant].mean().mean()
    status_label = get_quantile_category(mean_by_station, sel_mean)
    rank_badge_text = "Multi-stasiun: status ditentukan relatif dari distribusi stasiun (internal)."
    status_note = "Untuk ranking spesifik, pilih 1 stasiun."

c1, c2, c3, c4 = st.columns([1.15, 1.0, 1.0, 1.25], gap="large")

with c1:
    st.markdown(
        f"""
<div class="card">
  <div class="kpi-title">🧪 {pollutant} Terbaru (rata-rata nilai terakhir stasiun terpilih)</div>
  <div class="kpi-value">{format_num(latest_value, 1)}</div>
  <div class="kpi-sub">Satuan: <b>{unit}</b> • Basis: nilai terakhir per stasiun</div>
</div>
""",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
<div class="card">
  <div class="kpi-title">📊 Rata-rata {pollutant}</div>
  <div class="kpi-value">{format_num(mean_value, 1)}</div>
  <div class="kpi-sub">Periode terpilih • Satuan: <b>{unit}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
<div class="card">
  <div class="kpi-title">↕️ Min / Max {pollutant}</div>
  <div class="kpi-value">{format_num(min_value, 1)} / {format_num(max_value, 1)}</div>
  <div class="kpi-sub">Periode terpilih • Satuan: <b>{unit}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
<div class="card">
  <div class="kpi-title">🏷️ Status Relatif (Internal Dataset)</div>
  <div class="kpi-value">{status_label if status_label else "—"}</div>
  <div class="kpi-sub"><b>{rank_badge_text}</b><br/><span class="small-note">{status_note}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =========================================================
# SECTION: TREND
# =========================================================
st.markdown("## 📉 Tren Polutan")
st.markdown(
    f"<span class='small-note'>Apa yang ditampilkan: perubahan <b>{pollutant}</b> sepanjang waktu pada stasiun & rentang tanggal yang dipilih. "
    f"Nilai lebih tinggi = kondisi relatif lebih buruk (khususnya untuk PM2.5/PM10).</span>",
    unsafe_allow_html=True,
)

# resample
freq = {"Harian": "D", "Mingguan": "W", "Bulanan": "M"}[resolution]
tmp = dff[["datetime", "station", pollutant]].dropna().copy()
tmp = tmp.set_index("datetime")

trend = (
    tmp.groupby("station")[pollutant]
       .resample(freq)
       .mean()
       .reset_index()
       .rename(columns={pollutant: "value"})
)

fig_trend = px.line(
    trend,
    x="datetime",
    y="value",
    color="station",
    markers=False,
    labels={"datetime": "Waktu", "value": f"{pollutant} ({unit})", "station": "Stasiun"},
    title=f"Tren {pollutant} ({resolution})",
)
fig_trend.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=60, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.02)",
    font=dict(color="#E9EEF6"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_trend, use_container_width=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =========================================================
# SECTION: DAILY PATTERN + CATEGORY DISTRIBUTION
# =========================================================
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("## 🕒 Pola Harian (Rata-rata per Jam)")
    st.markdown(
        "<span class='small-note'>Menunjukkan jam-jam mana yang cenderung lebih tinggi/rendah (rata-rata) pada periode & stasiun terpilih.</span>",
        unsafe_allow_html=True,
    )
    if "hour" in dff.columns:
        hourly = dff.groupby("hour")[pollutant].mean().reset_index()
    else:
        hourly = dff.assign(hour=dff["datetime"].dt.hour).groupby("hour")[pollutant].mean().reset_index()

    fig_hour = px.line(
        hourly,
        x="hour",
        y=pollutant,
        markers=True,
        labels={"hour": "Jam", pollutant: f"{pollutant} ({unit})"},
        title=f"Rata-rata {pollutant} per Jam",
    )
    fig_hour.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#E9EEF6"),
    )
    st.plotly_chart(fig_hour, use_container_width=True)

with right:
    st.markdown("## 🧩 Distribusi Kategori (Internal)")
    st.markdown(
        "<span class='small-note'>Kategori dibuat dari <b>kuantil internal</b> (bukan standar luar). "
        "Tujuannya hanya memudahkan pembacaan proporsi kondisi relatif.</span>",
        unsafe_allow_html=True,
    )

    # internal categories based on quantiles of ALL station means in selected time window
    # -> apply to rows of selected subset for proportion
    # threshold computed from entire df_time distribution of the pollutant (more stable)
    values_ref = df_time[pollutant].dropna()

    # define bins by quantiles (5 bins)
    if values_ref.empty:
        st.info("Data referensi kosong untuk membuat kategori.")
    else:
        q = values_ref.quantile([0, 0.2, 0.4, 0.6, 0.8, 1.0]).values
        q = np.unique(q)
        if len(q) < 3:
            st.info("Variasi data terlalu kecil untuk membentuk kategori.")
        else:
            labels = CATEGORY_LABELS[: max(len(q) - 1, 1)]
            cats = pd.cut(dff[pollutant], bins=q, labels=labels, include_lowest=True)
            prop = cats.value_counts(normalize=True).reindex(labels, fill_value=0).reset_index()
            prop.columns = ["Kategori", "Proporsi"]

            fig_cat = px.bar(
                prop,
                x="Kategori",
                y="Proporsi",
                labels={"Proporsi": "Proporsi", "Kategori": "Kategori"},
                title=f"Proporsi Kategori {pollutant} (Periode & Stasiun Terpilih)",
            )
            fig_cat.update_layout(
                height=380,
                margin=dict(l=10, r=10, t=60, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.02)",
                font=dict(color="#E9EEF6"),
                yaxis=dict(tickformat=".0%"),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =========================================================
# SECTION: HEATMAP (Month vs Hour) for PM2.5 only (or selected pollutant)
# =========================================================
st.markdown("## 🧩 Heatmap (Bulan vs Jam) — Pola Musiman + Harian")
st.markdown(
    "<span class='small-note'>Heatmap ini membantu melihat pola gabungan: "
    "<b>bulan</b> mana yang cenderung tinggi, dan <b>jam</b> mana yang cenderung tinggi, pada filter yang dipilih. "
    "Warna lebih terang = nilai rata-rata lebih tinggi (relatif lebih buruk).</span>",
    unsafe_allow_html=True,
)

tmp2 = dff[["datetime", pollutant]].dropna().copy()
tmp2["month"] = tmp2["datetime"].dt.month
tmp2["hour"] = tmp2["datetime"].dt.hour

pivot = tmp2.pivot_table(index="month", columns="hour", values=pollutant, aggfunc="mean").sort_index()

fig_heat = px.imshow(
    pivot,
    labels=dict(x="Jam", y="Bulan", color=f"{pollutant} ({unit})"),
    title=f"Heatmap Rata-rata {pollutant} (Bulan vs Jam)",
    aspect="auto",
)
fig_heat.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=60, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E9EEF6"),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =========================================================
# SECTION: RANKING STATIONS (fix jumbo bar when only 1 station)
# =========================================================
st.markdown("## 🏁 Ranking Stasiun (Relatif Internal)")
st.markdown(
    "<span class='small-note'>Ranking dihitung dari <b>rata-rata periode terpilih</b>. Semakin kecil rata-rata → semakin baik (lebih sehat secara relatif).</span>",
    unsafe_allow_html=True,
)

rank_df = (
    df_time.groupby("station")[pollutant].mean()
    .sort_values(ascending=True)  # best first
    .reset_index()
    .rename(columns={pollutant: f"Rata-rata {pollutant}"})
)
rank_df["Peringkat (1=terbaik)"] = np.arange(1, len(rank_df) + 1)

if len(selected_stations) == 1:
    st_name = selected_stations[0]
    row = rank_df[rank_df["station"] == st_name]
    if not row.empty:
        r = int(row["Peringkat (1=terbaik)"].iloc[0])
        total = len(rank_df)
        mean_val = row[f"Rata-rata {pollutant}"].iloc[0]
        pct = 100 * (1 - (r - 1) / max(total - 1, 1))

        # show compact indicator instead of jumbo bar
        fig_ind = go.Figure(
            go.Indicator(
                mode="number+gauge",
                value=mean_val,
                number={"suffix": f" {unit}", "font": {"color": "white", "size": 38}},
                title={"text": f"Rata-rata {pollutant} — {st_name}<br><span style='font-size:14px;opacity:0.85'>Peringkat {r}/{total} (≈{pct:.0f} persentil terbaik)</span>"},
                gauge={
                    "axis": {"visible": False},
                    "bar": {"color": "rgba(255,255,255,0.55)"},
                    "bgcolor": "rgba(255,255,255,0.07)",
                },
            )
        )
        fig_ind.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=80, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E9EEF6"),
        )
        st.plotly_chart(fig_ind, use_container_width=True)

        with st.expander("📄 Lihat tabel ranking lengkap"):
            st.dataframe(rank_df, use_container_width=True, hide_index=True)
    else:
        st.info("Stasiun tidak ditemukan dalam ranking (cek data/filter).")
else:
    # multiple station selection -> show horizontal ranking bar (compact)
    rank_df_show = rank_df.copy()
    rank_df_show["Kelompok Terpilih"] = rank_df_show["station"].isin(selected_stations)

    fig_rank = px.bar(
        rank_df_show.sort_values(f"Rata-rata {pollutant}", ascending=True),
        x=f"Rata-rata {pollutant}",
        y="station",
        orientation="h",
        labels={f"Rata-rata {pollutant}": f"Rata-rata {pollutant} ({unit})", "station": "Stasiun"},
        title=f"Perbandingan Rata-rata {pollutant} Antar Stasiun (periode terpilih)",
    )
    fig_rank.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#E9EEF6"),
        yaxis=dict(categoryorder="total ascending"),
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    with st.expander("📄 Lihat data ranking & unduh"):
        st.dataframe(rank_df, use_container_width=True, hide_index=True)
        csv = rank_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download ranking (CSV)", data=csv, file_name="ranking_station.csv", mime="text/csv")

# =========================================================
# FOOTER NOTE
# =========================================================
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.markdown(
    """
<span class="small-note">
<b>Catatan penting:</b> Dashboard ini menggunakan kategori & status <b>relatif internal</b>.
Jika kamu butuh “sehat absolut”, itu harus pakai standar eksternal (WHO/EPA/IQAir) — tapi sesuai request kamu, ini sengaja tidak digunakan.
</span>
""",
    unsafe_allow_html=True,
)
