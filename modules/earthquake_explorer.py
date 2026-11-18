
"""
QuakeReady — Earthquake Explorer
- Grid 1° x 1° sesuai mapping BIG (810 grid).
- Lokasi referensi semua kejadian diambil dari CSV mapping 810 grid.
- Penggabungan lokasi menggunakan grid_id (tanpa spatial join 217.807 kejadian).
- Marker peta tetap menggunakan koordinat asli BMKG.
- Mempertahankan filter, tabel, detail, peta, dan unduhan CSV.
"""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from core.grid_location import (
    GRID_LOCATION_EXPLANATION,
    add_event_grid_reference,
    add_event_location,
    enrich_grid_locations,
    generate_event_grid_id,
    load_grid_location_mapping,
)


# ============================================================
# 1. CACHE IDENTIFIKASI LOKASI — LEVEL MODUL
# ============================================================

def _file_signature(path):
    path = Path(path)
    try:
        info = path.stat()
        return (
            str(path.resolve()),
            info.st_mtime_ns,
            info.st_size,
        )
    except OSError:
        return (
            str(path.resolve()),
            None,
            None,
        )


@st.cache_data(
    show_spinner="Menghubungkan katalog gempa dengan 810 grid lokasi...",
    max_entries=3,
    persist="disk",
)
def _cached_add_grid_reference(
    source_df,
    data_dir_text,
    mapping_signature,
):
    """
    Cache hasil penggabungan grid_id dengan CSV mapping 810 grid.

    Tidak membaca polygon BIG/SeaVoX dan tidak melakukan spatial join
    terhadap seluruh katalog saat halaman Earthquake Explorer dibuka.
    """
    _ = mapping_signature

    result = add_event_grid_reference(
        source_df,
        data_dir=data_dir_text,
    )

    if not isinstance(result, pd.DataFrame):
        raise TypeError(
            "add_event_grid_reference() tidak mengembalikan pandas DataFrame."
        )

    if len(result) != len(source_df):
        raise RuntimeError(
            "Jumlah baris berubah setelah penggabungan mapping grid. "
            f"Sumber={len(source_df)}, hasil={len(result)}."
        )

    return _add_grid_reference_fields(result)


@st.cache_data(
    show_spinner="Memeriksa lokasi tepat untuk satu episenter terpilih...",
    max_entries=256,
    persist="disk",
)
def _cached_exact_selected_location(
    latitude,
    longitude,
    data_dir_text,
    boundary_file_text,
    polygon_signature,
):
    """
    Pencocokan polygon BIG/SeaVoX hanya untuk satu titik yang dipilih pengguna.
    Tidak pernah dipanggil untuk seluruh katalog.
    """
    _ = polygon_signature

    point = pd.DataFrame(
        {
            "latitude": [float(latitude)],
            "longitude": [float(longitude)],
        }
    )

    result = add_event_location(
        point,
        data_dir=data_dir_text,
        boundary_file=boundary_file_text,
    )

    if not isinstance(result, pd.DataFrame) or result.empty:
        raise RuntimeError(
            "Pemeriksaan lokasi titik terpilih tidak menghasilkan data."
        )

    return result.iloc[0].to_dict()


# ============================================================
# 2. HELPER
# ============================================================

def _safe_text(value, fallback="—"):
    if value is None:
        return fallback

    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass

    value = str(value).strip()
    return value if value else fallback


def _exact_location_display(exact_location):
    if exact_location is None:
        return "Pemeriksaan titik tidak tersedia"

    location = _safe_text(
        exact_location.get("lokasi_episenter"),
        "Nama wilayah titik tidak tersedia",
    )
    status = _safe_text(
        exact_location.get("status_lokasi_episenter"),
        "",
    ).casefold()

    if (
        "belum teridentifikasi" in location.casefold()
        or "tidak teridentifikasi" in location.casefold()
        or "belum teridentifikasi" in status
    ):
        return (
            "Tidak ada polygon referensi yang mencakup titik ini; "
            "koordinat asli BMKG tetap tersedia."
        )

    return location


def _exact_location_type_display(exact_location):
    if exact_location is None:
        return "Pemeriksaan titik tidak tersedia"

    value = _safe_text(
        exact_location.get("jenis_lokasi_episenter"),
        "Klasifikasi titik tidak tersedia",
    )
    if "belum teridentifikasi" in value.casefold():
        return "Titik berada di luar cakupan polygon BIG/SeaVoX"
    return value


def _safe_float(value):
    try:
        value = float(value)
        return value if pd.notna(value) and abs(value) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _fmt(value, decimals=0):
    try:
        value = float(value)
        if pd.isna(value):
            return "—"
        return f"{value:,.{decimals}f}" if decimals else f"{value:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _coordinate_label(latitude, longitude):
    lat = _safe_float(latitude)
    lon = _safe_float(longitude)

    if lat is None or lon is None:
        return "Koordinat episenter tidak tersedia"

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return "Koordinat episenter tidak valid"

    lat_dir = "LU" if lat >= 0 else "LS"
    lon_dir = "BT" if lon >= 0 else "BB"

    return (
        f"{abs(lat):.4f}° {lat_dir}, "
        f"{abs(lon):.4f}° {lon_dir}"
    )


