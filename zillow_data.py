import json
import re
from pathlib import Path

import pandas as pd


BASE_URL = "https://www.zillow.com"
NUMERIC_FEATURES = [
    "beds",
    "baths",
    "area",
    "latitude",
    "longitude",
    "days_on_zillow",
    "rent_zestimate",
]
CATEGORICAL_FEATURES = [
    "zipcode",
    "home_type",
]
BOOLEAN_FEATURES = [
    "is_featured",
    "has_units",
    "has_home_info",
]
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

    for listing in listings:
        raw = listing.get("raw", {})
        home_info = raw.get("hdpData", {}).get("homeInfo", {})
        lat_long = raw.get("latLong", {})

        base_row = {
            "url": normalize_url(first_non_null(raw.get("detailUrl"), listing.get("url"))),
            "address": first_non_null(raw.get("address"), listing.get("address"), ""),
            "display_price": first_non_null(raw.get("price"), listing.get("price"), ""),
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
            "latitude": first_non_null(lat_long.get("latitude"), home_info.get("latitude")),
            "longitude": first_non_null(lat_long.get("longitude"), home_info.get("longitude")),
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
            for unit in units:
                row = base_row.copy()
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
