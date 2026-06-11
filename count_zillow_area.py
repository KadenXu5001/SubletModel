import json
import sys
from pathlib import Path


DEFAULT_PATH = Path("fb_data/zillow_evanston_all.json")


def main() -> None:
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

    with json_path.open("r", encoding="utf-8") as f:
        listings = json.load(f)

    if not isinstance(listings, list):
        raise ValueError(f"Expected a JSON array in {json_path}")

    count = sum(1 for listing in listings if listing.get("area") is not None)

    print(f"Listings with non-null area: {count}")
    print(f"Total listings: {len(listings)}")


if __name__ == "__main__":
    main()
