import json
import re
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd


BASE_URL = "https://www.zillow.com"
NORTHWESTERN_TECH_NAME = "Northwestern Tech"
NORTHWESTERN_TECH_LATITUDE = 42.0579
NORTHWESTERN_TECH_LONGITUDE = -87.6752
NUMERIC_FEATURES = [
    "beds",
    "baths",
    "area",
    "distance_from_northwestern_tech",
]
CATEGORICAL_FEATURES = []
BOOLEAN_FEATURES = []
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES


def first_non_null(*values):
    for value in values:
        if value is not None:
            return value
    return None


def normalize_baths(value):
    return 1 if value in (None, "") else value


def numeric_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    match = re.search(r"[\d,]+", str(value))
    if not match:
        return None

    return int(match.group(0).replace(",", ""))


def normalize_url(url):
    if not url:
        return ""
    url = str(url)
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{BASE_URL}{url}"
    return f"{BASE_URL}/{url}"


def first_photo_url(raw_listing):
    img_src = raw_listing.get("imgSrc")
    if img_src:
        return str(img_src)

    carousel = raw_listing.get("carouselPhotosComposable", {})
    base_url = carousel.get("baseUrl")
    photo_data = carousel.get("photoData") or []
    if base_url and photo_data:
        photo_key = photo_data[0].get("photoKey")
        if photo_key:
            return str(base_url).replace("{photoKey}", str(photo_key))

    return ""


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_miles * c


def distance_from_northwestern_tech(latitude, longitude):
    if latitude is None or longitude is None:
        return None

    return round(
        haversine_miles(
            float(latitude),
            float(longitude),
            NORTHWESTERN_TECH_LATITUDE,
            NORTHWESTERN_TECH_LONGITUDE,
        ),
        3,
    )


def resolve_json_path() -> Path:
    candidates = [
        Path("data/zillow_evanston_all.json"),
        Path("fb_data/zillow_evanston_all.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find zillow_evanston_all.json in data/ or fb_data/."
    )


def resolve_csv_path() -> Path:
    candidates = [
        Path("data/zillow_evanston_all.csv"),
        Path("fb_data/zillow_evanston_all.csv"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find zillow_evanston_all.csv in data/ or fb_data/."
    )


def build_metadata_lookup() -> dict:
    json_path = resolve_json_path()
    listings = json.loads(json_path.read_text(encoding="utf-8"))
    lookup = {}

    for listing in listings:
        raw = listing.get("raw", {})
        home_info = raw.get("hdpData", {}).get("homeInfo", {})
        lat_long = raw.get("latLong", {})
        normalized = normalize_url(first_non_null(raw.get("detailUrl"), listing.get("url")))
        lookup[normalized] = {
            "image_url": first_photo_url(raw),
            "latitude": first_non_null(lat_long.get("latitude"), home_info.get("latitude")),
            "longitude": first_non_null(lat_long.get("longitude"), home_info.get("longitude")),
        }

    return lookup


def build_listing_frame() -> pd.DataFrame:
    csv_path = resolve_csv_path()
    csv_df = pd.read_csv(csv_path)
    metadata_lookup = build_metadata_lookup()
    rows = []

    for row_index, csv_row in csv_df.iterrows():
        normalized_url = normalize_url(csv_row.get("url"))
        metadata = metadata_lookup.get(normalized_url, {})
        latitude = metadata.get("latitude")
        longitude = metadata.get("longitude")
        csv_distance = csv_row.get("distance_from_northwestern_tech")
        csv_image = csv_row.get("image_url")
        parsed_distance = pd.to_numeric(csv_distance, errors="coerce")

        rows.append(
            {
                "id": f"csv-{row_index}",
                "url": normalized_url,
                "address": first_non_null(csv_row.get("address"), ""),
                "display_price": csv_row.get("price"),
                "image_url": first_non_null(csv_image, metadata.get("image_url", ""), ""),
                "beds": csv_row.get("beds"),
                "baths": normalize_baths(csv_row.get("baths")),
                "area": csv_row.get("area"),
                "price": numeric_price(csv_row.get("price")),
                "latitude": latitude,
                "longitude": longitude,
                "distance_from_northwestern_tech": first_non_null(
                    parsed_distance if pd.notna(parsed_distance) else None,
                    distance_from_northwestern_tech(latitude, longitude),
                ),
                "days_on_zillow": None,
                "rent_zestimate": None,
                "zipcode": "MISSING",
                "home_type": "MISSING",
                "is_featured": 0,
                "has_units": 0,
                "has_home_info": int(latitude is not None and longitude is not None),
            }
        )

    df = pd.DataFrame(rows)
    df["home_type"] = df["home_type"].fillna("MISSING")
    df["zipcode"] = df["zipcode"].fillna("MISSING").astype(str)

    for column in NUMERIC_FEATURES + ["price"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in BOOLEAN_FEATURES:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

    return df
