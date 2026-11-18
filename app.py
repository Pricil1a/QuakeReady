
"""QuakeReady | Indonesian Seismic Data Observatory."""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import textwrap

from streamlit_folium import st_folium

from core.analysis import (
    annual_counts,
    event_summary,
    catalog_diagnostics,
    compare_periods,
    grid_year_detail,
    top_historic,
    top_projection,
    preview_map,
    NOTEBOOK_COUNTS,
    TEST_METRICS,
)

from core.data_preprocessing import (
    data_source,
    events_clean,
    historic_clean,
    annual_clean,
    projection_clean,
)

from core.data_storage import (
    save_dataset,
    remove_dataset,
    registry,
    file_revision,
    DatasetError,
)

from core.visualization import (
    build_map,
    in_radius,
    distance_km,
    ACTIVITY_NAMES,
    CLUSTER_COLORS,
)

# GRID LOCATION - BIG VERIFIED
from core.grid_location import (
    load_grid_location_mapping as core_load_grid_location_mapping,
    enrich_grid_locations as core_enrich_grid_locations,
    add_event_location as core_add_event_location,
)

from modules import (
    overview,
    earthquake_explorer,
    seismic_map,
    statistical_atlas,
    stgnn_research,
    knowledge_center,
    outlook_2025,
    data_library,
)


# ============================================================
# 1. PROJECT PATH
# ============================================================

ROOT = Path(__file__).resolve().parent

DATA = ROOT / "data"

ASSETS = ROOT / "assets"

MAPPING_FILE = DATA / "grid_location_mapping_BIG_verified.csv"

BOUNDARY_FILE = DATA / "batas_kabupaten_BIG.geojson"


# ============================================================
# 2. NAVIGATION
# ============================================================

NAV = [
    "Overview",
    "Earthquake Explorer",
    "Seismic Map",
    "Statistical Atlas",
    "ST-GNN Research",
    "Knowledge Center",
    "2025 Outlook",
    "Data Library",
]


# ============================================================
# 3. DATASET REGISTRY
# ============================================================

FILE_INFO = {

    "BMKG_Clean_Final.csv": (
        "Katalog kejadian 1998–2024",
        events_clean,
    ),

    "QuakeReady_Historis_1998_2024.csv": (
        "Ringkasan historis 810 grid",
        historic_clean,
    ),

    "QuakeReady_Klasifikasi_Tahunan_1998_2024.csv": (
        "Kelas aktivitas tahunan",
        annual_clean,
    ),

    "STGNN_Analysis_2025.csv": (
        "Proyeksi ST-GNN 2025 (opsional)",
        projection_clean,
    ),
}


# ============================================================
# 4. THEME
# ============================================================

RED = "#AD4248"
DARK = "#20384E"
TEAL = "#3D8385"
GOLD = "#C69A55"
GRID = "#DEE5EC"

PALETTE = [
    RED,
    DARK,
    TEAL,
    GOLD,
    "#9A6B91",
]


# ============================================================
# 5. STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="QuakeReady | Seismic Data Observatory",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 6. LOAD CSS
# ============================================================

style_file = ASSETS / "style.css"

if style_file.exists():

    st.markdown(
        '<style>'
        + style_file.read_text(encoding="utf-8")
        + '</style>',
        unsafe_allow_html=True,
    )

else:

    st.warning(
        "File assets/style.css tidak ditemukan. "
        "Dashboard menggunakan tampilan default."
    )


DATA.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# 7. SESSION STATE
# ============================================================

if "upload_generations" not in st.session_state:

    st.session_state.upload_generations = {}


if "home_upload_generation" not in st.session_state:

    st.session_state.home_upload_generation = 0


if "page" not in st.session_state:

    st.session_state.page = "Overview"


# ============================================================
# 8. LOAD AND CLEAN DATASETS
# ============================================================

@st.cache_data(show_spinner=False)
def read_clean(
    filepath: str,
    cleaner_name: str,
    revision: tuple[int, int] | None,
):

    """
    Cache file-derived data.
    File revision changes whenever a CSV is replaced.
    """

    if revision is None:

        return None

    raw = pd.read_csv(
        filepath,
        low_memory=False,
    )

    return FILE_INFO[cleaner_name][1](raw)


# ============================================================
# 9. UPLOAD DATASET
# ============================================================

def accept_upload(
    filename: str,
    payload: bytes,
    key_kind="library",
):

    """
    Validate and persist a dataset for all pages
    and future local restarts.
    """

    if filename not in FILE_INFO:

        raise ValueError(
            f"Dataset tidak terdaftar: {filename}"
        )

    record = save_dataset(
        DATA,
        filename,
        payload,
        FILE_INFO[filename][1],
    )

    read_clean.clear()

    if key_kind == "library":

        st.session_state.upload_generations[filename] = (
            st.session_state.upload_generations.get(
                filename,
                0,
            ) + 1
        )

    else:

        st.session_state.home_upload_generation += 1

    st.session_state.data_notice = (
        f"{filename} tersimpan permanen pada folder data/ "
        f"({record['validated_rows']:,} baris valid). "
        "Seluruh halaman kini menggunakan file ini."
    )

    st.rerun()


# ============================================================
# 10. LOAD ALL DATASETS
# ============================================================

sources = {}

errors = {}

for filename in FILE_INFO:

    try:

        sources[filename] = read_clean(
            str(DATA / filename),
            filename,
            file_revision(DATA, filename),
        )

    except Exception as exc:

        sources[filename] = None

        errors[filename] = str(exc)


# ============================================================
# 11. ASSIGN DATASETS
# ============================================================

E = sources["BMKG_Clean_Final.csv"]

H = sources["QuakeReady_Historis_1998_2024.csv"]

A = sources["QuakeReady_Klasifikasi_Tahunan_1998_2024.csv"]

P = sources["STGNN_Analysis_2025.csv"]


# ============================================================
# 12. GRID LOCATION MAPPING - BIG VERIFIED
# ============================================================

