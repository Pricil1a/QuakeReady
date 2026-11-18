
# modules/stgnn_research.py

from pathlib import Path

from core.grid_location import (
    enrich_grid_locations,
    load_grid_location_mapping,
)


def render(ctx):

    st = ctx["st"]
    pd = ctx["pd"]
    px = ctx["px"]
    go = ctx["go"]

    H = ctx["H"]
    A = ctx["A"]
    P = ctx["P"]

    DATA = ctx.get(
        "DATA",
        Path(__file__).resolve().parents[1] / "data"
    )

    heading = ctx["heading"]
    section = ctx["section"]
    empty = ctx["empty"]
    note = ctx["note"]
    charts = ctx["charts"]
    number = ctx["number"]
    download = ctx["download"]

    # =========================================================
    # PAGE HEADER
    # =========================================================

    heading(
        "ST-GNN Research",
        "Analisis hotspot historis, clustering embedding, "
        "klasifikasi tahunan, dan evaluasi model dengan "
        "identitas lokasi yang lebih jelas.",
        "QUAKEREADY / ST-GNN RESEARCH",
    )

    # =========================================================
    # LOAD GRID LOCATION MAPPING
    # =========================================================

    mapping_error = None
    grid_mapping = None

    try:

        grid_mapping = load_grid_location_mapping(DATA)

    except Exception as exc:

        grid_mapping = None

        mapping_error = (
            f"{type(exc).__name__}: {exc}"
        )

    if mapping_error:

        note(
            "Metadata lokasi grid belum dapat dimuat. "
            + mapping_error
            + " Pastikan file "
            "grid_location_mapping_BIG_verified.csv "
            "tersedia di folder data/."
        )

    # =========================================================
    # CHECK HISTORICAL DATA
    # =========================================================

    if H is None:

        empty(
            "Data historis belum tersedia",
            "Unggah atau sediakan file "
            "QuakeReady_Historis_1998_2024.csv "
            "pada folder data/ terlebih dahulu.",
        )

        return

    # =========================================================
    # HELPERS
    # =========================================================

    def safe_text(value):

        if value is None:
            return "—"

        try:

            if pd.isna(value):
                return "—"

        except Exception:
            pass

        text = str(value).strip()

        return text if text else "—"

    # ---------------------------------------------------------
    # GRID LOCATION LABEL
    # ---------------------------------------------------------

    def grid_location_label(row):

        grid_id = safe_text(
            row.get("grid_id")
        )

        nama_lokasi = safe_text(
            row.get("lokasi_grid")
        )

        if nama_lokasi == "—":

            nama_lokasi = safe_text(
                row.get("nama_lokasi")
            )

        provinsi = safe_text(
            row.get("provinsi_tercakup")
        )

        if nama_lokasi != "—":

            return (
                f"{grid_id} — {nama_lokasi}"
            )

        if provinsi != "—":

            return (
                f"{grid_id} — {provinsi}"
            )

        return grid_id

    # ---------------------------------------------------------
    # ENSURE LOCATION SCHEMA
    # ---------------------------------------------------------

    def ensure_location_schema(df):

        """
        Memastikan seluruh kolom lokasi tersedia.
        Alias lokasi_grid dibuat dari nama_lokasi.
        """

        if df is None:
            return None

        result = df.copy()

        text_columns = [
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
        ]

        for col in text_columns:

            if col not in result.columns:
                result[col] = pd.NA

        # PRIORITAS 1: NAMA LOKASI DARI MAPPING BIG

        alias = result["lokasi_grid"].astype("string")

        alias_missing = (
            alias.isna()
            |
            alias.str.strip().eq("")
        )

        nama = result["nama_lokasi"].astype("string")

        nama_valid = (
            nama.notna()
            &
            nama.str.strip().ne("")
            &
            nama.str.strip().ne("—")
        )

        use_nama = alias_missing & nama_valid

        alias.loc[use_nama] = nama.loc[use_nama]

        # PRIORITAS 2: PUSAT GRID

        alias_missing = (
            alias.isna()
            |
            alias.str.strip().eq("")
        )

        center_kab = (
            result["center_kabupaten"]
            .astype("string")
            .fillna("")
            .str.strip()
        )

        center_prov = (
            result["center_provinsi"]
            .astype("string")
            .fillna("")
            .str.strip()
        )

        center_label = center_kab.copy()

        has_center_prov = center_prov.ne("")

        center_label.loc[has_center_prov] = (
            center_kab.loc[has_center_prov]
            + ", "
            + center_prov.loc[has_center_prov]
        )

        center_valid = (
            center_kab.ne("")
            |
            center_prov.ne("")
        )

        use_center = alias_missing & center_valid

        alias.loc[use_center] = center_label.loc[use_center]

        # PRIORITAS 3: ID GRID

        alias_missing = (
            alias.isna()
            |
            alias.str.strip().eq("")
        )

        if "grid_id" in result.columns:

            grid_values = result["grid_id"].astype("string")

            use_grid = (
                alias_missing
                &
                grid_values.notna()
            )

            alias.loc[use_grid] = (
                "Grid " + grid_values.loc[use_grid]
            )

        alias = alias.fillna(
            "Belum teridentifikasi dalam polygon administrasi BIG"
        )

        alias = alias.str.strip()

        alias = alias.mask(
            alias.eq(""),
            "Belum teridentifikasi dalam polygon administrasi BIG",
        )

        result["lokasi_grid"] = alias

        return result

    # ---------------------------------------------------------
    # DISPLAY COLUMN RENAMING
    # ---------------------------------------------------------

    def rename_for_display(df):

        rename_map = {

            "historical_hotspot_rank":
                "Peringkat hotspot historis",

            "grid_id":
                "ID grid",

            "lokasi_grid":
                "Lokasi referensi grid",

            "nama_lokasi":
                "Nama lokasi pada mapping",

            "kabupaten_kota_tercakup":
                "Kabupaten/kota tercakup",

            "provinsi_tercakup":
                "Provinsi tercakup",

            "jenis_wilayah":
                "Status cakupan administratif grid",

            "center_kabupaten":
                "Kabupaten/kota di pusat grid",

            "center_provinsi":
                "Provinsi di pusat grid",

            "kabupaten_dominan":
                "Kabupaten/kota dengan irisan terluas",

            "provinsi_dominan":
                "Provinsi dengan irisan terluas",

            "luas_irisan_total_km2":
                "Luas irisan administratif (km²)",

            "total_event_1998_2024":
                "Total kejadian 1998–2024",

            "mean_annual_event":
                "Rata-rata tahunan",

            "years_with_events":
                "Tahun dengan kejadian",

            "years_high_activity":
                "Tahun aktivitas tinggi",

            "max_annual_event":
                "Maksimum tahunan",

            "peak_event_year":
                "Tahun puncak",

            "actual_event_2024":
                "Jumlah kejadian 2024",

            "activity_class_2024":
                "Kelas aktivitas 2024",

            "cluster_historical":
                "Cluster historis",

            "predicted_event_2025":
                "Prediksi kejadian 2025",

            "risk_class":
                "Kelas risiko 2025",

            "cluster":
                "Cluster 2025",

            "year":
                "Tahun",

            "event_count":
                "Jumlah kejadian",

            "activity_class":
                "Kelas aktivitas",

            "activity_label":
                "Label aktivitas",

            "latitude":
                "Latitude",

            "longitude":
                "Longitude",
        }

        existing = {

            old: new

            for old, new in rename_map.items()

            if old in df.columns
        }

        return df.rename(
            columns=existing
        )

    # =========================================================
    # ENRICH DATASETS WITH LOCATION METADATA
    # =========================================================

    def enrich_dataset(df, dataset_name):

        if df is None:
            return None

        if not isinstance(df, pd.DataFrame):

            note(
                f"Dataset {dataset_name} bukan pandas DataFrame. "
                "Metadata lokasi tidak dapat ditambahkan."
            )

            return None

        if "grid_id" not in df.columns:

            note(
                f"Kolom grid_id tidak ditemukan pada {dataset_name}. "
                "Dataset ditampilkan tanpa pengayaan lokasi."
            )

            return ensure_location_schema(df)

        if grid_mapping is not None:

            enriched = enrich_grid_locations(
                df.copy(),
                mapping=grid_mapping,
            )

        else:

            enriched = df.copy()

        return ensure_location_schema(enriched)

    hist = enrich_dataset(
        H,
        "Historical Grid"
    )

    if hist is None:

        empty(
            "Data historis tidak dapat diproses",
            "Pastikan data historis tersedia dalam format DataFrame "
            "dan memiliki kolom grid_id.",
        )

        return

    A = enrich_dataset(
        A,
        "Annual Classification"
    )

    P = enrich_dataset(
        P,
        "ST-GNN Projection"
    )

    # =========================================================
    # SORT HISTORICAL HOTSPOTS
    # =========================================================

    if "historical_hotspot_rank" in hist.columns:

        hist = hist.sort_values(
            "historical_hotspot_rank",
            ascending=True,
            kind="stable",
        ).reset_index(drop=True)

    elif "total_event_1998_2024" in hist.columns:

        hist = hist.sort_values(
            "total_event_1998_2024",
            ascending=False,
            kind="stable",
        ).reset_index(drop=True)

    # =========================================================
    # LOCATION FALLBACK
    # =========================================================

    if "nama_lokasi" not in hist.columns:

        hist["nama_lokasi"] = (
            hist["grid_id"].astype(str)
        )

    if "kabupaten_kota_tercakup" not in hist.columns:

        hist["kabupaten_kota_tercakup"] = "—"

    if "provinsi_tercakup" not in hist.columns:

        hist["provinsi_tercakup"] = "—"

    if "jenis_wilayah" not in hist.columns:

        hist["jenis_wilayah"] = "—"

    hist["grid_label"] = hist.apply(
        grid_location_label,
        axis=1,
    )

    # =========================================================
    # LOCATION EXPLANATION
    # =========================================================

    note(
        "Cara membaca lokasi: ID grid seperti -4.0_128.0 "
        "adalah sel geografis 1° × 1°. "
        "Lokasi referensi menunjukkan kabupaten/kota pada pusat grid "
        "atau wilayah dengan irisan terluas. "
        "Daftar kabupaten/kota dan provinsi menunjukkan seluruh wilayah "
        "yang beririsan dengan sel grid; daftar ini bukan penetapan "
        "kabupaten/kota tepat dari titik episenter dan bukan berarti "
        "gempa terjadi di semua wilayah tersebut. "
        "Cluster adalah kelompok kemiripan embedding, bukan kelas bahaya."
    )

    # =========================================================
    # NAVIGATION TABS
    # =========================================================

    tabs = st.tabs([
        "Historical hotspots",
        "Embedding clustering",
        "Annual classification",
        "Model evaluation",
    ])

    # =========================================================
    # TAB 1 — HISTORICAL HOTSPOTS
    # =========================================================

    with tabs[0]:

        section(
            "20 grid dengan frekuensi tertinggi",
            "Dilengkapi identitas lokasi agar tidak hanya menampilkan ID grid",
        )

        left, mid, right = st.columns(
            [1.7, 0.05, 1.2]
        )

        # HOTSPOT CHART

        with left:

            top20 = hist.head(20).copy()

            top20["plot_label"] = top20.apply(
                lambda r: (
                    f'{safe_text(r.get("grid_id"))} | '
                    f'{safe_text(r.get("lokasi_grid", r.get("nama_lokasi")))}'
                ),
                axis=1,
            )

            fig = go.Figure(

                go.Bar(

                    x=top20["total_event_1998_2024"],

                    y=top20["plot_label"],

                    orientation="h",

                    marker_color="#B5474D",

                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Total kejadian: %{x:,}"
                        "<extra></extra>"
                    ),
                )
            )

            fig.update_layout(

                xaxis_title="Total kejadian 1998–2024",

                yaxis_title="Grid dan lokasi",

                yaxis=dict(
                    autorange="reversed"
                ),

                showlegend=False,
            )

            charts(
                fig,
                height=560,
            )

        # GRID DETAIL

        with right:

            st.markdown(
                "### Detail grid"
            )

            option_map = {

                row["grid_label"]: row["grid_id"]

                for _, row in hist.iterrows()
            }

            selected_label = st.selectbox(
                "Pilih satu grid",
                options=list(option_map.keys()),
                index=0,
            )

            selected_grid = option_map[
                selected_label
            ]

            selected = hist.loc[
                hist["grid_id"] == selected_grid
            ].iloc[0]

            # LOCATION INFORMATION

            st.markdown(
                "#### Identitas lokasi"
            )

            st.write(
                f"**ID Grid:** "
                f"{safe_text(selected.get('grid_id'))}"
            )

            st.write(
                f"**Lokasi referensi grid:** "
                f"{safe_text(selected.get('lokasi_grid'))}"
            )

            st.write(
                f"**Kabupaten/kota yang beririsan:** "
                f"{safe_text(selected.get('kabupaten_kota_tercakup'))}"
            )

            st.write(
                f"**Provinsi yang beririsan:** "
                f"{safe_text(selected.get('provinsi_tercakup'))}"
            )

            st.write(
                f"**Kabupaten/kota di pusat grid:** "
                f"{safe_text(selected.get('center_kabupaten'))}"
            )

            st.write(
                f"**Provinsi di pusat grid:** "
                f"{safe_text(selected.get('center_provinsi'))}"
            )

            st.write(
                f"**Wilayah dengan irisan terluas:** "
                f"{safe_text(selected.get('kabupaten_dominan'))}, "
                f"{safe_text(selected.get('provinsi_dominan'))}"
            )

            st.write(
                f"**Status cakupan administratif grid:** "
                f"{safe_text(selected.get('jenis_wilayah'))}"
            )

            # HISTORICAL SUMMARY

            st.markdown(
                "#### Ringkasan historis"
            )

            st.write(
                f"**Total kejadian:** "
                f"{number(selected.get('total_event_1998_2024', 0))}"
            )

            st.write(
                f"**Peringkat hotspot:** "
                f"{number(selected.get('historical_hotspot_rank', 0))}"
            )

            st.write(
                f"**Rata-rata tahunan:** "
                f"{number(selected.get('mean_annual_event', 0), 1)}"
            )

            st.write(
                f"**Tahun dengan kejadian:** "
                f"{number(selected.get('years_with_events', 0))}"
            )

            st.write(
                f"**Tahun aktivitas tinggi:** "
                f"{number(selected.get('years_high_activity', 0))}"
            )

            st.write(
                f"**Maksimum tahunan:** "
                f"{number(selected.get('max_annual_event', 0))}"
            )

            st.write(
                f"**Tahun puncak:** "
                f"{safe_text(selected.get('peak_event_year'))}"
            )

            st.write(
                f"**Cluster historis:** "
                f"{safe_text(selected.get('cluster_historical'))}"
            )

            if (
                "latitude" in selected
                and "longitude" in selected
            ):

                st.write(
                    f"**Koordinat pusat grid:** "
                    f"{safe_text(selected.get('latitude'))}, "
                    f"{safe_text(selected.get('longitude'))}"
                )

        # HISTORICAL HOTSPOT TABLE

        st.markdown("---")

        st.markdown(
            "### Tabel hotspot historis"
        )

        hotspot_cols = [

            "historical_hotspot_rank",

            "grid_id",

            "lokasi_grid",

            "kabupaten_kota_tercakup",

            "provinsi_tercakup",

            "jenis_wilayah",

            "total_event_1998_2024",

            "mean_annual_event",

            "peak_event_year",

            "cluster_historical",
        ]

        hotspot_cols = [
            c
            for c in hotspot_cols
            if c in hist.columns
        ]

        hotspot_table = rename_for_display(
            hist[hotspot_cols].copy()
        )

        st.dataframe(
            hotspot_table,
            width="stretch",
            hide_index=True,
        )

        download(
            hotspot_table,
            filename=(
                "QuakeReady_Historical_Hotspots_With_Location.csv"
            ),
        )

    # =========================================================
    # TAB 2 — EMBEDDING CLUSTERING
    # =========================================================

    with tabs[1]:

        section(
            "Embedding clustering",
            "Visualisasi grid berdasarkan cluster embedding historis",
        )

        if "cluster_historical" not in hist.columns:

            empty(
                "Cluster historis belum tersedia",
                "Kolom cluster_historical tidak ditemukan pada data historis.",
            )

        else:

            left, right = st.columns(
                [1.6, 1.0]
            )

            # CLUSTER MAP

            with left:

                if all(
                    col in hist.columns
                    for col in [
                        "longitude",
                        "latitude",
                    ]
                ):

                    fig = px.scatter(

                        hist,

                        x="longitude",

                        y="latitude",

                        color="cluster_historical",

                        hover_name="grid_label",

                        hover_data={

                            "grid_id": True,

                            "lokasi_grid": True,

                            "nama_lokasi": False,

                            "kabupaten_kota_tercakup": True,

                            "provinsi_tercakup": True,

                            "total_event_1998_2024": True,

                            "longitude": ":.2f",

                            "latitude": ":.2f",
                        },

                        labels={

                            "longitude": "Longitude",

                            "latitude": "Latitude",

                            "cluster_historical": "Cluster historis",
                        },

                        title=(
                            "Sebaran grid berdasarkan embedding historis"
                        ),
                    )

                    charts(
                        fig,
                        height=560,
                    )

                else:

                    empty(
                        "Koordinat grid belum tersedia",
                        "Kolom latitude dan longitude diperlukan "
                        "untuk visualisasi cluster.",
                    )

            # CLUSTER SUMMARY

            with right:

                cluster_summary = (

                    hist.groupby(
                        "cluster_historical",
                        dropna=False,
                    )

                    .agg(

                        jumlah_grid=(
                            "grid_id",
                            "count",
                        ),

                        total_kejadian=(
                            "total_event_1998_2024",
                            "sum",
                        ),

                        rata_rata_tahunan=(
                            "mean_annual_event",
                            "mean",
                        ),
                    )

                    .reset_index()
                )

                cluster_summary = rename_for_display(
                    cluster_summary
                )

                st.markdown(
                    "### Ringkasan cluster"
                )

                st.dataframe(
                    cluster_summary,
                    width="stretch",
                    hide_index=True,
                )

                # SAMPLE GRID PER CLUSTER

                st.markdown(
                    "### Contoh grid per cluster"
                )

                sample_cols = [

                    "cluster_historical",

                    "grid_id",

                    "lokasi_grid",

                    "kabupaten_kota_tercakup",

                    "provinsi_tercakup",

                    "total_event_1998_2024",
                ]

                sample_cols = [
                    c
                    for c in sample_cols
                    if c in hist.columns
                ]

                sample_table = (

                    hist[sample_cols]

                    .sort_values(

                        [
                            "cluster_historical",
                            "total_event_1998_2024",
                        ],

                        ascending=[
                            True,
                            False,
                        ],

                        kind="stable",
                    )

                    .groupby(
                        "cluster_historical",
                        group_keys=False,
                    )

                    .head(5)
                )

                st.dataframe(
                    rename_for_display(sample_table),
                    width="stretch",
                    hide_index=True,
                )

    # =========================================================
    # TAB 3 — ANNUAL CLASSIFICATION
    # =========================================================

    with tabs[2]:

        section(
            "Klasifikasi tahunan",
            "Setiap grid ditampilkan bersama lokasi utamanya",
        )

        if A is None:

            empty(
                "Data klasifikasi tahunan belum tersedia",
                "File QuakeReady_Klasifikasi_Tahunan_1998_2024.csv "
                "belum tersedia.",
            )

        else:

            annual = A.copy()

            for col in [
                "lokasi_grid",
                "nama_lokasi",
                "kabupaten_kota_tercakup",
                "provinsi_tercakup",
                "jenis_wilayah",
            ]:

                if col not in annual.columns:

                    annual[col] = "—"

            years = sorted(
                annual["year"]
                .dropna()
                .astype(int)
                .unique()
                .tolist()
            )

            if not years:

                empty(
                    "Data tahun belum tersedia",
                    "Kolom year tidak memiliki nilai tahun yang valid.",
                )

            else:

                selected_year = st.selectbox(
                    "Pilih tahun",
                    options=years,
                    index=len(years) - 1,
                )

                year_df = annual.loc[
                    annual["year"].astype(int)
                    == int(selected_year)
                ].copy()

                left, right = st.columns(
                    [1.2, 1.0]
                )

                # ANNUAL CLASSIFICATION CHART

                with left:

                    class_count = (

                        year_df.groupby(
                            "activity_class",
                            dropna=False,
                        )

                        .size()

                        .reset_index(
                            name="jumlah_grid"
                        )

                        .sort_values(
                            "activity_class"
                        )
                    )

                    fig = px.bar(

                        class_count,

                        x="activity_class",

                        y="jumlah_grid",

                        text="jumlah_grid",

                        labels={

                            "activity_class": "Kelas aktivitas",

                            "jumlah_grid": "Jumlah grid",
                        },

                        title=(
                            f"Distribusi kelas aktivitas tahun "
                            f"{selected_year}"
                        ),
                    )

                    charts(
                        fig,
                        height=420,
                    )

                # CLASS EXPLANATION

                with right:

                    st.markdown(
                        "### Keterangan kelas"
                    )

                    st.write(
                        "**Kelas 0** → tidak tercatat kejadian "
                        "pada tahun tersebut"
                    )

                    st.write(
                        "**Kelas 1** → aktivitas sedang"
                    )

                    st.write(
                        "**Kelas 2** → aktivitas tinggi"
                    )

                    st.write("")

                    st.write(
                        "Kolom lokasi ditampilkan untuk membantu pengguna "
                        "memahami grid mana yang sedang dibaca, tanpa harus "
                        "menafsirkan ID grid sendiri."
                    )

                # HIGH ACTIVITY GRID

                st.markdown(
                    "### Grid aktivitas tinggi"
                )

                high_df = year_df.copy()

                sort_columns = [
                    col
                    for col in [
                        "activity_class",
                        "event_count",
                    ]
                    if col in high_df.columns
                ]

                if sort_columns:

                    high_df = high_df.sort_values(

                        sort_columns,

                        ascending=[
                            False
                            for _ in sort_columns
                        ],

                        kind="stable",
                    )

                annual_cols = [

                    "year",

                    "grid_id",

                    "lokasi_grid",

                    "kabupaten_kota_tercakup",

                    "provinsi_tercakup",

                    "jenis_wilayah",

                    "event_count",

                    "activity_class",

                    "activity_label",
                ]

                annual_cols = [
                    c
                    for c in annual_cols
                    if c in high_df.columns
                ]

                st.dataframe(
                    rename_for_display(
                        high_df[annual_cols]
                    ),
                    width="stretch",
                    hide_index=True,
                )

                download(
                    rename_for_display(
                        high_df[annual_cols]
                    ),
                    filename=(
                        f"QuakeReady_Annual_Classification_"
                        f"{selected_year}.csv"
                    ),
                )

    # =========================================================
    # TAB 4 — MODEL EVALUATION
    # =========================================================

    with tabs[3]:

        section(
            "Evaluasi model",
            "Ringkasan agar pengguna memahami arti angka evaluasi",
        )

        st.markdown(
            "### Penjelasan metrik"
        )

        st.write(
            "**MAE** mengukur rata-rata selisih absolut "
            "antara prediksi dan nilai aktual."
        )

        st.write(
            "**RMSE** memberi penalti lebih besar "
            "pada kesalahan yang sangat besar."
        )

        st.write(
            "**R²** menunjukkan seberapa baik model "
            "menjelaskan variasi data."
        )

        st.write(
            "**Spearman** menunjukkan seberapa baik model "
            "menjaga urutan/peringkat grid."
        )

        # MODEL INTERPRETATION

        st.markdown(
            "### Ringkasan interpretasi"
        )

        st.info(
            "Pada penelitian ini, baseline Persistence dan "
            "Five-Year Average masih lebih baik daripada ST-GNN "
            "dalam MAE dan RMSE. Namun, korelasi Spearman yang "
            "cukup tinggi menunjukkan ST-GNN cukup baik dalam "
            "mengenali urutan hotspot relatif, meskipun akurasi "
            "jumlah kejadian masih perlu ditingkatkan."
        )

        # PROJECTION 2025 PREVIEW

        if (
            P is not None
            and "predicted_event_2025" in P.columns
        ):

            st.markdown(
                "### Data proyeksi 2025 tersedia"
            )

            preview_cols = [

                "grid_id",

                "lokasi_grid",

                "kabupaten_kota_tercakup",

                "provinsi_tercakup",

                "predicted_event_2025",

                "risk_class",

                "cluster",
            ]

            preview_cols = [
                c
                for c in preview_cols
                if c in P.columns
            ]

            st.dataframe(
                rename_for_display(
                    P[preview_cols].head(20)
                ),
                width="stretch",
                hide_index=True,
            )

        else:

            note(
                "Jika kamu ingin menampilkan tabel hasil proyeksi "
                "2025 di halaman ini, pastikan file "
                "STGNN_Analysis_2025.csv tersedia dan sudah "
                "berisi kolom prediksi."
            )
