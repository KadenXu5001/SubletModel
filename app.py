import pickle
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

from zillow_data import distance_from_northwestern_tech, build_listing_frame


MODEL_PATH = Path("models/zillow_evanston_model.pkl")


def load_artifact() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. Run `python main.py` first."
        )

    with MODEL_PATH.open("rb") as f:
        return pickle.load(f)


artifact = load_artifact()
model = artifact["model"]
FEATURES = artifact["features"]
NUMERIC_FEATURES = artifact["numeric_features"]
FEATURE_DEFAULTS = artifact["feature_defaults"]
MODEL_MAE = artifact["metrics"]["mae"]
MODEL_R2 = artifact["metrics"]["r2"]

LISTINGS_DF = build_listing_frame()
GRAPH_LISTINGS_DF = LISTINGS_DF[
    LISTINGS_DF["price"].notna()
    & LISTINGS_DF["area"].notna()
    & LISTINGS_DF["distance_from_northwestern_tech"].notna()
].copy()
ADDRESS_BOOK = (
    LISTINGS_DF[["address", "latitude", "longitude"]]
    .dropna(subset=["address", "latitude", "longitude"])
    .drop_duplicates(subset=["address"])
    .reset_index(drop=True)
)

app = Flask(__name__)


def resolve_address_to_coordinates(address_query: str) -> tuple[float, float] | None:
    query = " ".join(str(address_query).lower().split())
    if not query or ADDRESS_BOOK.empty:
        return None

    best_row = None
    best_score = 0.0

    for _, candidate in ADDRESS_BOOK.iterrows():
        candidate_address = " ".join(str(candidate["address"]).lower().split())
        if not candidate_address:
            continue

        score = SequenceMatcher(None, query, candidate_address).ratio()
        if query in candidate_address:
            score += 0.25

        if score > best_score:
            best_score = score
            best_row = candidate

    if best_row is None or best_score < 0.45:
        return None

    return float(best_row["latitude"]), float(best_row["longitude"])


def build_model_row(data: dict) -> dict:
    row = FEATURE_DEFAULTS.copy()

    for feature in ("beds", "baths", "area"):
        value = data.get(feature)
        if value not in (None, ""):
            row[feature] = float(value)

    resolved_coordinates = resolve_address_to_coordinates(data.get("address_query", ""))
    if resolved_coordinates is not None:
        row["distance_from_northwestern_tech"] = distance_from_northwestern_tech(*resolved_coordinates)

    return row


def serialize_listing_node(comp) -> dict:
    return {
        "id": str(comp["id"]),
        "address": comp["address"],
        "url": comp["url"],
        "image_url": comp["image_url"],
        "price": int(comp["price"]) if pd.notna(comp["price"]) else None,
        "beds": float(comp["beds"]) if pd.notna(comp["beds"]) else None,
        "baths": float(comp["baths"]) if pd.notna(comp["baths"]) else None,
        "area": int(comp["area"]) if pd.notna(comp["area"]) else None,
        "distance_from_northwestern_tech": float(comp["distance_from_northwestern_tech"])
        if pd.notna(comp["distance_from_northwestern_tech"])
        else None,
    }


def build_meta(df: pd.DataFrame) -> dict:
    return {
        "x_domain": [float(df["area"].min()), float(df["area"].max())],
        "y_domain": [float(df["price"].min()), float(df["price"].max())],
        "distance_range": [
            float(df["distance_from_northwestern_tech"].min()),
            float(df["distance_from_northwestern_tech"].max()),
        ],
    }


@app.route("/")
def index():
    return jsonify(
        {
            "name": "wildcat room finder api",
            "status": "ok",
            "endpoint": "/api/market-map",
            "model_mae": round(float(MODEL_MAE), 2),
            "model_r2": round(float(MODEL_R2), 3),
        }
    )


@app.route("/api/market-map", methods=["POST"])
def market_map():
    data = request.get_json() or {}
    try:
        row = build_model_row(data)
        predicted_price = float(model.predict(pd.DataFrame([row])[FEATURES])[0])
        target = {
            "id": "target",
            "beds": float(row["beds"]),
            "baths": float(row["baths"]),
            "area": float(row["area"]),
            "distance_from_northwestern_tech": float(row["distance_from_northwestern_tech"]),
            "price": round(predicted_price, 2),
        }
        listings = [serialize_listing_node(comp) for _, comp in GRAPH_LISTINGS_DF.iterrows()]
        return jsonify(
            {
                "target": target,
                "listings": listings,
                "meta": build_meta(GRAPH_LISTINGS_DF),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