GRID_LOCATION_COLUMNS = [

    "nama_lokasi",

    "lokasi_grid",

    "center_kabupaten",

    "center_provinsi",

    "kabupaten_kota_tercakup",

    "provinsi_tercakup",

    "kabupaten_dominan",

    "provinsi_dominan",

    "jenis_wilayah",

    "status_pemetaan_lokasi",

    "luas_grid_km2",

    "luas_irisan_total_km2",

    "luas_dominan_km2",

    "persentase_cakupan_polygon",

]


GRID_LOCATION_EXPLANATION = (

    "Nama lokasi merupakan referensi wilayah administratif "
    "berdasarkan polygon BIG. Grid berukuran 1° × 1° dapat "
    "mencakup beberapa kabupaten/kota dan provinsi. "
    "Kabupaten/kota dominan merupakan wilayah dengan irisan "
    "terluas. Informasi ini bukan penetapan lokasi tepat "
    "episenter gempa. Lokasi episenter individual ditentukan "
    "dari koordinat latitude dan longitude."
)


location_mapping_status = {

    "available": False,

    "message": "",

    "grid_count": 0,

    "mapping_rows": 0,

    "datasets": {},

    "blank_location_names": 0,

}


GRID_LOCATION_MAPPING = None

GRID_LOCATION_IDS = set()


# ------------------------------------------------------------
# LOAD LOCATION MAPPING
# ------------------------------------------------------------

def load_location_mapping():

    """
    Load BIG verified mapping.

    File:
        data/grid_location_mapping_BIG_verified.csv

    Expected:
        810 unique grid IDs.
    """

    global GRID_LOCATION_MAPPING
    global GRID_LOCATION_IDS

    mapping = core_load_grid_location_mapping(
        DATA
    )

    if mapping is None or mapping.empty:

        raise ValueError(
            "Mapping BIG kosong atau tidak tersedia."
        )

    if "grid_id" not in mapping.columns:

        raise ValueError(
            "Kolom grid_id tidak ditemukan dalam mapping BIG."
        )

    mapping = mapping.copy()

    mapping["grid_id"] = (
        mapping["grid_id"]
        .astype("string")
        .str.strip()
    )

    if mapping["grid_id"].duplicated().any():

        raise ValueError(
            "Mapping BIG memiliki grid_id duplikat."
        )

    if len(mapping) != 810:

        raise ValueError(
            f"Jumlah mapping seharusnya 810 grid, "
            f"ditemukan {len(mapping)}."
        )

    GRID_LOCATION_MAPPING = mapping

    GRID_LOCATION_IDS = set(
        mapping["grid_id"]
        .dropna()
        .astype(str)
    )

    location_mapping_status["available"] = True

    location_mapping_status["message"] = ""

    location_mapping_status["grid_count"] = int(
        mapping["grid_id"].nunique()
    )

    location_mapping_status["mapping_rows"] = int(
        len(mapping)
    )

    location_mapping_status["blank_location_names"] = int(
        mapping["nama_lokasi"].isna().sum()
        +
        mapping["nama_lokasi"]
        .astype("string")
        .str.strip()
        .eq("")
        .sum()
    )

    return mapping


# ------------------------------------------------------------
# ADD GRID LOCATION
# ------------------------------------------------------------

def add_grid_location(df):

    """
    Add location metadata to a DataFrame.

    Uses core.grid_location.enrich_grid_locations().
    """

    if df is None:

        return None

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input add_grid_location harus berupa DataFrame."
        )

    if "grid_id" not in df.columns:

        return df.copy()

    if GRID_LOCATION_MAPPING is None:

        return df.copy()

    return core_enrich_grid_locations(
        df.copy(),
        mapping=GRID_LOCATION_MAPPING,
    )


# ------------------------------------------------------------
# ADD EXACT EPICENTER LOCATION
# ------------------------------------------------------------

def add_event_location(df):

    """
    Resolve exact earthquake epicenter against BIG polygons.

    This function is optional and is not automatically
    executed for all 217,807 earthquake records at startup.
    """

    return core_add_event_location(
        df,
        data_dir=DATA,
        boundary_file=BOUNDARY_FILE,
    )


# ------------------------------------------------------------
# INTEGRATE LOCATION INTO DATASET
# ------------------------------------------------------------

