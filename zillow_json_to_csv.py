import csv
import json
import re
import sys
from math import asin, cos, radians, sin, sqrt
from pathlib import Path


BASE_URL = "https://www.zillow.com"
NORTHWESTERN_TECH_LATITUDE = 42.0579
NORTHWESTERN_TECH_LONGITUDE = -87.6752


def resolve_default_input() -> Path:
    candidates = [
        Path("data/zillow_evanston_all.json"),
        Path("fb_data/zillow_evanston_all.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find zillow_evanston_all.json in data/ or fb_data/.")


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{BASE_URL}{url}"
    return f"{BASE_URL}/{url}"


def first_non_null(*values):
    for value in values:
        if value is not None:
            return value
    return None


def normalize_baths(value):
    return 1 if value in (None, "") else value


def numeric_price(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    match = re.search(r"[\d,]+", str(value))
    if not match:
        return None

    return int(match.group(0).replace(",", ""))


def format_price(raw_listing: dict) -> int | str:
    price = raw_listing.get("price")
    numeric = numeric_price(price)
    if numeric is not None:
        return numeric

    unformatted = raw_listing.get("unformattedPrice")
    if unformatted is not None:
        return int(unformatted)

    home_info = raw_listing.get("hdpData", {}).get("homeInfo", {})
    home_price = home_info.get("priceForHDP", home_info.get("price"))
    if home_price is None:
        return ""

    return int(home_price)


def format_address(raw_listing: dict) -> str:
    address = raw_listing.get("address")
    if address:
        return str(address)

    home_info = raw_listing.get("hdpData", {}).get("homeInfo", {})
    street = home_info.get("streetAddress")
    city = home_info.get("city")
    state = home_info.get("state")
    zipcode = home_info.get("zipcode")

    city_state_zip = " ".join(part for part in [f"{city}," if city else None, state, zipcode] if part)
    return ", ".join(part for part in [street, city_state_zip] if part)


def first_photo_url(raw_listing: dict) -> str:
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


def distance_from_northwestern_tech(latitude, longitude) -> float | str:
    if latitude is None or longitude is None:
        return ""

    return round(
        haversine_miles(
            float(latitude),
            float(longitude),
            NORTHWESTERN_TECH_LATITUDE,
            NORTHWESTERN_TECH_LONGITUDE,
        ),
        3,
    )


def listing_row(listing: dict) -> dict:
    raw_listing = listing.get("raw", {})
    home_info = raw_listing.get("hdpData", {}).get("homeInfo", {})
    lat_long = raw_listing.get("latLong", {})
    latitude = first_non_null(lat_long.get("latitude"), home_info.get("latitude"))
    longitude = first_non_null(lat_long.get("longitude"), home_info.get("longitude"))

    return {
        "url": normalize_url(first_non_null(raw_listing.get("detailUrl"), listing.get("url"))),
        "beds": first_non_null(raw_listing.get("beds"), home_info.get("bedrooms"), listing.get("beds"), ""),
        "baths": normalize_baths(
            first_non_null(raw_listing.get("baths"), home_info.get("bathrooms"), listing.get("baths"), "")
        ),
        "address": first_non_null(format_address(raw_listing), listing.get("address"), ""),
        "price": first_non_null(format_price(raw_listing), listing.get("price"), ""),
        "area": first_non_null(raw_listing.get("area"), home_info.get("livingArea"), listing.get("area"), ""),
        "image_url": first_photo_url(raw_listing),
        "distance_from_northwestern_tech": distance_from_northwestern_tech(latitude, longitude),
    }


def unit_rows(listing: dict) -> list[dict]:
    base_row = listing_row(listing)
    raw_listing = listing.get("raw", {})
    units = raw_listing.get("units")

    if not isinstance(units, list) or not units:
        return [base_row]

    rows = []
    for unit in units:
        rows.append(
            {
                "url": base_row["url"],
                "beds": first_non_null(unit.get("beds"), base_row["beds"]),
                "baths": base_row["baths"],
                "address": base_row["address"],
                "price": first_non_null(numeric_price(unit.get("price")), base_row["price"]),
                "area": base_row["area"],
                "image_url": base_row["image_url"],
                "distance_from_northwestern_tech": base_row["distance_from_northwestern_tech"],
            }
        )

    return rows


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else resolve_default_input()
    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else input_path.with_suffix(".csv")
    )

    with input_path.open("r", encoding="utf-8") as f:
        listings = json.load(f)

    if not isinstance(listings, list):
        raise ValueError(f"Expected a JSON array in {input_path}")

    rows = []
    for listing in listings:
        rows.extend(unit_rows(listing))

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "url",
                "beds",
                "baths",
                "address",
                "price",
                "area",
                "image_url",
                "distance_from_northwestern_tech",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
