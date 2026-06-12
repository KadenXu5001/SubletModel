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


def build_listing_frame() -> pd.DataFrame:
    json_path = resolve_json_path()
    listings = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []

    for listing_index, listing in enumerate(listings):
        raw = listing.get("raw", {})
        home_info = raw.get("hdpData", {}).get("homeInfo", {})
        lat_long = raw.get("latLong", {})
        latitude = first_non_null(lat_long.get("latitude"), home_info.get("latitude"))
        longitude = first_non_null(lat_long.get("longitude"), home_info.get("longitude"))
        listing_key = first_non_null(raw.get("zpid"), raw.get("id"), listing.get("zpid"), listing_index)

        base_row = {
            "id": f"{listing_key}-0",
            "url": normalize_url(first_non_null(raw.get("detailUrl"), listing.get("url"))),
            "address": first_non_null(raw.get("address"), listing.get("address"), ""),
            "display_price": first_non_null(raw.get("price"), listing.get("price"), ""),
            "image_url": first_photo_url(raw),
            "beds": first_non_null(raw.get("beds"), home_info.get("bedrooms"), listing.get("beds")),
            "baths": normalize_baths(
                first_non_null(raw.get("baths"), home_info.get("bathrooms"), listing.get("baths"), 1)
            ),
            "area": first_non_null(raw.get("area"), home_info.get("livingArea"), listing.get("area")),
            "price": first_non_null(
                numeric_price(raw.get("price")),
                raw.get("unformattedPrice"),
                home_info.get("priceForHDP"),
                home_info.get("price"),
                numeric_price(listing.get("price")),
            ),
            "latitude": latitude,
            "longitude": longitude,
            "distance_from_northwestern_tech": distance_from_northwestern_tech(latitude, longitude),
            "days_on_zillow": home_info.get("daysOnZillow"),
            "rent_zestimate": home_info.get("rentZestimate"),
            "zipcode": first_non_null(raw.get("addressZipcode"), home_info.get("zipcode")),
            "home_type": home_info.get("homeType"),
            "is_featured": int(bool(first_non_null(raw.get("isFeaturedListing"), home_info.get("isFeatured"), False))),
            "has_units": int(bool(raw.get("units"))),
            "has_home_info": int(bool(home_info)),
        }

        units = raw.get("units")
        if isinstance(units, list) and units:
            for unit_index, unit in enumerate(units, start=1):
                row = base_row.copy()
                row["id"] = f"{listing_key}-{unit_index}"
                row["beds"] = first_non_null(unit.get("beds"), row["beds"])
                row["price"] = first_non_null(numeric_price(unit.get("price")), row["price"])
                row["display_price"] = first_non_null(unit.get("price"), row["display_price"])
                rows.append(row)
        else:
            rows.append(base_row)

    df = pd.DataFrame(rows)
    df["home_type"] = df["home_type"].fillna("MISSING")
    df["zipcode"] = df["zipcode"].fillna("MISSING").astype(str)

    for column in NUMERIC_FEATURES + ["price"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in BOOLEAN_FEATURES:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(int)

    return df