def integrate_grid_location(
    dataset,
    dataset_name,
):

    """
    Attach BIG grid location metadata.

    Preserves original number of rows.
    """

    if dataset is None:

        location_mapping_status["datasets"][dataset_name] = {

            "status": "Dataset belum tersedia",

            "total_rows": 0,

            "matched_rows": 0,

            "unmatched_rows": 0,

            "total_grids": 0,

            "matched_grids": 0,

            "match_percentage": 0.0,

        }

        return None

    if not isinstance(dataset, pd.DataFrame):

        location_mapping_status["datasets"][dataset_name] = {

            "status": "Dataset bukan DataFrame",

            "total_rows": 0,

            "matched_rows": 0,

            "unmatched_rows": 0,

            "total_grids": 0,

            "matched_grids": 0,

            "match_percentage": 0.0,

        }

        return dataset

    if "grid_id" not in dataset.columns:

        location_mapping_status["datasets"][dataset_name] = {

            "status": "Kolom grid_id tidak tersedia",

            "total_rows": len(dataset),

            "matched_rows": 0,

            "unmatched_rows": len(dataset),

            "total_grids": 0,

            "matched_grids": 0,

            "match_percentage": 0.0,

        }

        return dataset

    if GRID_LOCATION_MAPPING is None:

        location_mapping_status["datasets"][dataset_name] = {

            "status": "Mapping belum tersedia",

            "total_rows": len(dataset),

            "matched_rows": 0,

            "unmatched_rows": len(dataset),

            "total_grids": int(
                dataset["grid_id"].nunique()
            ),

            "matched_grids": 0,

            "match_percentage": 0.0,

        }

        return dataset

    try:

        original_length = len(dataset)

        normalized_ids = (
            dataset["grid_id"]
            .astype("string")
            .str.strip()
        )

        matched_mask = normalized_ids.isin(
            GRID_LOCATION_IDS
        )

        mapped = add_grid_location(
            dataset
        )

        if len(mapped) != original_length:

            raise ValueError(
                "Jumlah baris berubah setelah integrasi lokasi."
            )

        total_rows = int(original_length)

        matched_rows = int(
            matched_mask.sum()
        )

        unmatched_rows = (
            total_rows - matched_rows
        )

        total_grids = int(
            normalized_ids.nunique(dropna=True)
        )

        matched_grids = int(
            normalized_ids[
                matched_mask
            ].nunique(dropna=True)
        )

        percentage = (
            matched_rows / total_rows * 100
            if total_rows > 0
            else 0.0
        )

        location_mapping_status["datasets"][dataset_name] = {

            "status": (
                "Berhasil"
                if unmatched_rows == 0
                else "Sebagian grid belum terpetakan"
            ),

            "total_rows": total_rows,

            "matched_rows": matched_rows,

            "unmatched_rows": unmatched_rows,

            "total_grids": total_grids,

            "matched_grids": matched_grids,

            "match_percentage": percentage,

        }

        print(
            f"[GRID LOCATION] {dataset_name}: "
            f"{matched_rows:,}/{total_rows:,} baris "
            f"({percentage:.2f}%), "
            f"{matched_grids:,}/{total_grids:,} grid terpetakan."
        )

        return mapped

    except Exception as exc:

        location_mapping_status["datasets"][dataset_name] = {

            "status": "Gagal menggabungkan metadata",

            "total_rows": len(dataset),

            "matched_rows": 0,

            "unmatched_rows": len(dataset),

            "total_grids": int(
                dataset["grid_id"].nunique()
            ),

            "matched_grids": 0,

            "match_percentage": 0.0,

            "error": str(exc),

        }

        location_mapping_status["message"] = (
            f"{dataset_name}: {exc}"
        )

        print(
            f"[GRID LOCATION ERROR] {dataset_name}: {exc}"
        )

        return dataset


# ------------------------------------------------------------
# LOAD MAPPING ONCE
# ------------------------------------------------------------

try:

    load_location_mapping()

except Exception as exc:

    location_mapping_status["available"] = False

    location_mapping_status["message"] = str(exc)

    print(
        "[GRID LOCATION ERROR]",
        exc
    )


# ============================================================
# 13. APPLY LOCATION MAPPING TO DATASETS
# ============================================================

if location_mapping_status["available"]:

    E = integrate_grid_location(
        E,
        "BMKG Events",
    )

    H = integrate_grid_location(
        H,
        "Historical Grid",
    )

    A = integrate_grid_location(
        A,
        "Annual Classification",
    )

    P = integrate_grid_location(
        P,
        "ST-GNN Projection",
    )

    # Synchronize shared sources.

    sources["BMKG_Clean_Final.csv"] = E

    sources["QuakeReady_Historis_1998_2024.csv"] = H

    sources["QuakeReady_Klasifikasi_Tahunan_1998_2024.csv"] = A

    sources["STGNN_Analysis_2025.csv"] = P


# ------------------------------------------------------------
# LOCATION VALIDATION REPORT
# ------------------------------------------------------------

print("\n====================================")

print("QUAKEREADY GRID LOCATION VALIDATION")

print("====================================")

print(
    "Mapping tersedia:",
    location_mapping_status["available"],
)

print(
    "File mapping:",
    MAPPING_FILE,
)

print(
    "Jumlah grid mapping:",
    location_mapping_status["grid_count"],
)

print(
    "Jumlah nama lokasi kosong:",
    location_mapping_status["blank_location_names"],
)

for dataset_name, report in (
    location_mapping_status["datasets"].items()
):

    print(f"\n{dataset_name}")

    for key, value in report.items():

        print(f"  {key}: {value}")

print("====================================\n")

# ============================================================
# 14. SHARED UI HELPERS
# ============================================================

def number(value, decimals=0):

    if value is None or pd.isna(value):

        return "—"

    if decimals:

        return f"{value:,.{decimals}f}".replace(",", " ")

    return f"{value:,.0f}".replace(",", ".")


def keyline(label="RESEARCH DATA PLATFORM"):

    st.markdown(
        f'<div class="qr-topline">'
        f'<span class="dot"></span>'
        f'{html.escape(label)}'
        f'</div>',
        unsafe_allow_html=True,
    )