def _resolve_paths(data_dir):
    data_dir = Path(data_dir).expanduser().resolve()

    mapping_candidates = [
        data_dir / "grid_location_mapping_BIG_verified.csv",
        data_dir / "grid_location_mapping.csv",
    ]

    mapping_file = next(
        (p for p in mapping_candidates if p.exists()),
        mapping_candidates[0],
    )

    boundary_candidates = [
        data_dir / "batas_kabupaten_BIG.geojson",
        data_dir / "batas_kabupaten.geojson",
    ]

    boundary_file = next(
        (p for p in boundary_candidates if p.exists()),
        boundary_candidates[0],
    )

    marine_file = data_dir / "seavox_indonesia.geojson"

    return data_dir, mapping_file, boundary_file, marine_file


def _add_grid_reference_fields(frame):
    """
    Menyiapkan kolom kompatibilitas tampilan berdasarkan metadata grid.

    Kolom yang sebelumnya bernama lokasi_episenter dipertahankan agar
    unduhan/komponen lama tetap kompatibel, tetapi nilainya adalah
    lokasi referensi grid, bukan klaim lokasi tepat episenter.
    """
    result = frame.copy()

    defaults = {
        "nama_lokasi": "Lokasi grid tidak tersedia",
        "lokasi_grid": "Lokasi grid tidak tersedia",
        "kabupaten_kota_tercakup": pd.NA,
        "provinsi_tercakup": pd.NA,
        "kabupaten_dominan": pd.NA,
        "provinsi_dominan": pd.NA,
        "jenis_wilayah": "Klasifikasi grid tidak tersedia",
        "status_pemetaan_lokasi": "Metadata mapping grid tidak tersedia",
        "grid_location_matched": False,
    }

    for column, default in defaults.items():
        if column not in result.columns:
            result[column] = default

    result["grid_location_matched"] = (
        result["grid_location_matched"].fillna(False).astype(bool)
    )

    # Kolom lama dipertahankan untuk kompatibilitas, dengan label UI
    # yang secara eksplisit menyatakan bahwa ini adalah referensi grid.
    result["lokasi_episenter"] = result["lokasi_grid"].fillna(
        "Lokasi grid tidak tersedia"
    )
    result["jenis_lokasi_episenter"] = result["jenis_wilayah"].fillna(
        "Klasifikasi grid tidak tersedia"
    )
    result["status_lokasi_episenter"] = result[
        "status_pemetaan_lokasi"
    ].fillna("Metadata mapping grid tidak tersedia")

    # Tidak mengisi kolom lokasi titik dengan nama wilayah grid.
    result["lokasi_episenter_kabupaten_kota"] = pd.NA
    result["lokasi_episenter_provinsi"] = pd.NA
    result["jumlah_kabupaten_episenter"] = 0
    result["lokasi_episenter_perairan"] = pd.NA

    result["sumber_identifikasi_lokasi"] = (
        "CSV mapping grid BIG/SeaVoX — referensi grid 1° × 1°"
    )

    # Koordinat tetap berasal dari katalog BMKG. Baris dengan koordinat
    # tidak valid tidak boleh diberi nama lokasi grid seolah-olah valid.
    if {"latitude", "longitude"}.issubset(result.columns):
        lat = pd.to_numeric(result["latitude"], errors="coerce")
        lon = pd.to_numeric(result["longitude"], errors="coerce")
        valid = lat.between(-90, 90) & lon.between(-180, 180)

        invalid = ~valid
        result.loc[invalid, "lokasi_episenter"] = (
            "Koordinat episenter tidak valid"
        )
        result.loc[invalid, "jenis_lokasi_episenter"] = (
            "Koordinat tidak valid"
        )
        result.loc[invalid, "status_lokasi_episenter"] = (
            "Koordinat BMKG tidak valid"
        )
        result.loc[invalid, "sumber_identifikasi_lokasi"] = (
            "Katalog BMKG — koordinat tidak valid"
        )

        unmatched = valid & ~result["grid_location_matched"]
        result.loc[unmatched, "status_lokasi_episenter"] = (
            "Grid berada di luar cakupan CSV mapping 810 grid"
        )
        result.loc[unmatched, "sumber_identifikasi_lokasi"] = (
            "Koordinat BMKG dan grid_id; tidak ada pasangan dalam mapping 810 grid"
        )

    return result


def _fallback_events(source_df, grid_mapping):
    """
    Fallback jika cache gagal: tetap gunakan lookup grid, tanpa spatial join.
    """
    result = source_df.copy().reset_index(drop=True)

    if {"latitude", "longitude"}.issubset(result.columns):
        result = generate_event_grid_id(result)

    if grid_mapping is not None and "grid_id" in result.columns:
        result = enrich_grid_locations(
            result,
            mapping=grid_mapping,
        )

    return _add_grid_reference_fields(result)


def _ensure_location_columns(frame):
    return _add_grid_reference_fields(frame)


# ============================================================
# 3. RENDER
# ============================================================

