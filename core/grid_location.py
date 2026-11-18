"""Pemetaan grid, lokasi episenter daratan BIG, dan lokasi perairan SeaVoX."""

from __future__ import annotations

import json
import os
import ssl
import warnings
from functools import lru_cache
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"

MAPPING_FILE = DATA_DIR / "grid_location_mapping_BIG_verified.csv"

BOUNDARY_FILE = DATA_DIR / "batas_kabupaten_BIG.geojson"

MARINE_FILE = DATA_DIR / "seavox_indonesia.geojson"

MARINE_WFS_URL = "https://geo.vliz.be/geoserver/MarineRegions/wfs"

MARINE_WFS_LAYER = "MarineRegions:seavox_v19"

MARINE_BBOX = "93,-12,142,8,CRS:84"

EXPECTED_GRID_COUNT = 810


# ============================================================
# 2. LOCATION COLUMNS
# ============================================================

LOCATION_COLUMNS = [
    "nama_lokasi",
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

EVENT_LOCATION_COLUMNS = [
    "lokasi_episenter_kabupaten_kota",
    "lokasi_episenter_provinsi",
    "jumlah_kabupaten_episenter",
    "lokasi_episenter",
    "status_lokasi_episenter",
    "jenis_lokasi_episenter",
    "lokasi_episenter_perairan",
    "sumber_identifikasi_lokasi",
]

GRID_LOCATION_EXPLANATION = (
    "Lokasi yang ditampilkan pada Earthquake Explorer merupakan referensi geografis "
    "grid 1° × 1° berdasarkan CSV mapping 810 grid hasil pencocokan polygon BIG dan "
    "SeaVoX. Nama wilayah, kabupaten/kota, dan provinsi menjelaskan cakupan sel grid, "
    "bukan alamat tepat titik episenter. Posisi marker peta tetap memakai koordinat "
    "asli BMKG. Pencocokan lokasi grid dilakukan melalui grid_id dan tidak menjalankan "
    "spatial join terhadap seluruh katalog setiap kali halaman dibuka. Jika pengguna "
    "memilih satu kejadian, lokasi titik tersebut dapat diperiksa terpisah menggunakan "
    "polygon BIG/SeaVoX tanpa memproses ulang seluruh katalog."
)


# ============================================================
# 3. PATH RESOLUTION
# ============================================================

def _resolve_folder(value=None):

    if value is None:
        return DATA_DIR

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = ROOT / path

    return path


def resolve_mapping_path(data_dir=None):

    path = (
        Path(data_dir).expanduser()
        if data_dir is not None
        else DATA_DIR
    )

    if path.suffix.lower() == ".csv":

        return path if path.is_absolute() else ROOT / path

    if not path.is_absolute():
        path = ROOT / path

    candidates = [
        path / "grid_location_mapping_BIG_verified.csv",
        path / "grid_location_mapping.csv",
    ]

    return next(
        (
            candidate
            for candidate in candidates
            if candidate.exists()
        ),
        candidates[0],
    )


def resolve_boundary_path(boundary_file=None):

    if boundary_file is not None:

        path = Path(boundary_file).expanduser()

        return (
            path
            if path.is_absolute()
            else ROOT / path
        )

    candidates = [
        BOUNDARY_FILE,
        DATA_DIR / "batas_kabupaten.geojson",
    ]

    return next(
        (
            candidate
            for candidate in candidates
            if candidate.exists()
        ),
        candidates[0],
    )


def _clean_columns(frame):

    frame = frame.copy()

    frame.columns = (
        frame.columns.astype(str).str.strip()
    )

    return frame


# ============================================================
# 4. GRID LOCATION MAPPING
# ============================================================

@lru_cache(maxsize=4)
def _load_mapping_cached(
    path_text,
    modified_ns,
    file_size,
):

    del modified_ns, file_size

    path = Path(path_text)

    mapping = _clean_columns(
        pd.read_csv(
            path,
            encoding="utf-8-sig",
            low_memory=False,
            dtype={"grid_id": "string"},
        )
    )

    required = [
        "grid_id",
        "nama_lokasi",
        "kabupaten_kota_tercakup",
        "provinsi_tercakup",
        "jenis_wilayah",
    ]

    missing = [
        column
        for column in required
        if column not in mapping.columns
    ]

    if missing:

        raise ValueError(
            f"Kolom wajib mapping BIG tidak tersedia: {missing}"
        )

    for column in LOCATION_COLUMNS:

        if column not in mapping.columns:
            mapping[column] = pd.NA

    mapping["grid_id"] = (
        mapping["grid_id"]
        .astype("string")
        .str.strip()
    )

    if (
        mapping["grid_id"].isna().any()
        or mapping["grid_id"].eq("").any()
    ):

        raise ValueError(
            "Terdapat grid_id kosong dalam mapping BIG."
        )

    if mapping["grid_id"].duplicated().any():

        duplicates = (
            mapping.loc[
                mapping["grid_id"].duplicated(),
                "grid_id",
            ]
            .head(10)
            .tolist()
        )

        raise ValueError(
            f"Grid ID duplikat dalam mapping BIG: {duplicates}"
        )

    if len(mapping) != EXPECTED_GRID_COUNT:

        raise ValueError(
            f"Jumlah mapping seharusnya "
            f"{EXPECTED_GRID_COUNT} grid, "
            f"tetapi ditemukan {len(mapping)}."
        )

    return mapping[
        ["grid_id"] + LOCATION_COLUMNS
    ].copy()


def load_grid_location_mapping(data_dir=None):

    path = resolve_mapping_path(data_dir)

    if not path.exists():

        raise FileNotFoundError(
            f"File mapping BIG tidak ditemukan: {path}. "
            "Pastikan grid_location_mapping_BIG_verified.csv "
            "atau grid_location_mapping.csv tersedia di folder data/."
        )

    stat = path.stat()

    return _load_mapping_cached(
        str(path.resolve()),
        stat.st_mtime_ns,
        stat.st_size,
    ).copy()


def _prepare_mapping(mapping):

    if not isinstance(mapping, pd.DataFrame):

        raise TypeError(
            "Mapping harus berupa pandas DataFrame."
        )

    mapping = _clean_columns(mapping)

    required = [
        "grid_id",
        "nama_lokasi",
        "kabupaten_kota_tercakup",
        "provinsi_tercakup",
        "jenis_wilayah",
    ]

    missing = [
        column
        for column in required
        if column not in mapping.columns
    ]

    if missing:

        raise ValueError(
            f"Kolom wajib mapping tidak tersedia: {missing}"
        )

    for column in LOCATION_COLUMNS:

        if column not in mapping.columns:
            mapping[column] = pd.NA

    mapping["grid_id"] = (
        mapping["grid_id"]
        .astype("string")
        .str.strip()
    )

    if (
        mapping["grid_id"].isna().any()
        or mapping["grid_id"].eq("").any()
    ):

        raise ValueError(
            "Mapping memiliki grid_id kosong."
        )

    if mapping["grid_id"].duplicated().any():

        raise ValueError(
            "Mapping memiliki grid_id duplikat."
        )

    return mapping[
        ["grid_id"] + LOCATION_COLUMNS
    ].copy()


# ============================================================
# 5. ADMINISTRATIVE BOUNDARIES — BIG
# ============================================================

def _find_admin_column(columns, candidates):

    lookup = {
        str(column).strip().lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


@lru_cache(maxsize=2)
def _load_admin_cached(
    path_text,
    modified_ns,
    file_size,
):

    del modified_ns, file_size

    path = Path(path_text)

    if not path.exists():

        raise FileNotFoundError(
            f"Polygon BIG tidak ditemukan: {path}"
        )

    # Geopandas hanya dimuat ketika pemrosesan polygon benar-benar diminta.
    import geopandas as gpd

    admin = gpd.read_file(path)

    if admin.empty:

        raise ValueError(
            "Polygon administrasi BIG kosong."
        )

    if admin.crs is None:

        raise ValueError(
            "CRS polygon BIG belum tersedia."
        )

    admin = admin.to_crs("EPSG:4326")

    kab_col = _find_admin_column(
        admin.columns,
        [
            "kabupaten_kota",
            "wadmkk",
        ],
    )

    prov_col = _find_admin_column(
        admin.columns,
        [
            "provinsi",
            "wadmpr",
        ],
    )

    if kab_col is None or prov_col is None:

        raise ValueError(
            "Kolom administrasi BIG tidak ditemukan. "
            f"Kolom tersedia: {admin.columns.tolist()}"
        )

    admin = admin[
        [
            kab_col,
            prov_col,
            "geometry",
        ]
    ].copy()

    admin = admin.rename(
        columns={
            kab_col: "kabupaten_kota",
            prov_col: "provinsi",
        }
    )

    admin = admin.dropna(
        subset=[
            "kabupaten_kota",
            "provinsi",
            "geometry",
        ]
    )

    admin["kabupaten_kota"] = (
        admin["kabupaten_kota"]
        .astype(str)
        .str.strip()
    )

    admin["provinsi"] = (
        admin["provinsi"]
        .astype(str)
        .str.strip()
    )

    admin = admin[
        admin["kabupaten_kota"].ne("")
        & admin["provinsi"].ne("")
        & admin.geometry.notna()
        & ~admin.geometry.is_empty
    ].copy()

    invalid = ~admin.geometry.is_valid

    if invalid.any():

        try:

            from shapely import make_valid

            repair = make_valid

        except ImportError:

            repair = lambda geometry: geometry.buffer(0)

        admin.loc[
            invalid,
            "geometry",
        ] = admin.loc[
            invalid,
            "geometry",
        ].apply(repair)

    admin = admin[
        admin.geometry.notna()
        & ~admin.geometry.is_empty
        & admin.geometry.geom_type.isin(
            [
                "Polygon",
                "MultiPolygon",
            ]
        )
    ].copy()

    if admin.empty:

        raise ValueError(
            "Tidak ada polygon administrasi BIG yang valid."
        )

    return admin.reset_index(drop=True)


def load_admin_boundaries(boundary_file=None):

    path = resolve_boundary_path(boundary_file)

    if not path.exists():

        raise FileNotFoundError(
            f"Polygon BIG tidak ditemukan: {path}"
        )

    stat = path.stat()

    return _load_admin_cached(
        str(path.resolve()),
        stat.st_mtime_ns,
        stat.st_size,
    ).copy()


# ============================================================
# 6. INTERNAL GRID LOCATION MERGE
# ============================================================

def _merge_grid_locations(df, mapping_df):

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input harus berupa pandas DataFrame."
        )

    if "grid_id" not in df.columns:

        raise ValueError(
            "Kolom grid_id tidak ditemukan."
        )

    result = df.copy()

    original_rows = len(result)

    result["grid_id"] = (
        result["grid_id"]
        .astype("string")
        .str.strip()
    )

    drop_columns = LOCATION_COLUMNS + [
        "lokasi_grid",
        "grid_location_matched",
    ]

    result = result.drop(
        columns=[
            column
            for column in drop_columns
            if column in result.columns
        ],
        errors="ignore",
    )

    result = result.merge(
        mapping_df,
        on="grid_id",
        how="left",
        validate="many_to_one",
        sort=False,
    )

    if len(result) != original_rows:

        raise RuntimeError(
            "Jumlah baris berubah setelah penggabungan mapping."
        )

    unmatched = (
        result["grid_id"].notna()
        & result["nama_lokasi"].isna()
    )

    result.loc[
        unmatched,
        "nama_lokasi",
    ] = "Grid ID tidak ditemukan dalam mapping BIG"

    result.loc[
        unmatched,
        "jenis_wilayah",
    ] = "ID grid belum terpetakan"

    result.loc[
        unmatched,
        "status_pemetaan_lokasi",
    ] = "Grid ID tidak ditemukan dalam mapping BIG"

    empty = (
        result["grid_id"].isna()
        | result["grid_id"].eq("")
    )

    result.loc[
        empty,
        "nama_lokasi",
    ] = "Grid ID tidak tersedia"

    result.loc[
        empty,
        "jenis_wilayah",
    ] = "Grid ID kosong"

    result.loc[
        empty,
        "status_pemetaan_lokasi",
    ] = "Grid ID kosong"

    result["lokasi_grid"] = result["nama_lokasi"]

    result["grid_location_matched"] = (
        ~unmatched
        & ~empty
        & result["nama_lokasi"].notna()
    )

    return result


# ============================================================
# 7. ADD GRID LOCATION
# ============================================================

def add_grid_location(df, data_dir=None):

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input harus berupa pandas DataFrame."
        )

    if "grid_id" not in df.columns:

        return df.copy()

    mapping = load_grid_location_mapping(data_dir)

    return _merge_grid_locations(
        df,
        mapping,
    )