def heading(
    title,
    subtitle,
    kicker="QUAKEREADY / OBSERVATORY",
):

    keyline(kicker)

    st.markdown(
        f'<div class="qr-page-head">'
        f'<h1>{html.escape(title)}</h1>'
        f'<p>{html.escape(subtitle)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section(title, aside=""):

    st.markdown(
        f'<div class="qr-section-title">'
        f'<h2>{html.escape(title)}</h2>'
        f'<span>{html.escape(aside)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def stat(label, value, sub=""):

    st.markdown(
        f'<div class="qr-stat">'
        f'<div class="qr-stat-label">'
        f'{html.escape(str(label))}</div>'
        f'<div class="qr-stat-value">'
        f'{html.escape(str(value))}</div>'
        f'<div class="qr-stat-meta">'
        f'{html.escape(str(sub))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def empty(title, body):

    st.markdown(
        f'<div class="qr-empty">'
        f'<h4>{html.escape(title)}</h4>'
        f'<p>{html.escape(body)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def note(body):

    st.markdown(
        f'<div class="qr-warn">'
        f'{html.escape(body)}'
        f'</div>',
        unsafe_allow_html=True,
    )


def charts(fig, height=350):

    fig.update_layout(
        height=height,
        template="plotly_white",
        font=dict(
            family="Segoe UI, sans-serif",
            color="#34495e",
            size=11,
        ),
        margin=dict(
            t=15,
            b=35,
            l=45,
            r=20,
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=PALETTE,
        hoverlabel=dict(
            bgcolor="white",
            font_color=DARK,
        ),
        xaxis=dict(
            gridcolor="#edf1f5",
            zerolinecolor="#edf1f5",
        ),
        yaxis=dict(
            gridcolor="#edf1f5",
            zerolinecolor="#edf1f5",
        ),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "lasso2d",
                "select2d",
            ],
        },
    )


def download(
    df,
    filename="QuakeReady_Export.csv",
):

    st.download_button(
        "Download filtered CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key="dl_" + filename,
    )


def range_slider(
    df,
    col,
    label,
    key,
    bounds_df=None,
):

    """Keep slider domains stable when other filters change."""

    if df is None or col not in df:

        return df

    domain = (
        bounds_df
        if bounds_df is not None
        else df
    )

    if domain is None or col not in domain or len(domain) == 0:

        return df

    a = float(domain[col].min())

    b = float(domain[col].max())

    if not np.isfinite(a + b) or a >= b:

        return df

    step = (
        .1
        if col in ("latitude", "longitude", "magnitude")
        else 1.
    )

    lo = float(np.floor(a / step) * step)

    hi = float(np.ceil(b / step) * step)

    values = st.slider(
        label,
        min_value=lo,
        max_value=hi,
        value=(lo, hi),
        step=step,
        key=key,
    )

    return df[
        df[col].between(
            values[0],
            values[1],
        )
    ]


def evidence_panel(
    title,
    scope,
    paragraphs,
    footer="",
):

    """Show deterministic, data-derived interpretation."""

    pieces = "".join(
        f"<p>{html.escape(str(line))}</p>"
        for line in paragraphs
        if line
    )

    foot = (
        f'<div class="qr-evidence-foot">'
        f'{html.escape(footer)}</div>'
        if footer
        else ""
    )

    st.markdown(
        f'<section class="qr-evidence">'
        f'<div class="qr-evidence-kicker">'
        f'INTERPRETASI DATA TERPILIH'
        f'</div>'
        f'<h3>{html.escape(title)}</h3>'
        f'<div class="qr-evidence-scope">'
        f'{html.escape(scope)}</div>'
        f'{pieces}{foot}'
        f'</section>',
        unsafe_allow_html=True,
    )


# ============================================================
# 15. EVENT SELECTION INTERPRETATION
# ============================================================

def describe_event_selection(
    selected,
    original,
    description,
):

    """Describe only measurements present in the filtered catalogue."""

    if original is None or len(original) == 0:

        return

    if selected is None or len(selected) == 0:

        evidence_panel(
            "Tidak ada kejadian pada kombinasi filter ini",
            description,
            [
                "Tabel, peta, dan statistik tidak menampilkan kejadian karena tidak ada baris katalog yang memenuhi seluruh batas yang dipilih.",

                "Coba perluas rentang tanggal, magnitudo, atau kedalaman. Tidak adanya catatan pada hasil filter bukan bukti bahwa wilayah tersebut bebas bahaya gempa.",
            ],
            "Sumber: BMKG_Clean_Final.csv; seluruh nilai mengikuti filter saat ini.",
        )

        return

    n = len(selected)

    share = n / len(original) * 100

    med = float(selected.magnitude.median())

    mmax = float(selected.magnitude.max())

    shallow = int(
        (selected.depth_km < 70).sum()
    )

    median_depth = float(
        selected.depth_km.median()
    )

    grid_ct = int(
        selected.grid_id.nunique()
    )

    top_grid = (
        selected.grid_id.value_counts().idxmax()
    )

    top_n = int(
        selected.grid_id.value_counts().iloc[0]
    )

    # Find the administrative coverage name for the most frequent grid.

    top_location = None

    if "nama_lokasi" in selected.columns:

        location_values = (
            selected.loc[
                selected["grid_id"].astype(str) == str(top_grid),
                "nama_lokasi",
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        location_values = location_values[
            location_values.ne("")
        ]

        if not location_values.empty:

            top_location = location_values.iloc[0]

    top_grid_label = (
        f"Grid {top_grid} ({top_location})"
        if top_location
        else f"Grid {top_grid}"
    )

    years = (
        selected.year.value_counts().sort_index()
    )

    top_y = int(years.idxmax())

    top_yn = int(years.max())

    span = (
        f"{int(selected.year.min())}–"
        f"{int(selected.year.max())}"
    )

    paragraphs = [

        f"Terdapat {number(n)} kejadian yang memenuhi kombinasi filter, setara {share:.2f}% dari {number(len(original))} catatan dalam katalog historis yang diunggah. Hasil ini bukan total gempa Indonesia secara resmi.",

        f"Magnitudo median M {med:.1f}, dengan magnitudo terbesar M {mmax:.1f}. Kedalaman median {median_depth:.1f} km; sebanyak {number(shallow)} kejadian ({shallow/n*100:.1f}%) memiliki kedalaman kurang dari 70 km.",

        f"Kejadian yang terseleksi berada pada {number(grid_ct)} grid 1° × 1°. {top_grid_label} mempunyai catatan terbanyak dalam seleksi ini ({number(top_n)} kejadian). Nama wilayah menunjukkan cakupan administratif grid, sedangkan titik episenter individual tetap ditentukan oleh koordinat latitude dan longitude. Titik pada peta bukan prediksi lokasi gempa berikutnya.",

        f"Dalam tahun yang masih terwakili pada seleksi ({span}), catatan paling banyak berada pada {top_y} ({number(top_yn)} kejadian). Perbandingan antarperiode perlu mempertimbangkan perubahan cakupan dan kemampuan pencatatan.",
    ]

    evidence_panel(
        "Apa yang ditunjukkan hasil filter?",
        description,
        paragraphs,
        "Sumber: BMKG_Clean_Final.csv · Hasil diperbarui setiap filter diubah · Frekuensi kejadian tidak sama dengan tingkat risiko bencana.",
    )


# ============================================================
# 16. MAP SELECTION INTERPRETATION
# ============================================================

def describe_map_selection(
    events,
    historical,
    annual,
    mode,
    heat,
    limit,
    circle=None,
):

    """Explain map layers, marker sampling, and radius calculations."""

    messages = []

    if mode == "Hotspot historis":

        messages.append(
            "Warna pada grid menampilkan total kejadian historis 1998–2024. Nilai tersebut tidak berubah ketika filter tahun, magnitudo, atau kedalaman untuk layer episenter diubah."
        )

    elif mode == "Cluster historis":

        messages.append(
            "Warna grid menunjukkan kelompok kemiripan embedding ST-GNN melalui K-Means. Nomor cluster 0, 1, dan 2 bukan tingkatan bahaya atau urutan jumlah gempa."
        )

    elif mode.startswith("Klasifikasi"):

        yr = mode.split()[-1]

        messages.append(
            f"Warna grid menampilkan kategori jumlah kejadian pada {yr}: 0 = tidak tercatat, 1 = 1–12, 2 = minimal 13 kejadian. Ambang tersebut berasal dari penelitian, bukan penilaian risiko resmi."
        )

        if annual is not None:

            sub = annual[
                annual.year == int(yr)
            ]

            counts = (
                sub.activity_class
                .value_counts()
                .reindex(
                    [0, 1, 2],
                    fill_value=0,
                )
            )

            messages.append(
                f"Tahun {yr} memiliki "
                f"{number(int(counts[0]))} grid kelas 0, "
                f"{number(int(counts[1]))} kelas 1, "
                f"dan {number(int(counts[2]))} kelas 2 "
                f"menurut file klasifikasi tahunan."
            )

    if events is not None:

        n = len(events)

        sampled = min(
            n,
            int(limit),
        )

        messages.append(
            f"Filter episenter menghasilkan {number(n)} kejadian; untuk menjaga performa peta menampilkan hingga {number(sampled)} marker sebagai sampel tetap. Jumlah kejadian sebenarnya pada hasil filter tetap {number(n)}."
        )

        if heat:

            messages.append(
                f"Heatmap aktif dan dibuat dari paling banyak {number(min(n, 5000))} catatan terpilih; semakin pekat berarti semakin banyak titik pada visualisasi sampel, bukan otomatis risiko lebih tinggi."
            )

    if circle is not None and events is not None:

        lat, lon, rad = circle

        in_circle = in_radius(
            events,
            lat,
            lon,
            rad,
        )

        messages.append(
            f"Lingkaran radius {number(rad)} km dari koordinat ({lat:.2f}, {lon:.2f}) memuat {number(len(in_circle))} kejadian dari hasil filter ({(len(in_circle)/len(events)*100 if len(events) else 0):.1f}%). Lingkaran adalah alat seleksi spasial; perhitungan ini menggunakan seluruh kejadian terfilter, bukan hanya marker sampel."
        )

    elif circle is None:

        messages.append(
            "Pencarian radius belum diaktifkan. Pilih pusat dan radius lalu centang Aktifkan radius untuk melihat jumlah kejadian di area tersebut."
        )

    evidence_panel(
        "Cara membaca peta setelah pengaturan",
        f"Layer aktif: {mode}",
        messages,
        "Sumber grid: file historis/tahunan · Sumber episenter: BMKG_Clean_Final.csv · Layer dan filter mempunyai dasar data yang berbeda.",
    )


# ============================================================
# 17. YEARLY FIGURE
# ============================================================

def yearly_fig(df):

    yearly = (
        df.groupby(
            "year",
            observed=True,
        )
        .size()
        .rename("events")
        .reset_index()
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=yearly.year,
            y=yearly.events,
            marker_color=RED,
            hovertemplate=(
                "Tahun %{x}<br>"
                "%{y:,} kejadian"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title="Tahun",
        yaxis_title="Jumlah kejadian tercatat",
        bargap=.28,
    )

    return fig


# ============================================================
# 18. HISTOGRAM FIGURE
# ============================================================

def hist_fig(
    df,
    col,
    bins,
    unit,
    color,
):

    values = (
        pd.to_numeric(
            df[col],
            errors="coerce",
        )
        .dropna()
        .to_numpy()
    )

    if len(values) == 0:

        return go.Figure()

    counts, edges = np.histogram(
        values,
        bins=bins,
    )

    centers = (
        edges[:-1] + edges[1:]
    ) / 2

    fig = go.Figure(
        go.Bar(
            x=centers,
            y=counts,
            marker_color=color,
            width=np.diff(edges) * .93,
            hovertemplate=(
                unit
                + ": %{x:.2f}<br>"
                + "Jumlah: %{y:,}"
                + "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title=unit,
        yaxis_title="Jumlah kejadian",
        bargap=.03,
    )

    return fig


def render_sidebar_html(content):

    content = textwrap.dedent(content).strip()

    html_renderer = getattr(st, "html", None)

    if callable(html_renderer):

        html_renderer(content)

    else:

        # Compatibility fallback for older Streamlit
        st.markdown(
            content.replace("\n", " "),
            unsafe_allow_html=True,
        )

# ============================================================
# 19. SIDEBAR - FIXED HTML + CLEAN BRAND + NAVIGATION
# ============================================================

# ------------------------------------------------------------
# SIDEBAR STATE
# ------------------------------------------------------------

if "sidebar_compact" not in st.session_state:

    st.session_state.sidebar_compact = False


def toggle_sidebar_compact():

    st.session_state.sidebar_compact = (
        not st.session_state.get("sidebar_compact", False)
    )


def select_sidebar_page(target):

    st.session_state.page = target


sidebar_compact = bool(
    st.session_state.sidebar_compact
)


# ------------------------------------------------------------
# NAVIGATION ICONS
# ------------------------------------------------------------

NAV_ICONS = {

    "Overview": "⌂",
    "Earthquake Explorer": "◉",
    "Seismic Map": "⌖",
    "Statistical Atlas": "▥",
    "ST-GNN Research": "⌘",
    "Knowledge Center": "ⓘ",
    "2025 Outlook": "↗",
    "Data Library": "▤",

}


# ------------------------------------------------------------
# SIDEBAR CSS
# USE UNIQUE CLASS NAMES TO AVOID OLD CSS CONFLICTS
# ------------------------------------------------------------

sidebar_css = """
<style>

/* ========================================================
   SIDEBAR GENERAL
======================================================== */

section[data-testid="stSidebar"] {

    transition:
        width 0.25s ease,
        min-width 0.25s ease,
        max-width 0.25s ease;

}

/* Hide native collapse button */

[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] button {

    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;

}

/* ========================================================
   BRAND CONTAINER
======================================================== */

.qr-sidebar-brand-new {

    display: flex !important;

    align-items: center !important;

    justify-content: flex-start !important;

    gap: 10px !important;

    width: 100% !important;

    min-width: 0 !important;

    padding: 7px 0 19px 0 !important;

    box-sizing: border-box !important;

}

/* LOGO BOX */

.qr-sidebar-logo-new {

    width: 42px !important;

    height: 42px !important;

    min-width: 42px !important;

    flex: 0 0 42px !important;

    display: flex !important;

    align-items: center !important;

    justify-content: center !important;

    background: #AD4248 !important;

    color: #FFFFFF !important;

    border-radius: 12px !important;

    font-family: Arial, sans-serif !important;

    font-size: 24px !important;

    font-weight: 800 !important;

    line-height: 1 !important;

    text-align: center !important;

    border: none !important;

    margin: 0 !important;

    padding: 0 !important;

    position: static !important;

    transform: none !important;

    box-shadow: 0 3px 10px rgba(0,0,0,.15);

}

/* BRAND TEXT */

.qr-sidebar-brand-copy-new {

    display: flex !important;

    flex-direction: column !important;

    justify-content: center !important;

    align-items: flex-start !important;

    flex: 1 1 auto !important;

    min-width: 0 !important;

    margin: 0 !important;

    padding: 0 !important;

}

/* BRAND NAME */

.qr-sidebar-name-new {

    color: #FFFFFF !important;

    font-family: Arial, sans-serif !important;

    font-size: 19px !important;

    font-weight: 750 !important;

    line-height: 1.2 !important;

    letter-spacing: -.4px !important;

    margin: 0 !important;

    padding: 0 !important;

    white-space: nowrap !important;

}

/* BRAND SUBTITLE */

.qr-sidebar-sub-new {

    color: #B8C8D9 !important;

    font-family: Arial, sans-serif !important;

    font-size: 8px !important;

    font-weight: 600 !important;

    line-height: 1.5 !important;

    letter-spacing: 1px !important;

    margin: 3px 0 0 0 !important;

    padding: 0 !important;

    white-space: nowrap !important;

}

/* ========================================================
   NAVIGATION LABEL
======================================================== */

.qr-sidebar-label-new {

    color: #AFC0D1 !important;

    font-size: 10px !important;

    font-weight: 700 !important;

    letter-spacing: 1.3px !important;

    margin: 8px 0 10px 0 !important;

    padding: 0 !important;

}

/* ========================================================
   DATA STATUS
======================================================== */

.qr-sidebar-status-new {

    color: #FFFFFF !important;

    font-size: 12px !important;

    font-weight: 600 !important;

    background: rgba(255,255,255,.08) !important;

    border: 1px solid rgba(255,255,255,.08);

    border-radius: 8px !important;

    padding: 9px 10px !important;

    margin: 5px 0 10px 0 !important;

}

.qr-sidebar-data-line-new {

    display: flex !important;

    align-items: center !important;

    justify-content: space-between !important;

    gap: 8px !important;

    color: #D9E2EC !important;

    font-size: 10px !important;

    line-height: 1.4 !important;

    padding: 7px 0 !important;

    border-bottom: 1px solid rgba(255,255,255,.09);

}

.qr-sidebar-data-name-new {

    color: #D9E2EC !important;

    flex: 1 1 auto !important;

}

.qr-sidebar-data-state-new {

    font-size: 9px !important;

    font-weight: 700 !important;

    white-space: nowrap !important;

}

/* ========================================================
   FOOTER
======================================================== */

.qr-sidebar-footer-new {

    color: #AFC0D1 !important;

    font-size: 10px !important;

    line-height: 1.7 !important;

    padding: 8px 0 12px 0 !important;

    margin: 0 !important;

}

/* ========================================================
   COMPACT LOGO
======================================================== */

.qr-sidebar-compact-logo-new {

    width: 42px !important;

    height: 42px !important;

    margin: 15px auto 24px auto !important;

}

/* ========================================================
   COMPACT SIDEBAR WIDTH
======================================================== */

"""


if sidebar_compact:

    sidebar_css += """

    section[data-testid="stSidebar"] {

        width: 108px !important;

        min-width: 108px !important;

        max-width: 108px !important;

        flex: 0 0 108px !important;

    }

    section[data-testid="stSidebar"] > div {

        width: 108px !important;

        min-width: 108px !important;

    }

    section[data-testid="stSidebar"]
    [data-testid="stSidebarContent"] {

        padding-left: 8px !important;

        padding-right: 8px !important;

    }

    """


sidebar_css += "\n</style>"

render_sidebar_html(sidebar_css)


# ============================================================
# SIDEBAR CONTENT
# ============================================================

with st.sidebar:

    # ========================================================
    # COMPACT MODE
    # ========================================================

    if sidebar_compact:

        # EXPAND BUTTON

        st.button(
            "»",
            key="sidebar_compact_toggle",
            help="Perbesar sidebar",
            width="stretch",
            on_click=toggle_sidebar_compact,
        )

        # COMPACT LOGO

        render_sidebar_html("""
            <div class="qr-sidebar-logo-new
                        qr-sidebar-compact-logo-new">
                Q
            </div>
        """)

        # ICON NAVIGATION

        for index, nav_item in enumerate(NAV):

            active = (
                st.session_state.get("page")
                == nav_item
            )

            st.button(
                NAV_ICONS.get(nav_item, "•"),
                key=f"sidebar_compact_nav_{index}",
                help=nav_item,
                width="stretch",
                type=(
                    "primary"
                    if active
                    else "secondary"
                ),
                on_click=(
                    lambda target=nav_item:
                    select_sidebar_page(target)
                ),
            )

        st.divider()


    # ========================================================
    # EXPANDED MODE
    # ========================================================

    else:

        # ----------------------------------------------------
        # BRAND AND COLLAPSE BUTTON
        # ----------------------------------------------------

        brand_col, toggle_col = st.columns(
            [5, 1]
        )

        with brand_col:

            render_sidebar_html("""
                <div class="qr-sidebar-brand-new">

                    <div class="qr-sidebar-logo-new">
                        Q
                    </div>

                    <div class="qr-sidebar-brand-copy-new">

                        <div class="qr-sidebar-name-new">
                            QuakeReady
                        </div>

                        <div class="qr-sidebar-sub-new">
                            SEISMIC DATA OBSERVATORY
                        </div>

                    </div>

                </div>
            """)

        with toggle_col:

            st.button(
                "«",
                key="sidebar_compact_toggle",
                help="Ciutkan sidebar menjadi ikon",
                width="stretch",
                on_click=toggle_sidebar_compact,
            )


        # ----------------------------------------------------
        # NAVIGATION LABEL
        # ----------------------------------------------------

        render_sidebar_html("""
            <div class="qr-sidebar-label-new">
                NAVIGASI
            </div>
        """)


        # ----------------------------------------------------
        # ORIGINAL NAVIGATION RADIO
        # ----------------------------------------------------

        st.radio(
            "Halaman",
            NAV,
            label_visibility="collapsed",
            key="page",
        )

        st.divider()


        # ----------------------------------------------------
        # DATA STATUS
        # ----------------------------------------------------

        render_sidebar_html("""
            <div class="qr-sidebar-label-new">
                DATA TERHUBUNG
            </div>
        """)

        available = sum(
            value is not None
            for value in sources.values()
        )

        render_sidebar_html(f"""
            <div class="qr-sidebar-status-new">
                {available} dari 4 dataset tersedia
            </div>
        """)


        # ----------------------------------------------------
        # DATASET STATUS LIST
        # ----------------------------------------------------

        for filename in FILE_INFO:

            label = {

                "BMKG_Clean_Final.csv":
                    "Katalog kejadian",

                "QuakeReady_Historis_1998_2024.csv":
                    "Grid historis",

                "QuakeReady_Klasifikasi_Tahunan_1998_2024.csv":
                    "Kelas aktivitas tahunan",

                "STGNN_Analysis_2025.csv":
                    "Proyeksi 2025",

            }[filename]


            status = (

                "TERSEDIA"

                if sources[filename] is not None

                else (

                    "ERROR"

                    if filename in errors

                    else "BELUM ADA"

                )

            )


            color = (

                "#91d4c0"

                if sources[filename] is not None

                else "#a7b4c4"

            )


            render_sidebar_html(f"""
                <div class="qr-sidebar-data-line-new">

                    <span class="qr-sidebar-data-name-new">
                        {html.escape(label)}
                    </span>

                    <span
                        class="qr-sidebar-data-state-new"
                        style="color:{color}">
                        {status}
                    </span>

                </div>
            """)


        # ----------------------------------------------------
        # DATA LIBRARY SHORTCUT
        # ----------------------------------------------------

        st.button(
            "Kelola semua dataset",
            key="sidebar_data_shortcut",
            width="stretch",
            on_click=lambda: st.session_state.update(
                page="Data Library"
            ),
        )


        # ----------------------------------------------------
        # HOME SHORTCUT
        # ----------------------------------------------------

        st.button(
            "Kembali ke beranda",
            key="sidebar_home_shortcut",
            width="stretch",
            on_click=lambda: st.session_state.update(
                page="Overview"
            ),
        )

        st.divider()


        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        render_sidebar_html("""
            <div class="qr-sidebar-footer-new">

                INDONESIA · 1998–2024<br>

                Observatorium data dan literasi seismik.<br>

                Bukan sistem peringatan dini.

            </div>
        """)


# ============================================================
# 20. NAVIGATION HISTORY
# ============================================================

# GET CURRENT PAGE FROM SIDEBAR SESSION STATE

page = st.session_state.get("page", "Overview")

# VALIDATE PAGE

if page not in NAV:
    page = "Overview"
    st.session_state["page"] = page

if "_last_visited" not in st.session_state:

    st.session_state._last_visited = page

    st.session_state._back_history = []

    st.session_state._back_navigation = False

elif page != st.session_state._last_visited:

    if not st.session_state._back_navigation:

        st.session_state._back_history.append(
            st.session_state._last_visited
        )

        st.session_state._back_history = (
            st.session_state._back_history[-15:]
        )

    st.session_state._back_navigation = False

    st.session_state._last_visited = page


def go_back():

    if st.session_state._back_history:

        st.session_state.page = (
            st.session_state._back_history.pop()
        )

        st.session_state._back_navigation = True


# ============================================================
# 21. TOP NAVIGATION
# ============================================================

nav_back, nav_home, nav_title, nav_right = st.columns(
    [1.0, 1.0, 3.4, 1.15],
    gap="small",
)

with nav_back:

    st.button(
        "Kembali",
        key="top_back",
        width="stretch",
        disabled=not bool(
            st.session_state._back_history
        ),
        on_click=go_back,
    )

with nav_home:

    st.button(
        "Beranda",
        key="top_home",
        width="stretch",
        on_click=lambda: st.session_state.update(
            page="Overview"
        ),
    )

with nav_title:

    st.markdown(
        f'<div class="qr-breadcrumb">'
        f'QUAKEREADY <span>/</span> '
        f'{html.escape(page.upper())}'
        f'</div>',
        unsafe_allow_html=True,
    )

with nav_right:

    st.button(
        "Data Library",
        key="top_library",
        width="stretch",
        on_click=lambda: st.session_state.update(
            page="Data Library"
        ),
    )

# ============================================================
# 22. SYSTEM NOTIFICATIONS
# ============================================================

if st.session_state.get("data_notice"):

    st.success(
        st.session_state.pop("data_notice")
    )


# ------------------------------------------------------------
# LOCATION MAPPING NOTIFICATIONS
# ------------------------------------------------------------

if not location_mapping_status["available"]:

    st.warning(
        "Metadata lokasi grid belum aktif. "
        "Pastikan grid_location_mapping_BIG_verified.csv "
        "tersedia di folder data/. Dashboard tetap dapat "
        "digunakan, tetapi nama wilayah belum dapat ditampilkan."
    )

elif location_mapping_status["message"]:

    st.warning(
        "Ada masalah saat menghubungkan metadata lokasi: "
        + location_mapping_status["message"]
    )

else:

    unmatched_datasets = [

        name

        for name, report in (
            location_mapping_status["datasets"].items()
        )

        if report["unmatched_rows"] > 0

    ]

    if unmatched_datasets:

        st.info(
            "Sebagian grid belum memiliki pasangan pada mapping lokasi "
            "untuk dataset: "
            + ", ".join(unmatched_datasets)
            + ". Periksa konsistensi penulisan grid_id."
        )

    if location_mapping_status["blank_location_names"] > 0:

        st.warning(
            f'{location_mapping_status["blank_location_names"]} grid '
            "pada file mapping belum memiliki nama_lokasi. "
            "Lengkapi nama wilayah sebelum menyajikan hasil kepada pengguna."
        )


# ============================================================
# 23. SHARED PAGE CONTEXT
# ============================================================

page_context = {

    # STREAMLIT AND LIBRARIES

    "st": st,

    "np": np,

    "pd": pd,

    "go": go,

    "px": px,

    "st_folium": st_folium,

    "html": html,

    "date": __import__("datetime").date,


    # PROJECT PATH

    "ROOT": ROOT,

    "DATA": DATA,

    "NAV": NAV,

    "FILE_INFO": FILE_INFO,


    # COLORS

    "RED": RED,

    "DARK": DARK,

    "TEAL": TEAL,

    "GOLD": GOLD,

    "GRID": GRID,

    "PALETTE": PALETTE,


    # CURRENT PAGE

    "page": page,

    "sources": sources,

    "errors": errors,


    # DATASETS WITH LOCATION METADATA

    "E": E,

    "H": H,

    "A": A,

    "P": P,


    # LOCATION MAPPING

    "add_grid_location": add_grid_location,

    "add_event_location": add_event_location,

    "GRID_LOCATION_MAPPING": GRID_LOCATION_MAPPING,

    "GRID_LOCATION_IDS": GRID_LOCATION_IDS,

    "GRID_LOCATION_COLUMNS": GRID_LOCATION_COLUMNS,

    "GRID_LOCATION_EXPLANATION": GRID_LOCATION_EXPLANATION,

    "MAPPING_FILE": MAPPING_FILE,

    "BOUNDARY_FILE": BOUNDARY_FILE,

    "location_mapping_status": location_mapping_status,


    # UI HELPERS

    "number": number,

    "keyline": keyline,

    "heading": heading,

    "section": section,

    "stat": stat,

    "empty": empty,

    "note": note,

    "charts": charts,

    "download": download,


    "range_slider": range_slider,

    "evidence_panel": evidence_panel,


    # INTERPRETATION

    "describe_event_selection": describe_event_selection,

    "describe_map_selection": describe_map_selection,


    # FIGURES

    "yearly_fig": yearly_fig,

    "hist_fig": hist_fig,


    # DATA MANAGEMENT

    "accept_upload": accept_upload,

    "read_clean": read_clean,

    "save_dataset": save_dataset,

    "remove_dataset": remove_dataset,

    "registry": registry,

    "file_revision": file_revision,

    "DatasetError": DatasetError,


    # ANALYSIS FUNCTIONS

    "annual_counts": annual_counts,

    "event_summary": event_summary,

    "catalog_diagnostics": catalog_diagnostics,

    "compare_periods": compare_periods,

    "grid_year_detail": grid_year_detail,

    "top_historic": top_historic,

    "top_projection": top_projection,

    "preview_map": preview_map,


    "NOTEBOOK_COUNTS": NOTEBOOK_COUNTS,

    "TEST_METRICS": TEST_METRICS,


    # CLEANING FUNCTIONS

    "events_clean": events_clean,

    "historic_clean": historic_clean,

    "annual_clean": annual_clean,

    "projection_clean": projection_clean,


    # VISUALIZATION FUNCTIONS

    "build_map": build_map,

    "in_radius": in_radius,

    "distance_km": distance_km,


    "ACTIVITY_NAMES": ACTIVITY_NAMES,

    "CLUSTER_COLORS": CLUSTER_COLORS,

}


# ============================================================
# 24. PAGE RENDERERS
# ============================================================

PAGE_RENDERERS = {

    "Overview": overview,

    "Earthquake Explorer": earthquake_explorer,

    "Seismic Map": seismic_map,

    "Statistical Atlas": statistical_atlas,

    "ST-GNN Research": stgnn_research,

    "Knowledge Center": knowledge_center,

    "2025 Outlook": outlook_2025,

    "Data Library": data_library,

}


# ============================================================
# 25. RENDER ACTIVE PAGE
# ============================================================

if page not in PAGE_RENDERERS:

    page = "Overview"

    st.session_state.page = "Overview"


PAGE_RENDERERS[page].render(
    page_context
)


# ============================================================
# 26. FOOTER
# ============================================================

st.markdown(
    '<div class="qr-divider"></div>'
    '<div style="font-size:11px;color:#8693a3;'
    'display:flex;justify-content:space-between;'
    'gap:15px;flex-wrap:wrap">'
    '<span>QUAKEREADY / INDONESIAN SEISMIC DATA OBSERVATORY</span>'
    '<span>HISTORICAL RESEARCH · NOT A REAL-TIME WARNING SYSTEM</span>'
    '</div>',
    unsafe_allow_html=True,
)