def render(context):
    """Render Earthquake Explorer."""

    # Konteks dari app.py berisi st, pd, E, DATA, dan helper tampilan.
    globals().update(context)

    st_ui = context.get("st", st)
    E = context.get("E")

    data_dir = Path(
        context.get(
            "DATA",
            Path(__file__).resolve().parents[1] / "data",
        )
    ).expanduser().resolve()

    heading = context.get("heading", globals().get("heading"))
    section = context.get("section", globals().get("section"))
    stat = context.get("stat", globals().get("stat"))
    range_slider = context.get(
        "range_slider",
        globals().get("range_slider"),
    )
    describe_event_selection = context.get(
        "describe_event_selection",
        globals().get("describe_event_selection"),
    )
    top_historic = context.get(
        "top_historic",
        globals().get("top_historic"),
    )
    download = context.get(
        "download",
        globals().get("download"),
    )

    data_path, mapping_file, boundary_file, marine_file = (
        _resolve_paths(data_dir)
    )

    # --------------------------------------------------------
    # LOAD MAPPING GRID 810 SEL
    # --------------------------------------------------------

    grid_mapping = None
    mapping_error = None

    try:
        grid_mapping = load_grid_location_mapping(data_path)

        if len(grid_mapping) != 810:
            raise ValueError(
                f"Mapping harus berisi 810 grid, ditemukan {len(grid_mapping)}."
            )

    except Exception as exc:
        mapping_error = f"{type(exc).__name__}: {exc}"

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    if callable(heading):
        heading(
            "Earthquake Explorer",
            (
                "Telusuri kejadian gempa historis berdasarkan waktu, magnitudo, "
                "kedalaman, koordinat BMKG, sumber katalog, dan referensi lokasi grid 1° × 1°."
            ),
            "DATASET / EVENT CATALOGUE",
        )
    else:
        st_ui.title("Earthquake Explorer")
        st_ui.caption(
            "Katalog kejadian gempa dan referensi lokasi berdasarkan grid 1° × 1°."
        )

    if mapping_error:
        st_ui.warning(
            "Mapping grid BIG belum berhasil dimuat. "
            f"Detail: {mapping_error}"
        )
    else:
        st_ui.info(GRID_LOCATION_EXPLANATION)
        st_ui.caption(
            f"Mapping aktif: {len(grid_mapping):,} grid 1° × 1°."
        )

        # Daftar lengkap 810 grid dapat dibuka tanpa menghitung ulang polygon.
        with st_ui.expander(
            f"Lihat seluruh {len(grid_mapping):,} grid beserta lokasinya",
            expanded=False,
        ):
            all_grid_columns = [
                "grid_id",
                "nama_lokasi",
                "kabupaten_kota_tercakup",
                "provinsi_tercakup",
                "kabupaten_dominan",
                "provinsi_dominan",
                "jenis_wilayah",
                "status_pemetaan_lokasi",
            ]
            all_grid_columns = [
                column for column in all_grid_columns
                if column in grid_mapping.columns
            ]

            st_ui.caption(
                "Daftar ini memuat seluruh grid pada CSV mapping. "
                "Lokasi merupakan referensi sel grid 1° × 1°."
            )
            st_ui.dataframe(
                grid_mapping[all_grid_columns],
                width="stretch",
                height=420,
                hide_index=True,
            )

    # --------------------------------------------------------
    # JIKA KATALOG EVENT BELUM TERSEDIA
    # --------------------------------------------------------

    if E is None:
        st_ui.info(
            "Katalog kejadian individual belum dimuat. "
            "Tabel berikut hanya menampilkan ringkasan grid historis, "
            "bukan daftar kejadian gempa satu per satu."
        )

        if callable(top_historic):
            try:
                top = top_historic()

                if top is not None and len(top):
                    if grid_mapping is not None and "grid_id" in top.columns:
                        top = enrich_grid_locations(
                            top,
                            mapping=grid_mapping,
                        )

                    display_cols = [
                        col for col in [
                            "grid_id",
                            "lokasi_grid",
                            "kabupaten_kota_tercakup",
                            "provinsi_tercakup",
                            "jenis_wilayah",
                            "total_event_1998_2024",
                        ]
                        if col in top.columns
                    ]

                    st_ui.dataframe(
                        top[display_cols],
                        width="stretch",
                        hide_index=True,
                    )

            except Exception as exc:
                st_ui.warning(
                    f"Ringkasan grid tidak dapat ditampilkan: {exc}"
                )

        st_ui.button(
            "Buka Data Library untuk mengunggah katalog",
            key="go_library_explorer",
            on_click=lambda: st_ui.session_state.update(
                page="Data Library"
            ),
        )

        st_ui.caption(
            "Unggah BMKG_Clean_Final.csv untuk mengaktifkan pencarian Event ID, "
            "filter waktu, magnitudo, kedalaman, dan pemilihan episenter."
        )

        return

    if not isinstance(E, pd.DataFrame):
        st_ui.error(
            "Katalog kejadian harus berupa pandas DataFrame."
        )
        return

    if E.empty:
        st_ui.warning("Katalog kejadian tidak memiliki data.")
        return

    # --------------------------------------------------------
    # CACHE KEY
    # --------------------------------------------------------

    # Cache daftar kejadian hanya bergantung pada CSV mapping grid.
    # File polygon baru diperiksa jika pengguna memilih satu kejadian.
    location_signature = _file_signature(mapping_file)
    polygon_signature = (
        _file_signature(boundary_file),
        _file_signature(marine_file),
    )

    with st_ui.expander(
        "Pengaturan identifikasi lokasi",
        expanded=False,
    ):
        st_ui.caption(
            "Lokasi kejadian dihubungkan ke CSV mapping 810 grid menggunakan "
            "grid_id. Proses ini tidak menjalankan spatial join BIG/SeaVoX "
            "terhadap seluruh katalog. Hasil penggabungan disimpan dalam cache disk."
        )

        if st_ui.button(
            "Perbarui cache mapping lokasi grid",
            key="refresh_explorer_location_cache",
        ):
            _cached_add_grid_reference.clear()
            st_ui.rerun()

    # --------------------------------------------------------
    # PENGGABUNGAN LOKASI GRID DENGAN CACHE — TANPA SPATIAL JOIN
    # --------------------------------------------------------

    identification_error = None

    try:
        events = _cached_add_grid_reference(
            E,
            str(data_path),
            location_signature,
        )

    except Exception as exc:
        identification_error = f"{type(exc).__name__}: {exc}"

        st_ui.warning(
            "Cache penggabungan grid tidak dapat digunakan. "
            f"Detail: {identification_error}. "
            "Katalog tetap dicoba ditampilkan melalui lookup mapping grid."
        )

        events = _fallback_events(
            E,
            grid_mapping,
        )

    # --------------------------------------------------------
    # PASTIKAN GRID DAN KOLOM LOKASI
    # --------------------------------------------------------

    if (
        "grid_id" not in events.columns
        and {"latitude", "longitude"}.issubset(events.columns)
    ):
        events = generate_event_grid_id(events)

    if (
        grid_mapping is not None
        and "grid_id" in events.columns
        and "lokasi_grid" not in events.columns
    ):
        events = enrich_grid_locations(
            events,
            mapping=grid_mapping,
        )

    events = _ensure_location_columns(events)

    # --------------------------------------------------------
    # NORMALISASI DATA
    # --------------------------------------------------------

    for col in [
        "year",
        "magnitude",
        "depth_km",
        "latitude",
        "longitude",
    ]:
        if col in events.columns:
            events[col] = pd.to_numeric(
                events[col],
                errors="coerce",
            )

    if "date" in events.columns:
        events["date"] = pd.to_datetime(
            events["date"],
            utc=True,
            errors="coerce",
        )

    if "year" not in events.columns:
        if "date" in events.columns:
            events["year"] = events["date"].dt.year
        else:
            st_ui.error(
                "Kolom year dan date tidak tersedia pada katalog."
            )
            return

    if "date" in events.columns:
        events["year"] = events["year"].fillna(
            events["date"].dt.year
        )

    year_values = pd.to_numeric(
        events["year"],
        errors="coerce",
    ).dropna()

    year_values = year_values[
        year_values.between(1998, 2024)
    ]

    if year_values.empty:
        st_ui.error(
            "Tidak ditemukan tahun kejadian valid pada periode 1998–2024."
        )
        return

    year_min = int(year_values.min())
    year_max = int(year_values.max())

    # --------------------------------------------------------
    # FILTER PANEL
    # --------------------------------------------------------

    st_ui.markdown(
        '<div class="qr-panel-title">Filter data kejadian</div>',
        unsafe_allow_html=True,
    )

    st_ui.markdown(
        '<div class="qr-panel-sub">'
        'Sesuaikan filter untuk membatasi catatan kejadian. '
        'Semua filter diterapkan bersamaan. Tabel, ringkasan, '
        'dan interpretasi mengikuti hasil filter saat ini.'
        '</div>',
        unsafe_allow_html=True,
    )

    df = events.copy()
    mtypes = []
    chosen_sources = []
    query = ""

    date_range = (
        date(year_min, 1, 1),
        date(year_max, 12, 31),
    )

    c1, c2, c3 = st_ui.columns(3, gap="medium")

    # TAHUN DAN MAGNITUDO
    with c1:
        if year_min == year_max:
            years = (year_min, year_max)
            st_ui.caption(f"Tahun kejadian: {year_min}")
        else:
            years = st_ui.slider(
                "Rentang tahun kejadian",
                min_value=year_min,
                max_value=year_max,
                value=(year_min, year_max),
                key="exp_year",
                help="Pilih tahun awal dan akhir yang ingin dianalisis.",
            )

        df = df[df["year"].between(*years)]

        if (
            len(df)
            and "magnitude" in df.columns
            and callable(range_slider)
        ):
            df = range_slider(
                df,
                "magnitude",
                "Rentang magnitudo (M)",
                key="exp_mag",
                bounds_df=events,
            )

    # KEDALAMAN DAN JENIS MAGNITUDO
    with c2:
        if (
            len(df)
            and "depth_km" in df.columns
            and callable(range_slider)
        ):
            df = range_slider(
                df,
                "depth_km",
                "Rentang kedalaman (km)",
                key="exp_depth",
                bounds_df=events,
            )

        if "mag_type" in df.columns:
            mag_values = sorted(
                df["mag_type"].dropna().astype(str).unique().tolist()
            )

            mtypes = st_ui.multiselect(
                "Jenis magnitudo",
                mag_values,
                placeholder="Semua jenis magnitudo",
                help="Jenis skala magnitudo yang tercatat pada katalog.",
            )

            if mtypes:
                df = df[
                    df["mag_type"].astype(str).isin(mtypes)
                ]

    # SUMBER DAN PENCARIAN LOKASI
    with c3:
        if "source" in df.columns:
            source_values = sorted(
                df["source"].dropna().astype(str).unique().tolist()
            )

            chosen_sources = st_ui.multiselect(
                "Sumber pencatatan",
                source_values,
                placeholder="Semua sumber",
                help="Kode sumber yang tercantum pada katalog.",
            )

            if chosen_sources:
                df = df[
                    df["source"].astype(str).isin(chosen_sources)
                ]

        query = st_ui.text_input(
            "Cari kejadian atau wilayah",
            placeholder=(
                "Event ID, grid, kabupaten/kota, provinsi, atau laut"
            ),
            help=(
                "Pencarian mencakup ID kejadian, ID grid, lokasi grid, "
                "kabupaten/kota, provinsi, dan nama wilayah pada mapping grid."
            ),
            key="exp_location_search",
        )

        if query.strip():
            searchable_columns = [
                "event_id",
                "grid_id",
                "lokasi_grid",
                "nama_lokasi",
                "kabupaten_kota_tercakup",
                "provinsi_tercakup",
                "kabupaten_dominan",
                "provinsi_dominan",
                "lokasi_episenter",
                "lokasi_episenter_perairan",
                "jenis_lokasi_episenter",
                "status_lokasi_episenter",
            ]

            mask = pd.Series(
                False,
                index=df.index,
                dtype=bool,
            )

            for col in searchable_columns:
                if col in df.columns:
                    mask |= (
                        df[col]
                        .astype("string")
                        .str.contains(
                            query.strip(),
                            case=False,
                            regex=False,
                            na=False,
                        )
                    )

            df = df.loc[mask]

    # --------------------------------------------------------
    # FILTER LANJUTAN
    # --------------------------------------------------------

    with st_ui.expander(
        "Filter lanjutan — tanggal dan koordinat episenter",
        expanded=False,
    ):
        f1, f2 = st_ui.columns(2)

        with f1:
            if "date" in df.columns:
                date_range = st_ui.date_input(
                    "Rentang tanggal kejadian (UTC)",
                    value=(
                        date(years[0], 1, 1),
                        date(years[1], 12, 31),
                    ),
                    min_value=date(1998, 1, 1),
                    max_value=date(2024, 12, 31),
                    key="exp_date_range",
                    help="Tanggal menggunakan waktu UTC pada katalog.",
                )

                if isinstance(date_range, (tuple, list)):
                    event_dates = pd.to_datetime(
                        df["date"],
                        utc=True,
                        errors="coerce",
                    ).dt.date

                    if len(date_range) == 2:
                        df = df.loc[
                            event_dates.between(
                                date_range[0],
                                date_range[1],
                            )
                        ]
                    elif len(date_range) == 1:
                        df = df.loc[
                            event_dates == date_range[0]
                        ]

            if (
                len(df)
                and "latitude" in df.columns
                and callable(range_slider)
            ):
                df = range_slider(
                    df,
                    "latitude",
                    "Lintang episenter",
                    key="exp_lat",
                    bounds_df=events,
                )

        with f2:
            if (
                len(df)
                and "longitude" in df.columns
                and callable(range_slider)
            ):
                df = range_slider(
                    df,
                    "longitude",
                    "Bujur episenter",
                    key="exp_lon",
                    bounds_df=events,
                )

    # --------------------------------------------------------
    # RINGKASAN LOKASI DAN FILTER
    # --------------------------------------------------------

    total_grids = (
        int(df["grid_id"].nunique())
        if "grid_id" in df.columns
        else 0
    )

    if (
        "grid_location_matched" in df.columns
        and "grid_id" in df.columns
    ):
        mapped_grids = int(
            df.loc[
                df["grid_location_matched"].fillna(False),
                "grid_id",
            ].nunique()
        )
    else:
        mapped_grids = 0

    max_magnitude = (
        _fmt(df["magnitude"].max(), 1)
        if len(df) and "magnitude" in df.columns
        else "—"
    )

    if "jenis_wilayah" in df.columns:
        grid_type = df["jenis_wilayah"].astype("string").fillna("")
        land_count = int(grid_type.str.contains("daratan", case=False, na=False).sum())
        sea_count = int(grid_type.str.contains("perairan", case=False, na=False).sum())
        mixed_count = int(
            grid_type.str.contains("campuran|perbatasan", case=False, regex=True, na=False).sum()
        )
        if "grid_location_matched" in df.columns:
            unmatched_mask = ~df["grid_location_matched"].fillna(False)
            if {"latitude", "longitude"}.issubset(df.columns):
                lat_check = pd.to_numeric(df["latitude"], errors="coerce")
                lon_check = pd.to_numeric(df["longitude"], errors="coerce")
                valid_check = lat_check.between(-90, 90) & lon_check.between(-180, 180)
                outside_count = int((unmatched_mask & valid_check).sum())
                invalid_count = int((~valid_check).sum())
            else:
                outside_count = int(unmatched_mask.sum())
                invalid_count = 0
        else:
            outside_count = 0
            invalid_count = 0

        st_ui.caption(
            "Klasifikasi wilayah grid pada hasil filter (jumlah kejadian): "
            f"{_fmt(land_count)} daratan · "
            f"{_fmt(sea_count)} perairan · "
            f"{_fmt(mixed_count)} grid campuran/perbatasan · "
            f"{_fmt(outside_count)} di luar mapping · "
            f"{_fmt(invalid_count)} koordinat tidak valid."
        )

    m1, m2, m3 = st_ui.columns(3, gap="small")

    with m1:
        if callable(stat):
            stat(
                "HASIL FILTER",
                _fmt(len(df)),
                "Kejadian yang memenuhi semua filter",
            )
        else:
            st_ui.metric("HASIL FILTER", _fmt(len(df)))

    with m2:
        if callable(stat):
            stat(
                "GRID DENGAN LOKASI",
                _fmt(mapped_grids),
                f"Dari {_fmt(total_grids)} grid",
            )
        else:
            st_ui.metric("GRID DENGAN LOKASI", _fmt(mapped_grids))

    with m3:
        if callable(stat):
            stat(
                "MAGNITUDO TERTINGGI",
                max_magnitude,
                "Pada hasil filter saat ini",
            )
        else:
            st_ui.metric("MAGNITUDO TERTINGGI", max_magnitude)

    # --------------------------------------------------------
    # PENJELASAN FILTER AKTIF
    # --------------------------------------------------------

    filter_details = [
        f"Tahun {years[0]}–{years[1]}"
    ]

    for key, label, fmt in [
        ("exp_mag", "Magnitudo M", "{:.1f}"),
        ("exp_depth", "Kedalaman (km)", "{:.0f}"),
        ("exp_lat", "Lintang", "{:.1f}"),
        ("exp_lon", "Bujur", "{:.1f}"),
    ]:
        values = st_ui.session_state.get(key)

        if values is not None and len(values) == 2:
            try:
                filter_details.append(
                    f"{label} {fmt.format(values[0])}–{fmt.format(values[1])}"
                )
            except (TypeError, ValueError):
                pass

    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        filter_details.append(
            f"Tanggal UTC {date_range[0]}–{date_range[1]}"
        )

    if mtypes:
        filter_details.append(
            "Jenis magnitudo: " + ", ".join(mtypes[:5])
        )

    if chosen_sources:
        filter_details.append(
            "Sumber: " + ", ".join(chosen_sources[:5])
        )

    if query.strip():
        filter_details.append(
            "Pencarian: " + query.strip()[:70]
        )

    if callable(describe_event_selection):
        describe_event_selection(
            df,
            events,
            " | ".join(filter_details),
        )

    if len(df) and "grid_id" in df.columns:
        grid_counts = df["grid_id"].dropna().value_counts()

        if not grid_counts.empty:
            most_common_grid = grid_counts.index[0]
            representative = df.loc[
                df["grid_id"] == most_common_grid
            ].iloc[0]

            st_ui.caption(
                "Grid dengan catatan terbanyak pada hasil filter: "
                f"{most_common_grid} — "
                f"{_safe_text(representative.get('lokasi_grid'))}. "
                "Jumlah ini menunjukkan frekuensi catatan, bukan ukuran risiko."
            )

    # --------------------------------------------------------
    # TABEL KEJADIAN
    # --------------------------------------------------------

    if callable(section):
        section(
            "Daftar kejadian dan lokasi grid",
            "DAPAT DICARI DAN DIUNDUH",
        )
    else:
        st_ui.subheader(
            "Daftar kejadian dan lokasi grid"
        )

    st_ui.caption(
        "Nama lokasi pada tabel merupakan referensi geografis sel grid 1° × 1° "
        "dari CSV mapping 810 grid. Kabupaten/kota dan provinsi menunjukkan "
        "cakupan grid, bukan alamat tepat episenter. Koordinat lintang dan bujur "
        "tetap merupakan koordinat asli BMKG."
    )

    display_columns = [
        "date",
        "event_id",
        "magnitude",
        "depth_km",
        "latitude",
        "longitude",
        "grid_id",
        "lokasi_grid",
        "kabupaten_kota_tercakup",
        "provinsi_tercakup",
        "kabupaten_dominan",
        "provinsi_dominan",
        "jenis_wilayah",
        "status_pemetaan_lokasi",
        "mag_type",
        "source",
    ]

    display_columns = [
        col for col in display_columns
        if col in df.columns
    ]

    visible_rows = (
        df[display_columns]
        .head(3000)
        .reset_index(drop=True)
    )

    st_ui.caption(
        f"Tabel menampilkan {_fmt(len(visible_rows))} baris pertama dari "
        f"{_fmt(len(df))} hasil filter. Unduhan CSV mencakup seluruh hasil filter."
    )

    column_config = {}

    if "date" in visible_rows.columns:
        column_config["date"] = (
            st_ui.column_config.DatetimeColumn(
                "Waktu kejadian (UTC)",
                format="YYYY-MM-DD HH:mm",
            )
        )

    text_labels = {
        "event_id": "Event ID",
        "grid_id": "ID grid 1° × 1°",
        "lokasi_grid": "Lokasi referensi grid 1° × 1°",
        "kabupaten_kota_tercakup": "Kabupaten/kota dalam cakupan grid",
        "provinsi_tercakup": "Provinsi dalam cakupan grid",
        "kabupaten_dominan": "Kabupaten/kota dengan irisan terluas",
        "provinsi_dominan": "Provinsi dengan irisan terluas",
        "jenis_wilayah": "Klasifikasi wilayah grid",
        "status_pemetaan_lokasi": "Metode pemetaan grid",
        "mag_type": "Jenis magnitudo",
        "source": "Sumber katalog",
    }

    for col, label in text_labels.items():
        if col in visible_rows.columns:
            column_config[col] = (
                st_ui.column_config.TextColumn(label)
            )

    numeric_labels = {
        "magnitude": ("Magnitudo (M)", "%.1f"),
        "depth_km": ("Kedalaman (km)", "%.1f"),
        "latitude": ("Lintang episenter", "%.3f"),
        "longitude": ("Bujur episenter", "%.3f"),
    }

    for col, (label, fmt) in numeric_labels.items():
        if col in visible_rows.columns:
            column_config[col] = (
                st_ui.column_config.NumberColumn(
                    label,
                    format=fmt,
                )
            )

    if visible_rows.empty:
        st_ui.info(
            "Tidak ada kejadian yang memenuhi filter saat ini."
        )
        selected_rows = []

    else:
        selection = st_ui.dataframe(
            visible_rows,
            hide_index=True,
            width="stretch",
            height=460,
            selection_mode="single-row",
            on_select="rerun",
            key="selected_event",
            column_config=column_config,
        )

        selected_rows = []

        if selection is not None:
            selected_state = getattr(
                selection,
                "selection",
                None,
            )

            if selected_state is not None:
                selected_rows = (
                    getattr(selected_state, "rows", [])
                    or []
                )

    # --------------------------------------------------------
    # DETAIL KEJADIAN DAN PETA
    # --------------------------------------------------------

    if selected_rows:
        selected_index = int(selected_rows[0])

        if 0 <= selected_index < len(visible_rows):
            row = visible_rows.iloc[selected_index]

            event_id = _safe_text(
                row.get("event_id"),
                "ID tidak tersedia",
            )

            event_time = _safe_text(row.get("date"))
            magnitude = _safe_float(row.get("magnitude"))
            depth = _safe_float(row.get("depth_km"))
            latitude = _safe_float(row.get("latitude"))
            longitude = _safe_float(row.get("longitude"))
            grid_id = _safe_text(row.get("grid_id"))

            exact_location = None
            exact_location_error = None

            if (
                latitude is not None
                and longitude is not None
                and -90 <= latitude <= 90
                and -180 <= longitude <= 180
            ):
                try:
                    exact_location = _cached_exact_selected_location(
                        latitude,
                        longitude,
                        str(data_path),
                        str(boundary_file),
                        polygon_signature,
                    )
                except Exception as exc:
                    exact_location_error = (
                        f"{type(exc).__name__}: {exc}"
                    )

            st_ui.markdown("### Detail kejadian terpilih")
            st_ui.markdown(f"**Event ID:** `{event_id}`")

            d1, d2 = st_ui.columns(2)

            with d1:
                st_ui.write(
                    f"**Waktu kejadian (UTC):** {event_time}"
                )

                st_ui.write(
                    "**Magnitudo:** "
                    + (
                        f"M {magnitude:.1f}"
                        if magnitude is not None
                        else "—"
                    )
                )

                st_ui.write(
                    "**Kedalaman sumber:** "
                    + (
                        f"{depth:.1f} km"
                        if depth is not None
                        else "—"
                    )
                )

                st_ui.write(
                    "**Koordinat episenter:** "
                    + _coordinate_label(latitude, longitude)
                )

            with d2:
                st_ui.write(f"**ID grid:** {grid_id}")

                st_ui.write(
                    "**Lokasi referensi grid:** "
                    f"{_safe_text(row.get('lokasi_grid'))}"
                )

                st_ui.write(
                    "**Kabupaten/kota yang beririsan:** "
                    f"{_safe_text(row.get('kabupaten_kota_tercakup'))}"
                )

                st_ui.write(
                    "**Provinsi yang beririsan:** "
                    f"{_safe_text(row.get('provinsi_tercakup'))}"
                )

                st_ui.write(
                    "**Wilayah dengan irisan terluas:** "
                    f"{_safe_text(row.get('kabupaten_dominan'))}, "
                    f"{_safe_text(row.get('provinsi_dominan'))}"
                )

                st_ui.write(
                    "**Klasifikasi wilayah grid:** "
                    f"{_safe_text(row.get('jenis_wilayah'))}"
                )

                st_ui.write(
                    "**Metode pemetaan grid:** "
                    f"{_safe_text(row.get('status_pemetaan_lokasi'))}"
                )

                st_ui.write(
                    "**Lokasi tepat berdasarkan polygon:** "
                    + _exact_location_display(exact_location)
                )

                if exact_location is not None:
                    st_ui.write(
                        "**Jenis lokasi titik:** "
                        f"{_exact_location_type_display(exact_location)}"
                    )
                    st_ui.write(
                        "**Sumber identifikasi titik:** "
                        f"{_safe_text(exact_location.get('sumber_identifikasi_lokasi'))}"
                    )

                elif exact_location_error:
                    st_ui.caption(
                        "Pemeriksaan polygon untuk titik terpilih tidak berhasil: "
                        f"{exact_location_error}"
                    )

                st_ui.write(
                    "**Sumber referensi grid:** "
                    f"{_safe_text(row.get('sumber_identifikasi_lokasi'))}"
                )

            st_ui.info(
                "Lokasi referensi grid berasal dari CSV mapping 810 grid. "
                "Lokasi tepat pada detail kejadian diperiksa hanya untuk satu "
                "titik terpilih menggunakan polygon BIG/SeaVoX. Marker peta "
                "tetap memakai koordinat asli BMKG."
            )

            st_ui.markdown(
                "**Peta episenter kejadian terpilih**"
            )

            if (
                latitude is not None
                and longitude is not None
                and -90 <= latitude <= 90
                and -180 <= longitude <= 180
            ):
                try:
                    import folium

                    # Gunakan OpenStreetMap sebagai basemap.
                    # CARTODB positron sebelumnya menampilkan "API KEY REQUIRED"
                    # sehingga tile peta kosong walaupun marker berhasil dibuat.
                    # OpenStreetMap tidak memerlukan API key.
                    event_map = folium.Map(
                        location=[latitude, longitude],
                        zoom_start=7,
                        min_zoom=2,
                        max_zoom=19,
                        tiles="OpenStreetMap",
                        control_scale=True,
                        zoom_control=True,
                        prefer_canvas=True,
                    )

                    popup_lines = [
                        f"<b>{html.escape(event_id)}</b>",
                        (
                            "Magnitudo: "
                            + (
                                f"M {magnitude:.1f}"
                                if magnitude is not None
                                else "—"
                            )
                        ),
                        (
                            "Kedalaman: "
                            + (
                                f"{depth:.1f} km"
                                if depth is not None
                                else "—"
                            )
                        ),
                        (
                            "Koordinat: "
                            + html.escape(
                                _coordinate_label(latitude, longitude)
                            )
                        ),
                        "ID grid: " + html.escape(grid_id),
                        (
                            "Lokasi tepat berdasarkan polygon: "
                            + html.escape(
                                _exact_location_display(exact_location)
                            )
                        ),
                        (
                            "Lokasi referensi grid 1° × 1°: "
                            + html.escape(
                                _safe_text(row.get("lokasi_grid"))
                            )
                        ),
                        (
                            "Klasifikasi grid: "
                            + html.escape(
                                _safe_text(row.get("jenis_wilayah"))
                            )
                        ),
                    ]

                    # Marker episenter menggunakan koordinat asli katalog,
                    # bukan titik tengah grid 1° x 1°.
                    folium.Marker(
                        location=[latitude, longitude],
                        tooltip=f"Episenter tercatat — {event_id}",
                        popup=folium.Popup(
                            "<br>".join(popup_lines),
                            max_width=420,
                        ),
                        icon=folium.Icon(
                            color="red",
                            icon="info-sign",
                        ),
                    ).add_to(event_map)

                    # Lingkaran kecil membantu melihat posisi titik secara jelas.
                    folium.CircleMarker(
                        location=[latitude, longitude],
                        radius=7,
                        color="#B42318",
                        weight=2,
                        fill=True,
                        fill_color="#F04438",
                        fill_opacity=0.30,
                        tooltip="Koordinat episenter",
                    ).add_to(event_map)

                    # Tidak menggunakan st_folium sehingga tidak memerlukan
                    # frontend component streamlit_folium.
                    # HTML Folium diperbarui setiap kali pilihan baris berubah.
                    st_ui.components.v1.html(
                        event_map.get_root().render(),
                        height=430,
                        scrolling=False,
                    )

                except Exception as exc:
                    st_ui.warning(
                        f"Peta episenter tidak dapat ditampilkan: {exc}"
                    )

            else:
                st_ui.warning(
                    "Koordinat episenter tidak valid; peta tidak dapat dibuat."
                )

    else:
        st_ui.caption(
            "Pilih satu baris pada tabel untuk melihat detail kejadian "
            "dan posisi episenternya pada peta."
        )

    # --------------------------------------------------------
    # INTERPRETASI DAN EKSPOR
    # --------------------------------------------------------

    st_ui.caption(
        "Catatan interpretasi: magnitudo menggambarkan ukuran sumber gempa; "
        "kedalaman merupakan parameter sumber, bukan ukuran dampak di permukaan. "
        "Frekuensi historis bukan tingkat risiko bencana dan bukan prediksi "
        "terjadinya gempa berikutnya."
    )

    export_df = df.drop(
        columns=[
            "_coordinate_valid",
            "_event_row_id",
        ],
        errors="ignore",
    )

    filename = (
        "QuakeReady_Event_Explorer_Filtered_With_"
        "Grid_Location_Reference.csv"
    )

    if callable(download):
        download(export_df, filename)

    else:
        st_ui.download_button(
            "Unduh seluruh hasil filter (CSV)",
            data=export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=filename,
            mime="text/csv",
            key="download_explorer_csv",
            width="stretch",
        )
