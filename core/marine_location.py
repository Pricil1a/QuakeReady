from pathlib import Path
from functools import lru_cache
import re
import warnings

import geopandas as gpd
import pandas as pd


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MARINE_FILE = (
    PROJECT_ROOT
    / "data"
    / "seavox_indonesia.geojson"
)


# ============================================================
# FIELD DETECTION
# ============================================================

NAME_CANDIDATES = (
    "preferredgazetteername",
    "preferredname",
    "gazetteername",
    "placename",
    "name",
    "nameen",
    "englishname",
)

TYPE_CANDIDATES = (
    "placetype",
    "placetype_name",
    "place_type",
    "type",
)


def normalize_column(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower()
    )


def find_column(columns, candidates):

    lookup = {
        normalize_column(col): col
        for col in columns
    }

    for candidate in candidates:

        key = normalize_column(candidate)

        if key in lookup:
            return lookup[key]

    return None


# ============================================================
# INDONESIAN MARINE NAME TRANSLATION
# ============================================================

MARINE_TRANSLATIONS = {

    "java sea": "Laut Jawa",
    "bali sea": "Laut Bali",
    "flores sea": "Laut Flores",
    "banda sea": "Laut Banda",
    "arafura sea": "Laut Arafura",
    "timor sea": "Laut Timor",

    "sulawesi sea": "Laut Sulawesi",
    "celebes sea": "Laut Sulawesi",

    "makassar strait": "Selat Makassar",
    "makasar strait": "Selat Makassar",
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


def display_marine_name(name):

    clean = str(name).strip()

    return MARINE_TRANSLATIONS.get(
        clean.casefold(),
        clean
    )


# ============================================================
# FILE RESOLUTION
# ============================================================

def resolve_marine_file(data_dir=None):

    if data_dir is None:
        return DEFAULT_MARINE_FILE

    path = Path(data_dir).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if path.suffix.lower() in (
        ".geojson",
        ".json",
        ".gpkg",
        ".shp",
    ):
        return path

    return path / "seavox_indonesia.geojson"


# ============================================================
# SELECT MOST SPECIFIC MARINE AREA
# ============================================================

def type_priority(value):

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

    if "region" in text:
        return 5

    if any(
        word in text
        for word in (
            "sea",
            "strait",
            "gulf",
            "bay",
        )
    ):
        return 6

    if "ocean" in text:
        return 7

    return 8


# ============================================================
# LOAD MARINE POLYGONS
# ============================================================

@lru_cache(maxsize=2)
def load_marine_areas_cached(file_path):

    path = Path(file_path)

    if not path.exists():

        raise FileNotFoundError(
            f"Dataset perairan tidak ditemukan: {path}"
        )

    marine = gpd.read_file(path)

    if marine.empty:

        raise ValueError(
            "Dataset polygon perairan kosong."
        )

    marine.columns = (
        marine.columns.astype(str).str.strip()
    )

    if marine.crs is None:

        marine = marine.set_crs("EPSG:4326")

    else:

        marine = marine.to_crs("EPSG:4326")

    # --------------------------------------------------------
    # DETECT COLUMN
    # --------------------------------------------------------

    name_col = find_column(
        marine.columns,
        NAME_CANDIDATES
    )

    type_col = find_column(
        marine.columns,
        TYPE_CANDIDATES
    )

    if name_col is None:

        raise ValueError(
            "Kolom nama perairan tidak ditemukan. "
            f"Kolom tersedia: {marine.columns.tolist()}"
        )

    if type_col is None:

        raise ValueError(
            "Kolom placeType tidak ditemukan. "
            "Pemeriksaan dihentikan agar danau atau sungai "
            "tidak salah disebut laut."
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

    # --------------------------------------------------------
    # FILTER SEA AREAS
    # --------------------------------------------------------

    marine_mask = marine["_marine_type"].str.contains(
        r"seavox\s*seaarea|\bsea\b|\bocean\b|"
        r"\bstrait\b|\bgulf\b|\bbay\b|"
        r"\bchannel\b|\bsound\b|\bpassage\b",
        case=False,
        regex=True,
        na=False,
    )

    marine = marine.loc[
        marine_mask
    ].copy()

    marine = marine.dropna(
        subset=[
            "_marine_name",
            "geometry"
        ]
    )

    marine = marine[
        marine.geometry.notna()
        & ~marine.geometry.is_empty
        & marine["_marine_name"].astype(str).str.strip().ne("")
    ].copy()

    if marine.empty:

        raise ValueError(
            "Tidak ada polygon laut yang sesuai "
            "dengan filter SeaVoX."
        )

    # --------------------------------------------------------
    # REPAIR INVALID GEOMETRY
    # --------------------------------------------------------

    invalid = ~marine.geometry.is_valid

    if invalid.any():

        try:
            from shapely import make_valid

        except ImportError:
            from shapely.validation import make_valid

        marine.loc[
            invalid,
            "geometry"
        ] = marine.loc[
            invalid,
            "geometry"
        ].apply(make_valid)

    marine = marine[
        marine.geometry.geom_type.isin(
            ["Polygon", "MultiPolygon"]
        )
        & marine.geometry.notna()
        & ~marine.geometry.is_empty
    ].copy()

    if marine.empty:

        raise ValueError(
            "Tidak terdapat polygon laut yang valid."
        )

    # --------------------------------------------------------
    # PRIORITY AND AREA
    # --------------------------------------------------------

    marine["_type_priority"] = (
        marine["_marine_type"]
        .map(type_priority)
    )

    marine["_area_km2"] = (
        marine.to_crs("EPSG:6933")
        .geometry.area
        .to_numpy()
        / 1_000_000
    )

    marine = marine[
        [
            "_marine_name",
            "_marine_type",
            "_type_priority",
            "_area_km2",
            "geometry",
        ]
    ].reset_index(drop=True)

    return marine


# ============================================================
# COORDINATE FORMAT
# ============================================================

def format_coordinate(latitude, longitude):

    lat_dir = "LU" if latitude >= 0 else "LS"

    lon_dir = "BT" if longitude >= 0 else "BB"

    return (
        f"{abs(latitude):.4f}° {lat_dir}, "
        f"{abs(longitude):.4f}° {lon_dir}"
    )


# ============================================================
# MAIN FUNCTION
# ============================================================

def add_marine_location(df, data_dir=None):

    """
    Mengidentifikasi lokasi episenter perairan.

    Tidak mengubah hasil identifikasi daratan BIG.

    Jika polygon laut belum tersedia atau tidak cocok,
    koordinat tetap ditampilkan sebagai fallback.
    """

    if not isinstance(df, pd.DataFrame):

        raise TypeError(
            "Input harus berupa pandas DataFrame."
        )

    result = df.copy().reset_index(drop=True)

    if (
        "latitude" not in result.columns
        or "longitude" not in result.columns
    ):

        raise ValueError(
            "Kolom latitude dan longitude wajib tersedia."
        )

    result["latitude"] = pd.to_numeric(
        result["latitude"],
        errors="coerce"
    )

    result["longitude"] = pd.to_numeric(
        result["longitude"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # INITIALIZE OUTPUT
    # --------------------------------------------------------

    result["jenis_lokasi_episenter"] = pd.NA

    result["lokasi_episenter_perairan"] = pd.NA

    result["sumber_identifikasi_lokasi"] = pd.NA

    if "lokasi_episenter" not in result.columns:
        result["lokasi_episenter"] = pd.NA

    if "status_lokasi_episenter" not in result.columns:
        result["status_lokasi_episenter"] = pd.NA

    # --------------------------------------------------------
    # VALIDATE COORDINATES
    # --------------------------------------------------------

    valid = (
        result["latitude"].between(-90, 90)
        & result["longitude"].between(-180, 180)
    )

    # --------------------------------------------------------
    # IDENTIFY LAND EVENTS
    # --------------------------------------------------------

    land = pd.Series(
        False,
        index=result.index
    )

    if "jumlah_kabupaten_episenter" in result.columns:

        land |= (
            pd.to_numeric(
                result["jumlah_kabupaten_episenter"],
                errors="coerce"
            )
            .fillna(0)
            .gt(0)
        )

    for column in (
        "lokasi_episenter_kabupaten_kota",
        "lokasi_episenter_provinsi",
    ):

        if column in result.columns:

            land |= (
                result[column].notna()
                & result[column].astype("string").str.strip().ne("")
            )

    # --------------------------------------------------------
    # KEEP BIG RESULT
    # --------------------------------------------------------

    result.loc[
        land,
        "jenis_lokasi_episenter"
    ] = "Daratan administratif"

    result.loc[
        land,
        "sumber_identifikasi_lokasi"
    ] = "BIG — polygon administrasi kabupaten/kota"

    # --------------------------------------------------------
    # INVALID COORDINATES
    # --------------------------------------------------------

    invalid = ~valid

    result.loc[
        invalid,
        "jenis_lokasi_episenter"
    ] = "Koordinat tidak valid"

    result.loc[
        invalid,
        "lokasi_episenter"
    ] = "Koordinat episenter tidak valid"

    result.loc[
        invalid,
        "status_lokasi_episenter"
    ] = "Koordinat tidak valid"

    result.loc[
        invalid,
        "sumber_identifikasi_lokasi"
    ] = "Tidak tersedia — koordinat tidak valid"

    # --------------------------------------------------------
    # EVENTS NOT IDENTIFIED ON LAND
    # --------------------------------------------------------

    pending = valid & ~land

    if not pending.any():
        return result

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    for idx in result.index[pending]:

        coord = format_coordinate(
            float(result.at[idx, "latitude"]),
            float(result.at[idx, "longitude"])
        )

        result.at[
            idx,
            "jenis_lokasi_episenter"
        ] = "Belum teridentifikasi"

        result.at[
            idx,
            "lokasi_episenter"
        ] = (
            f"Wilayah belum teridentifikasi ({coord})"
        )

        result.at[
            idx,
            "status_lokasi_episenter"
        ] = (
            "Koordinat valid; belum cocok dengan "
            "polygon administrasi BIG atau polygon perairan."
        )

        result.at[
            idx,
            "sumber_identifikasi_lokasi"
        ] = (
            "Koordinat BMKG; polygon perairan belum dicocokkan"
        )

    # --------------------------------------------------------
    # LOAD MARINE DATA
    # --------------------------------------------------------

    marine_file = resolve_marine_file(
        data_dir
    )

    if not marine_file.exists():

        result.loc[
            pending,
            "status_lokasi_episenter"
        ] = (
            "Dataset SeaVoX belum tersedia; "
            "lokasi ditampilkan berdasarkan koordinat."
        )

        return result

    try:

        marine = load_marine_areas_cached(
            str(marine_file.resolve())
        ).copy()

    except Exception as exc:

        warnings.warn(
            f"Polygon SeaVoX gagal dimuat: {exc}",
            RuntimeWarning
        )

        result.loc[
            pending,
            "status_lokasi_episenter"
        ] = (
            "Dataset SeaVoX gagal dibaca; "
            "koordinat tetap ditampilkan."
        )

        result.loc[
            pending,
            "sumber_identifikasi_lokasi"
        ] = "Koordinat BMKG; SeaVoX gagal dimuat"

        return result

    # --------------------------------------------------------
    # CREATE EVENT POINTS
    # --------------------------------------------------------

    points_df = result.loc[
        pending,
        ["latitude", "longitude"]
    ].copy()

    points_df["_event_row_id"] = points_df.index

    points = gpd.GeoDataFrame(
        points_df[["_event_row_id"]],

        geometry=gpd.points_from_xy(
            points_df["longitude"],
            points_df["latitude"]
        ),

        crs="EPSG:4326"
    )

    # --------------------------------------------------------
    # SPATIAL JOIN
    # --------------------------------------------------------

    try:

        joined = gpd.sjoin(
            points,
            marine,
            how="inner",
            predicate="intersects"
        )

    except Exception as exc:

        warnings.warn(
            f"Spatial join laut gagal: {exc}",
            RuntimeWarning
        )

        result.loc[
            pending,
            "status_lokasi_episenter"
        ] = (
            "Pencocokan polygon perairan gagal; "
            "koordinat tetap ditampilkan."
        )

        return result

    if joined.empty:
        return result

    # --------------------------------------------------------
    # SELECT MOST SPECIFIC MATCH
    # --------------------------------------------------------

    joined = joined.sort_values(
        [
            "_event_row_id",
            "_type_priority",
            "_area_km2"
        ],
        ascending=[
            True,
            True,
            True
        ],
        kind="stable"
    )

    best = joined.drop_duplicates(
        subset="_event_row_id",
        keep="first"
    )

    # --------------------------------------------------------
    # APPLY MARINE LOCATION
    # --------------------------------------------------------

    for _, row in best.iterrows():

        row_id = int(row["_event_row_id"])

        sea_name = display_marine_name(
            row["_marine_name"]
        )

        result.at[
            row_id,
            "jenis_lokasi_episenter"
        ] = "Perairan"

        result.at[
            row_id,
            "lokasi_episenter_perairan"
        ] = sea_name

        result.at[
            row_id,
            "lokasi_episenter"
        ] = sea_name

        result.at[
            row_id,
            "status_lokasi_episenter"
        ] = (
            "Titik episenter cocok dengan "
            "polygon perairan SeaVoX v19."
        )

        result.at[
            row_id,
            "sumber_identifikasi_lokasi"
        ] = (
            "Marine Regions / SeaVoX v19 (2023)"
        )

    return result