import csv
import json
import sys
from pathlib import Path


BASE_URL = "https://www.zillow.com"
DEFAULT_INPUT = Path("fb_data/zillow_evanston_all.json")


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


def format_price(raw_listing: dict) -> str:
    price = raw_listing.get("price")
    if price is not None:
        return str(price)

    unformatted = raw_listing.get("unformattedPrice")
    if unformatted is not None:
        currency = raw_listing.get("countryCurrency", "$")
        return f"{currency}{unformatted}"

    home_info = raw_listing.get("hdpData", {}).get("homeInfo", {})
    home_price = home_info.get("priceForHDP", home_info.get("price"))
    if home_price is None:
        return ""

    currency = raw_listing.get("countryCurrency", "$")
    return f"{currency}{home_price}"


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


def listing_row(listing: dict) -> dict:
    raw_listing = listing.get("raw", {})
    home_info = raw_listing.get("hdpData", {}).get("homeInfo", {})

    return {
        "url": normalize_url(first_non_null(raw_listing.get("detailUrl"), listing.get("url"))),
        "beds": first_non_null(raw_listing.get("beds"), home_info.get("bedrooms"), listing.get("beds"), ""),
        "baths": normalize_baths(
            first_non_null(raw_listing.get("baths"), home_info.get("bathrooms"), listing.get("baths"), "")
        ),
        "address": first_non_null(format_address(raw_listing), listing.get("address"), ""),
        "price": first_non_null(format_price(raw_listing), listing.get("price"), ""),
        "area": first_non_null(raw_listing.get("area"), home_info.get("livingArea"), listing.get("area"), ""),
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
                "price": first_non_null(unit.get("price"), base_row["price"]),
                "area": base_row["area"],
            }
        )

    return rows


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
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
        writer = csv.DictWriter(f, fieldnames=["url", "beds", "baths", "address", "price", "area"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