def add_event_grid_reference(
    df,
    data_dir=None,
    mapping=None,
):
    """
    Tambahkan lokasi referensi grid pada katalog kejadian secara cepat.

    Fungsi ini hanya membuat grid_id dari koordinat BMKG dan melakukan
    many-to-one merge ke CSV mapping 810 grid. Fungsi ini TIDAK menjalankan
    spatial join BIG/SeaVoX terhadap seluruh kejadian.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input harus berupa pandas DataFrame.")

    result = df.copy().reset_index(drop=True)

    if {"latitude", "longitude"}.issubset(result.columns):
        result = generate_event_grid_id(result)
    elif "grid_id" not in result.columns:
        raise ValueError(
            "Kolom latitude/longitude atau grid_id wajib tersedia."
        )

    if mapping is None:
        mapping_df = load_grid_location_mapping(data_dir)
    elif isinstance(mapping, pd.DataFrame):
        mapping_df = _prepare_mapping(mapping)
    elif isinstance(mapping, (str, Path)):
        mapping_df = load_grid_location_mapping(mapping)
    else:
        raise TypeError(
            "Parameter mapping harus berupa DataFrame, path, folder data, atau None."
        )

    return _merge_grid_locations(
        result,
        _prepare_mapping(mapping_df),
    )


# ============================================================
# 8. ENRICH GRID LOCATIONS
# ============================================================

def enrich_grid_locations(
    df,
    mapping=None,
    data_dir=None,
):

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input df harus berupa pandas DataFrame."
        )

    if "grid_id" not in df.columns:

        raise ValueError(
            "Kolom grid_id tidak ditemukan pada dataset."
        )

    if mapping is None:

        mapping_df = load_grid_location_mapping(
            data_dir
        )

    elif isinstance(mapping, pd.DataFrame):

        mapping_df = _prepare_mapping(mapping)

    elif isinstance(mapping, (str, Path)):

        mapping_df = load_grid_location_mapping(
            mapping
        )

    else:

        raise TypeError(
            "Parameter mapping harus berupa DataFrame, "
            "path, folder data, atau None."
        )

    return _merge_grid_locations(
        df,
        _prepare_mapping(mapping_df),
    )


# ============================================================
# 9. GENERATE GRID ID FROM COORDINATES
# ============================================================

def generate_event_grid_id(df):

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input harus berupa pandas DataFrame."
        )

    missing = [
        column
        for column in [
            "latitude",
            "longitude",
        ]
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Kolom koordinat tidak ditemukan: {missing}"
        )

    result = df.copy()

    result["latitude"] = pd.to_numeric(
        result["latitude"],
        errors="coerce",
    )

    result["longitude"] = pd.to_numeric(
        result["longitude"],
        errors="coerce",
    )

    valid = (
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    )

    result["grid_id"] = pd.Series(
        pd.NA,
        index=result.index,
        dtype="string",
    )

    lat_floor = np.floor(
        result.loc[valid, "latitude"].to_numpy()
    )

    lon_floor = np.floor(
        result.loc[valid, "longitude"].to_numpy()
    )

    result.loc[
        valid,
        "grid_id",
    ] = [
        f"{lat:.1f}_{lon:.1f}"
        for lat, lon in zip(
            lat_floor,
            lon_floor,
        )
    ]

    return result


# ============================================================
# 10. MARINE DATASET PATH
# ============================================================

def resolve_marine_path(data_dir=None):

    folder = _resolve_folder(data_dir)

    if folder.suffix.lower() in (
        ".geojson",
        ".json",
        ".gpkg",
        ".shp",
    ):

        return folder

    return folder / "seavox_indonesia.geojson"


# ============================================================
# 11. AUTOMATIC SEAVOX DOWNLOAD
# ============================================================

def _marine_ssl_context():

    """
    Membuat SSL context dengan CA bundle tepercaya.

    Prioritas:
    1. SSL_CERT_FILE jika ditentukan oleh lingkungan.
    2. CA bundle certifi agar Python di Windows dapat memverifikasi
       sertifikat HTTPS Marine Regions.

    Verifikasi SSL tidak pernah dinonaktifkan.
    """

    ca_bundle = os.environ.get("SSL_CERT_FILE")

    if not ca_bundle:

        try:
            import certifi

        except ImportError as exc:

            raise RuntimeError(
                "Paket certifi belum tersedia. Jalankan perintah: "
                "python -m pip install --upgrade certifi"
            ) from exc

        ca_bundle = certifi.where()

    ca_path = Path(ca_bundle).expanduser()

    if not ca_path.is_file():

        raise FileNotFoundError(
            "File sertifikat CA tidak ditemukan: "
            f"{ca_path}. Periksa SSL_CERT_FILE atau instal ulang certifi."
        )

    return ssl.create_default_context(
        cafile=str(ca_path)
    )


def _download_marine_areas(marine_file):

    marine_file = Path(marine_file)

    marine_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Sertifikat CA dibuat satu kali untuk seluruh halaman WFS.
    ssl_context = _marine_ssl_context()

    page_size = 1000

    max_pages = 20

    start_index = 0

    all_features = []

    seen_ids = set()

    matched_count = None

    for _ in range(max_pages):

        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": MARINE_WFS_LAYER,
            "outputFormat": "application/json",
            "srsName": "CRS:84",
            "bbox": MARINE_BBOX,
            "count": page_size,
            "startIndex": start_index,
        }

        request = Request(
            MARINE_WFS_URL + "?" + urlencode(params),
            headers={
                "User-Agent": "QuakeReady-Seismic-Research/1.0",
                "Accept": "application/json",
            },
        )

        try:

            with urlopen(
                request,
                timeout=120,
                context=ssl_context,
            ) as response:

                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except URLError as exc:

            reason = getattr(exc, "reason", None)

            if isinstance(
                reason,
                ssl.SSLCertVerificationError,
            ):

                raise RuntimeError(
                    "Verifikasi sertifikat SSL Marine Regions gagal. "
                    "Perbarui CA bundle dengan perintah "
                    "'python -m pip install --upgrade certifi', "
                    "lalu jalankan ulang aplikasi. "
                    "Jika jaringan menggunakan proxy perusahaan/kampus, "
                    "atur SSL_CERT_FILE ke sertifikat CA resmi jaringan. "
                    "Verifikasi SSL tetap diaktifkan."
                ) from exc

            raise RuntimeError(
                "Gagal mengakses layanan WFS Marine Regions: "
                f"{exc}"
            ) from exc

        except ssl.SSLCertVerificationError as exc:

            raise RuntimeError(
                "Verifikasi sertifikat SSL Marine Regions gagal. "
                "Perbarui CA bundle dengan perintah "
                "'python -m pip install --upgrade certifi'. "
                "Verifikasi SSL tetap diaktifkan."
            ) from exc

        if (
            not isinstance(payload, dict)
            or "features" not in payload
        ):

            raise ValueError(
                "Marine Regions tidak mengembalikan GeoJSON FeatureCollection."
            )

        features = payload.get("features") or []

        if not features:
            break

        for feature in features:

            properties = feature.get("properties") or {}

            feature_id = (
                feature.get("id")
                or properties.get("MRGID")
                or properties.get("mrgid")
            )

            if feature_id is None:

                feature_id = json.dumps(
                    feature,
                    sort_keys=True,
                )

            if str(feature_id) not in seen_ids:

                seen_ids.add(str(feature_id))

                all_features.append(feature)

        start_index += len(features)

        try:

            matched_count = int(
                payload.get("numberMatched")
            )

        except (TypeError, ValueError):

            matched_count = None

        if (
            matched_count is not None
            and start_index >= matched_count
        ):

            break

        if (
            len(features) < page_size
            and matched_count is None
        ):

            break

    else:

        if (
            matched_count is not None
            and start_index < matched_count
        ):

            raise RuntimeError(
                "Unduhan SeaVoX belum lengkap: batas halaman terlampaui."
            )

    if not all_features:

        raise ValueError(
            "Tidak ada polygon SeaVoX yang diterima untuk wilayah Indonesia."
        )

    geojson = {
        "type": "FeatureCollection",
        "name": "SeaVoX_v19_Indonesia",
        "features": all_features,
    }

    temp_file = marine_file.with_suffix(
        marine_file.suffix + ".tmp"
    )

    with temp_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            geojson,
            file,
            ensure_ascii=False,
        )

    temp_file.replace(marine_file)

    return marine_file


# ============================================================
# 12. MARINE COLUMN DETECTION
# ============================================================

def _find_marine_column(columns, candidates):

    lookup = {
        "".join(
            char.lower()
            for char in str(column)
            if char.isalnum()
        ): column
        for column in columns
    }

    for candidate in candidates:

        key = "".join(
            char.lower()
            for char in candidate
            if char.isalnum()
        )

        if key in lookup:
            return lookup[key]

    return None


def _marine_type_priority(value):

    text = str(value).lower()

    if "sub-region" in text or "subregion" in text:
        return 0

    if "level 4" in text:
        return 1

    if "level 3" in text:
        return 2

    if "level 2" in text:
        return 3

    if "level 1" in text:
        return 4

    if "subocean" in text:
        return 5

    if "region" in text:
        return 6

    return 7


def _translate_marine_name(value):

    name = str(value).strip()

    translations = {
        "java sea": "Laut Jawa",
        "bali sea": "Laut Bali",
        "flores sea": "Laut Flores",
        "banda sea": "Laut Banda",
        "arafura sea": "Laut Arafura",
        "timor sea": "Laut Timor",
        "sulawesi sea": "Laut Sulawesi",
        "celebes sea": "Laut Sulawesi",
        "makassar strait": "Selat Makassar",
        "sunda strait": "Selat Sunda",
        "lombok strait": "Selat Lombok",
        "karimata strait": "Selat Karimata",
        "malacca strait": "Selat Malaka",
        "halmahera sea": "Laut Halmahera",
        "molucca sea": "Laut Maluku",
        "seram sea": "Laut Seram",
        "savu sea": "Laut Sawu",
        "indian ocean": "Samudra Hindia",
        "pacific ocean": "Samudra Pasifik",
        "philippine sea": "Laut Filipina",
        "south china sea": "Laut Cina Selatan",
    }

    return translations.get(
        name.casefold(),
        name,
    )


# ============================================================
# 13. LOAD SEAVOX POLYGONS
# ============================================================

@lru_cache(maxsize=2)
def _load_marine_cached(
    path_text,
    modified_ns,
    file_size,
):

    del modified_ns, file_size

    # Geopandas hanya dimuat ketika pemrosesan polygon benar-benar diminta.
    import geopandas as gpd

    marine = gpd.read_file(path_text)

    if marine.empty:

        raise ValueError(
            "Dataset SeaVoX kosong."
        )

    marine.columns = (
        marine.columns.astype(str).str.strip()
    )

    if marine.crs is None:

        marine = marine.set_crs("EPSG:4326")

    else:

        marine = marine.to_crs("EPSG:4326")

    name_col = _find_marine_column(
        marine.columns,
        [
            "preferredGazetteerName",
            "preferredName",
            "gazetteerName",
            "placeName",
            "name",
        ],
    )

    type_col = _find_marine_column(
        marine.columns,
        [
            "placeType",
            "place_type",
            "type",
        ],
    )

    if name_col is None or type_col is None:

        raise ValueError(
            "Kolom preferredGazetteerName/placeType "
            "tidak ditemukan pada SeaVoX. "
            f"Kolom tersedia: {marine.columns.tolist()}"
        )

    marine["_marine_name"] = (
        marine[name_col]
        .astype("string")
        .str.strip()
    )

    marine["_marine_type"] = (
        marine[type_col]
        .astype("string")
        .str.strip()
    )

    # Hanya SeaVoX SeaArea.
    # Sungai dan danau tidak boleh dianggap sebagai laut.

    marine = marine[
        marine["_marine_type"].str.contains(
            "SeaVoX SeaArea",
            case=False,
            regex=False,
            na=False,
        )
    ].copy()

    marine = marine.dropna(
        subset=[
            "_marine_name",
            "geometry",
        ]
    )

    marine = marine[
        marine.geometry.notna()
        & ~marine.geometry.is_empty
        & marine["_marine_name"].astype(str).str.strip().ne("")
    ].copy()

    if marine.empty:

        raise ValueError(
            "Tidak ada polygon SeaVoX SeaArea yang valid."
        )

    invalid = ~marine.geometry.is_valid

    if invalid.any():

        try:

            from shapely import make_valid

            repair = make_valid

        except ImportError:

            repair = lambda geometry: geometry.buffer(0)

        marine.loc[
            invalid,
            "geometry",
        ] = marine.loc[
            invalid,
            "geometry",
        ].apply(repair)

    marine = marine[
        marine.geometry.notna()
        & ~marine.geometry.is_empty
        & marine.geometry.geom_type.isin(
            [
                "Polygon",
                "MultiPolygon",
            ]
        )
    ].copy()

    if marine.empty:

        raise ValueError(
            "Polygon SeaVoX tidak memiliki geometri polygon yang valid."
        )

    marine["_type_priority"] = (
        marine["_marine_type"]
        .map(_marine_type_priority)
    )

    marine["_area_km2"] = (
        marine.to_crs("EPSG:6933")
        .geometry.area.to_numpy()
        / 1_000_000
    )

    return marine[
        [
            "_marine_name",
            "_marine_type",
            "_type_priority",
            "_area_km2",
            "geometry",
        ]
    ].reset_index(drop=True)


def load_marine_areas(data_dir=None):

    path = resolve_marine_path(data_dir)

    if not path.exists():

        _download_marine_areas(path)

    stat = path.stat()

    return _load_marine_cached(
        str(path.resolve()),
        stat.st_mtime_ns,
        stat.st_size,
    ).copy()


# ============================================================
# 14. APPLY MARINE LOCATION
# ============================================================

def _apply_marine_locations(
    result,
    pending_mask,
    data_dir=None,
):

    if not pending_mask.any():
        return result

    pending = result.loc[
        pending_mask,
        [
            "latitude",
            "longitude",
        ],
    ].copy()

    pending["_event_row_id"] = pending.index

    try:

        marine = load_marine_areas(data_dir)

    except Exception as exc:

        warnings.warn(
            "Polygon SeaVoX tidak dapat dimuat; "
            "lokasi yang tidak cocok dengan BIG "
            "tetap ditampilkan sebagai belum teridentifikasi. "
            f"Detail: {exc}",
            RuntimeWarning,
        )

        return result

    import geopandas as gpd

    points = gpd.GeoDataFrame(
        pending[["_event_row_id"]].copy(),

        geometry=gpd.points_from_xy(
            pending["longitude"],
            pending["latitude"],
        ),

        crs="EPSG:4326",
    )

    try:

        joined = gpd.sjoin(
            points,
            marine,
            how="inner",
            predicate="intersects",
        )

    except Exception as exc:

        warnings.warn(
            f"Spatial join SeaVoX gagal: {exc}",
            RuntimeWarning,
        )

        return result

    if joined.empty:
        return result

    joined = joined.sort_values(
        [
            "_event_row_id",
            "_type_priority",
            "_area_km2",
        ],
        ascending=[
            True,
            True,
            True,
        ],
        kind="stable",
    )

    best = joined.drop_duplicates(
        subset="_event_row_id",
        keep="first",
    )

    for _, row in best.iterrows():

        row_id = int(
            row["_event_row_id"]
        )

        name = _translate_marine_name(
            row["_marine_name"]
        )

        result.at[
            row_id,
            "jenis_lokasi_episenter",
        ] = "Perairan"

        result.at[
            row_id,
            "lokasi_episenter_perairan",
        ] = name

        result.at[
            row_id,
            "lokasi_episenter",
        ] = name

        result.at[
            row_id,
            "status_lokasi_episenter",
        ] = "Titik episenter cocok dengan polygon SeaVoX v19."

        result.at[
            row_id,
            "sumber_identifikasi_lokasi",
        ] = "Marine Regions — SeaVoX v19"

    return result


# ============================================================
# 15. ADD EVENT LOCATION
# ============================================================

def add_event_location(
    df,
    data_dir=None,
    boundary_file=None,
):

    """Identifikasi episenter dengan BIG; titik yang tidak cocok diperiksa ke SeaVoX."""

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input harus berupa pandas DataFrame."
        )

    result = df.copy().reset_index(drop=True)

    for column in [
        "latitude",
        "longitude",
    ]:

        if column not in result.columns:

            raise ValueError(
                f"Kolom {column} wajib tersedia."
            )

        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    valid = (
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    )

    result["_coordinate_valid"] = valid

    result = generate_event_grid_id(result)

    result = result.drop(
        columns=[
            column
            for column in EVENT_LOCATION_COLUMNS
            if column in result.columns
        ],
        errors="ignore",
    )

    # BIG grid mapping tetap digunakan seperti sebelumnya.

    result = add_grid_location(
        result,
        data_dir=data_dir,
    )

    result["_event_row_id"] = np.arange(
        len(result)
    )

    # --------------------------------------------------------
    # INITIALIZE EVENT LOCATION
    # --------------------------------------------------------

    result["lokasi_episenter_kabupaten_kota"] = pd.NA

    result["lokasi_episenter_provinsi"] = pd.NA

    result["jumlah_kabupaten_episenter"] = 0

    result["lokasi_episenter"] = (
        "Tidak teridentifikasi pada polygon BIG maupun SeaVoX."
    )

    result["status_lokasi_episenter"] = (
        "Belum teridentifikasi"
    )

    result["jenis_lokasi_episenter"] = (
        "Belum teridentifikasi"
    )

    result["lokasi_episenter_perairan"] = pd.NA

    result["sumber_identifikasi_lokasi"] = pd.NA

    # --------------------------------------------------------
    # INVALID COORDINATES
    # --------------------------------------------------------

    invalid = ~result["_coordinate_valid"]

    result.loc[
        invalid,
        "lokasi_episenter",
    ] = "Koordinat episenter tidak valid"

    result.loc[
        invalid,
        "status_lokasi_episenter",
    ] = "Koordinat tidak valid"

    result.loc[
        invalid,
        "jenis_lokasi_episenter",
    ] = "Koordinat tidak valid"

    result.loc[
        invalid,
        "sumber_identifikasi_lokasi",
    ] = "Tidak tersedia — koordinat tidak valid"

    # --------------------------------------------------------
    # BIG SPATIAL JOIN
    # --------------------------------------------------------

    valid_points = result.loc[
        valid,
        [
            "_event_row_id",
            "latitude",
            "longitude",
        ],
    ].copy()

    if not valid_points.empty:

        import geopandas as gpd

        points = gpd.GeoDataFrame(
            valid_points[["_event_row_id"]].copy(),

            geometry=gpd.points_from_xy(
                valid_points["longitude"],
                valid_points["latitude"],
            ),

            crs="EPSG:4326",
        )

        admin = load_admin_boundaries(
            boundary_file
        )

        joined = gpd.sjoin(
            points,
            admin,
            how="left",
            predicate="intersects",
        )

        def join_unique(values):

            unique = sorted(
                set(
                    values.dropna().astype(str)
                )
            )

            return (
                " / ".join(unique)
                if unique
                else pd.NA
            )

        summary = joined.groupby(
            "_event_row_id"
        ).agg(
            _spatial_kabupaten=(
                "kabupaten_kota",
                join_unique,
            ),

            _spatial_provinsi=(
                "provinsi",
                join_unique,
            ),

            _spatial_jumlah=(
                "kabupaten_kota",
                lambda values: values.dropna().nunique(),
            ),
        )

        result = result.merge(
            summary,
            left_on="_event_row_id",
            right_index=True,
            how="left",
            validate="one_to_one",
            sort=False,
        )

        result["lokasi_episenter_kabupaten_kota"] = (
            result["_spatial_kabupaten"]
        )

        result["lokasi_episenter_provinsi"] = (
            result["_spatial_provinsi"]
        )

        result["jumlah_kabupaten_episenter"] = (
            pd.to_numeric(
                result["_spatial_jumlah"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        result = result.drop(
            columns=[
                "_spatial_kabupaten",
                "_spatial_provinsi",
                "_spatial_jumlah",
            ],
            errors="ignore",
        )

    # --------------------------------------------------------
    # NORMALIZE BIG RESULTS
    # --------------------------------------------------------

    result["jumlah_kabupaten_episenter"] = (
        pd.to_numeric(
            result["jumlah_kabupaten_episenter"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    matched = (
        result["jumlah_kabupaten_episenter"].gt(0)
    )

    # --------------------------------------------------------
    # LAND LOCATION — KEEP BIG RESULT
    # --------------------------------------------------------

    result.loc[
        matched,
        "lokasi_episenter",
    ] = (
        result.loc[
            matched,
            "lokasi_episenter_kabupaten_kota",
        ].astype(str)
        + ", "
        + result.loc[
            matched,
            "lokasi_episenter_provinsi",
        ].astype(str)
    )

    result.loc[
        matched,
        "status_lokasi_episenter",
    ] = (
        "Titik episenter teridentifikasi dalam polygon administrasi BIG"
    )

    result.loc[
        matched,
        "jenis_lokasi_episenter",
    ] = "Daratan administratif"

    result.loc[
        matched,
        "sumber_identifikasi_lokasi",
    ] = (
        "Badan Informasi Geospasial (BIG) — polygon administrasi"
    )

    multiple = (
        result["jumlah_kabupaten_episenter"].gt(1)
    )

    result.loc[
        multiple,
        "status_lokasi_episenter",
    ] = (
        "Titik episenter beririsan dengan beberapa polygon administrasi"
    )

    # --------------------------------------------------------
    # MARINE LOCATION — ONLY UNMATCHED BIG POINTS
    # --------------------------------------------------------

    marine_pending = (
        valid & ~matched
    )

    result = _apply_marine_locations(
        result,
        marine_pending,
        data_dir=data_dir,
    )

    # --------------------------------------------------------
    # FALLBACK — NO POLYGON MATCH
    # --------------------------------------------------------

    still_unmatched = (
        valid
        & ~matched
        & result["lokasi_episenter_perairan"].isna()
    )

    if still_unmatched.any():

        coordinates = result.loc[
            still_unmatched,
            [
                "latitude",
                "longitude",
            ],
        ].apply(
            lambda row: (
                f"{abs(float(row['latitude'])):.4f}° "
                f"{'LU' if float(row['latitude']) >= 0 else 'LS'}, "
                f"{abs(float(row['longitude'])):.4f}° "
                f"{'BT' if float(row['longitude']) >= 0 else 'BB'}"
            ),
            axis=1,
        )

        result.loc[
            still_unmatched,
            "lokasi_episenter",
        ] = (
            "Wilayah belum teridentifikasi ("
            + coordinates
            + ")"
        )

        result.loc[
            still_unmatched,
            "status_lokasi_episenter",
        ] = (
            "Koordinat valid, tetapi tidak cocok dengan "
            "polygon administrasi BIG maupun polygon SeaVoX yang tersedia"
        )

        result.loc[
            still_unmatched,
            "sumber_identifikasi_lokasi",
        ] = (
            "Koordinat BMKG; tidak ada polygon yang cocok"
        )

    # --------------------------------------------------------
    # CLEAN INTERNAL COLUMNS
    # --------------------------------------------------------

    result = result.drop(
        columns=[
            "_coordinate_valid",
            "_event_row_id",
        ],
        errors="ignore",
    )

    return result


# ============================================================
# 16. GET SINGLE GRID LOCATION
# ============================================================

def get_grid_location(grid_id, data_dir=None):

    mapping = load_grid_location_mapping(
        data_dir
    )

    selected = mapping[
        mapping["grid_id"].astype(str).str.strip()
        == str(grid_id).strip()
    ]

    return (
        None
        if selected.empty
        else selected.iloc[0].to_dict()
    )


# ============================================================
# 17. BACKWARD COMPATIBILITY
# ============================================================

def grid_location(value, data_dir=None):

    if isinstance(value, pd.DataFrame):

        return add_grid_location(
            value,
            data_dir=data_dir,
        )

    return get_grid_location(
        value,
        data_dir=data_dir,
    )


# ============================================================
# 18. PUBLIC FUNCTIONS
# ============================================================

__all__ = [
    "GRID_LOCATION_EXPLANATION",
    "load_grid_location_mapping",
    "load_admin_boundaries",
    "load_marine_areas",
    "add_grid_location",
    "add_event_grid_reference",
    "enrich_grid_locations",
    "generate_event_grid_id",
    "add_event_location",
    "get_grid_location",
    "grid_location",
]

