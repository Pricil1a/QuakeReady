# ============================================================
# BUILD GRID LOCATION MAPPING
# QuakeReady - VS CODE VERSION
# Source: BIG Administrative Boundary Polygon
# ============================================================

from pathlib import Path
import requests
import json
import pandas as pd
import geopandas as gpd
import numpy as np

from shapely.geometry import box

# ============================================================
# 1. PROJECT PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"

HISTORICAL_FILE = (
    DATA_DIR / "QuakeReady_Historis_1998_2024.csv"
)

BOUNDARY_FILE = (
    DATA_DIR / "batas_kabupaten.geojson"
)

OUTPUT_FILE = (
    DATA_DIR / "grid_location_mapping.csv"
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

print("=" * 60)
print("QUAKEREADY - GRID LOCATION MAPPING")
print("=" * 60)

print("Project:", ROOT)
print("Data:", DATA_DIR)

# ============================================================
# 2. LOAD GRID DATA
# ============================================================

if not HISTORICAL_FILE.exists():
    raise FileNotFoundError(
        f"Dataset tidak ditemukan: {HISTORICAL_FILE}"
    )

df = pd.read_csv(HISTORICAL_FILE)

if "grid_id" not in df.columns:
    raise ValueError(
        "Kolom grid_id tidak ditemukan dalam dataset historis."
    )

grids = (
    df[["grid_id"]]
    .dropna()
    .drop_duplicates()
    .copy()
)

grids["grid_id"] = grids["grid_id"].astype(str)

if len(grids) != 810:
    raise ValueError(
        f"Jumlah grid yang ditemukan {len(grids)}, "
        "seharusnya 810. Periksa dataset historis."
    )

if grids["grid_id"].duplicated().any():
    raise ValueError("Terdapat grid_id duplikat.")

# ============================================================
# 3. PARSE GRID ID
# ============================================================

parts = grids["grid_id"].str.split(
    "_",
    expand=True
)

if parts.shape[1] != 2:
    raise ValueError(
        "Format grid_id harus latitude_min_longitude_min."
    )

grids["lat_min"] = pd.to_numeric(
    parts[0],
    errors="raise"
)

grids["lon_min"] = pd.to_numeric(
    parts[1],
    errors="raise"
)

# Titik pusat geometris grid 1 x 1 derajat
grids["latitude"] = (
    grids["lat_min"] + 0.5
)

grids["longitude"] = (
    grids["lon_min"] + 0.5
)

print("\nJumlah grid:", len(grids))

# ============================================================
# 4. DOWNLOAD POLYGON ADMINISTRASI BIG
# ============================================================

BIG_URL = (
    "https://geoservices.big.go.id/gis/rest/services/"
    "DISIGT/BatasWilayah/FeatureServer/0/query"
)

session = requests.Session()

print("\nMenghubungi layanan BIG...")

response = session.get(
    BIG_URL,
    params={
        "where": "1=1",
        "returnIdsOnly": "true",
        "f": "json"
    },
    timeout=120
)

response.raise_for_status()

id_result = response.json()

if "error" in id_result:
    raise RuntimeError(
        f"BIG API Error: {id_result['error']}"
    )

object_ids = id_result.get("objectIds", [])

if not object_ids:
    raise RuntimeError(
        "BIG tidak mengembalikan ID polygon."
    )

print(
    "Jumlah ID administrasi dari BIG:",
    len(object_ids)
)

# ============================================================
# 5. DOWNLOAD SELURUH POLYGON SECARA BATCH
# ============================================================

features = []

BATCH_SIZE = 500

for start in range(
    0,
    len(object_ids),
    BATCH_SIZE
):

    batch = object_ids[
        start:start + BATCH_SIZE
    ]

    response = session.get(
        BIG_URL,
        params={
            "objectIds": ",".join(
                map(str, batch)
            ),
            "outFields": "wadmkk,wadmpr",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson"
        },
        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    if "error" in result:
        raise RuntimeError(
            f"BIG API Error: {result['error']}"
        )

    batch_features = result.get(
        "features",
        []
    )

    features.extend(batch_features)

    print(
        f"Download: {len(features)} / {len(object_ids)}"
    )

if not features:
    raise RuntimeError(
        "Tidak ada polygon yang berhasil diunduh."
    )

# ============================================================
# 6. SAVE GEOJSON
# ============================================================

geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open(
    BOUNDARY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geojson,
        f,
        ensure_ascii=False
    )

print("\nPolygon berhasil disimpan:")
print(BOUNDARY_FILE)

# ============================================================
# 7. LOAD GEOJSON
# ============================================================

admin = gpd.read_file(
    BOUNDARY_FILE
)

if admin.crs is None:
    raise ValueError(
        "CRS polygon administrasi tidak tersedia."
    )

if not {
    "wadmkk",
    "wadmpr"
}.issubset(admin.columns):

    raise ValueError(
        f"Kolom administrasi tidak lengkap: "
        f"{admin.columns.tolist()}"
    )

admin = admin[
    [
        "wadmkk",
        "wadmpr",
        "geometry"
    ]
].copy()

admin = admin.rename(
    columns={
        "wadmkk": "kabupaten_kota",
        "wadmpr": "provinsi"
    }
)

admin = admin.dropna(
    subset=[
        "kabupaten_kota",
        "provinsi",
        "geometry"
    ]
).to_crs("EPSG:4326")

admin = admin[
    (~admin.geometry.is_empty)
    &
    (admin.geometry.notna())
].copy()

# ============================================================
# 8. GEOMETRY VALIDATION
# ============================================================

admin["geometry"] = (
    admin.geometry.make_valid()
)

admin = admin.explode(
    index_parts=False
).reset_index(drop=True)

admin = admin[
    admin.geometry.geom_type.isin([
        "Polygon",
        "MultiPolygon"
    ])
].copy()

admin = admin[
    admin.geometry.is_valid
    &
    (~admin.geometry.is_empty)
].copy()

if admin.empty:
    raise RuntimeError(
        "Tidak ada polygon administrasi yang valid."
    )

print("\nVALIDASI POLYGON")
print("CRS:", admin.crs)
print("Jumlah polygon:", len(admin))

print(
    "Tipe geometri:",
    admin.geometry.geom_type.value_counts().to_dict()
)

# ============================================================
# 9. CREATE GRID POLYGONS
# ============================================================

grid_geometry = [
    box(
        lon,
        lat,
        lon + 1,
        lat + 1
    )
    for lat, lon in zip(
        grids["lat_min"],
        grids["lon_min"]
    )
]

grid_gdf = gpd.GeoDataFrame(
    grids.copy(),
    geometry=grid_geometry,
    crs="EPSG:4326"
)

# ============================================================
# 10. IDENTIFY CENTER LOCATION
# ============================================================

centers = gpd.GeoDataFrame(
    grids[["grid_id"]].copy(),
    geometry=gpd.points_from_xy(
        grids["longitude"],
        grids["latitude"]
    ),
    crs="EPSG:4326"
)

center_join = gpd.sjoin(
    centers,
    admin,
    how="left",
    predicate="within"
)

center_info = (
    center_join
    .dropna(subset=["kabupaten_kota"])
    .groupby("grid_id")
    .agg(
        center_kabupaten=(
            "kabupaten_kota",
            lambda x: " / ".join(
                sorted(set(x.astype(str)))
            )
        ),
        center_provinsi=(
            "provinsi",
            lambda x: " / ".join(
                sorted(set(x.astype(str)))
            )
        )
    )
    .reset_index()
)

# ============================================================
# 11. SPATIAL INTERSECTION
# ============================================================

print("\nMenghitung irisan grid dan kabupaten/kota...")

grid_metric = grid_gdf[
    ["grid_id", "geometry"]
].to_crs("EPSG:6933")

admin_metric = admin[
    [
        "kabupaten_kota",
        "provinsi",
        "geometry"
    ]
].to_crs("EPSG:6933")

overlap = gpd.overlay(
    grid_metric,
    admin_metric,
    how="intersection",
    keep_geom_type=True
)

if not overlap.empty:

    overlap["area_km2"] = (
        overlap.geometry.area / 1_000_000
    )

    overlap = overlap[
        overlap["area_km2"] > 0
    ].copy()

    area_by_region = (
        overlap.groupby(
            [
                "grid_id",
                "kabupaten_kota",
                "provinsi"
            ],
            as_index=False
        )["area_km2"]
        .sum()
    )

    # Seluruh kabupaten/kota yang tercakup
    coverage = (
        area_by_region
        .groupby("grid_id")
        .agg(
            kabupaten_kota_tercakup=(
                "kabupaten_kota",
                lambda x: "; ".join(
                    sorted(set(x.astype(str)))
                )
            ),
            provinsi_tercakup=(
                "provinsi",
                lambda x: "; ".join(
                    sorted(set(x.astype(str)))
                )
            ),
            luas_irisan_total_km2=(
                "area_km2",
                "sum"
            )
        )
        .reset_index()
    )

    # Kabupaten/kota dengan irisan terbesar
    dominant = (
        area_by_region
        .sort_values(
            ["grid_id", "area_km2", "kabupaten_kota"],
            ascending=[True, False, True]
        )
        .drop_duplicates("grid_id")
        .rename(
            columns={
                "kabupaten_kota": "kabupaten_dominan",
                "provinsi": "provinsi_dominan",
                "area_km2": "luas_dominan_km2"
            }
        )[
            [
                "grid_id",
                "kabupaten_dominan",
                "provinsi_dominan",
                "luas_dominan_km2"
            ]
        ]
    )

else:

    coverage = pd.DataFrame(
        columns=[
            "grid_id",
            "kabupaten_kota_tercakup",
            "provinsi_tercakup",
            "luas_irisan_total_km2"
        ]
    )

    dominant = pd.DataFrame(
        columns=[
            "grid_id",
            "kabupaten_dominan",
            "provinsi_dominan",
            "luas_dominan_km2"
        ]
    )

# ============================================================
# 12. MERGE LOCATION INFORMATION
# ============================================================

location = (
    grids
    .merge(
        center_info,
        on="grid_id",
        how="left"
    )
    .merge(
        coverage,
        on="grid_id",
        how="left"
    )
    .merge(
        dominant,
        on="grid_id",
        how="left"
    )
)

# ============================================================
# 13. DETERMINE LOCATION NAME
# ============================================================

def get_location(row):

    if pd.notna(row["center_kabupaten"]):

        return (
            f'{row["center_kabupaten"]}, '
            f'{row["center_provinsi"]}'
        )

    if pd.notna(row["kabupaten_dominan"]):

        return (
            f'Grid mencakup '
            f'{row["kabupaten_dominan"]}, '
            f'{row["provinsi_dominan"]} '
            f'(pusat grid di luar polygon administrasi)'
        )

    return (
        "Tidak teridentifikasi dalam "
        "polygon kabupaten/kota"
    )


def get_area_type(row):

    if pd.notna(row["center_kabupaten"]):
        return "Pusat grid di dalam polygon administrasi"

    if pd.notna(row["kabupaten_dominan"]):
        return (
            "Pusat di luar polygon; "
            "grid beririsan dengan daratan"
        )

    return (
        "Tidak beririsan dengan polygon kabupaten/kota"
    )


location["nama_lokasi"] = location.apply(
    get_location,
    axis=1
)

location["jenis_wilayah"] = location.apply(
    get_area_type,
    axis=1
)

# ============================================================
# 14. FINAL VALIDATION
# ============================================================

assert len(location) == 810

assert location["grid_id"].is_unique

assert location["nama_lokasi"].notna().all()

assert location[
    ["latitude", "longitude"]
].notna().all().all()

# ============================================================
# 15. SAVE GRID LOCATION MAPPING
# ============================================================

output_columns = [
    "grid_id",
    "nama_lokasi",
    "kabupaten_kota_tercakup",
    "provinsi_tercakup",
    "kabupaten_dominan",
    "provinsi_dominan",
    "luas_dominan_km2",
    "luas_irisan_total_km2",
    "jenis_wilayah",
    "latitude",
    "longitude"
]

location = location[
    output_columns
]

location.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# 16. FINAL REPORT
# ============================================================

print("\n" + "=" * 60)
print("GRID LOCATION MAPPING COMPLETED")
print("=" * 60)

print("Total grid:", len(location))

print(
    "Unique grid:",
    location["grid_id"].nunique()
)

print(
    "\nPusat grid di dalam polygon:",
    (
        location["jenis_wilayah"]
        == "Pusat grid di dalam polygon administrasi"
    ).sum()
)

print(
    "\nPusat di luar polygon tetapi grid beririsan:",
    (
        location["jenis_wilayah"]
        == "Pusat di luar polygon; grid beririsan dengan daratan"
    ).sum()
)

print(
    "\nTidak beririsan dengan polygon:",
    (
        location["jenis_wilayah"]
        == "Tidak beririsan dengan polygon kabupaten/kota"
    ).sum()
)

print("\nTOP 15 GRID LOCATION")

print(
    location.head(15).to_string(index=False)
)

print("\nFILE BERHASIL DIBUAT:")
print(BOUNDARY_FILE)
print(OUTPUT_FILE)

print("\nSELESAI.")