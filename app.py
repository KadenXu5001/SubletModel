import pickle
from pathlib import Path
from difflib import SequenceMatcher

from flask import Flask, jsonify, render_template, request
import pandas as pd

from zillow_data import (
    NORTHWESTERN_TECH_NAME,
    distance_from_northwestern_tech,
    build_listing_frame,
)


MODEL_PATH = Path("models/zillow_evanston_model.pkl")
HIDDEN_FIELDS = {"zipcode", "home_type", "rent_zestimate"}
FIELD_ORDER = [
    "beds",
    "baths",
    "area",
    "address_query",
]
FIELD_LABELS = {
    "beds": "Bedrooms",
    "baths": "Bathrooms",
    "area": "Square Footage",
    "address_query": "Address",
}
FIELD_HELP = {
    "beds": "Studio = 0.",
    "baths": "Use 0.5 steps if needed.",
    "area": "Square feet.",
    "address_query": "Used to infer distance from Northwestern Tech.",
}


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
NUMERIC_FEATURES = artifact.get("numeric_features", ["beds", "baths", "area"])
CATEGORICAL_FEATURES = artifact.get("categorical_features", [])
BOOLEAN_FEATURES = artifact.get("boolean_features", [])
FEATURE_DEFAULTS = artifact["feature_defaults"]
MODEL_MAE = artifact["metrics"]["mae"]
MODEL_R2 = artifact["metrics"]["r2"]
LISTINGS_DF = build_listing_frame()
ADDRESS_BOOK = (
    LISTINGS_DF[["address", "latitude", "longitude"]]
    .dropna(subset=["address", "latitude", "longitude"])
    .drop_duplicates(subset=["address"])
    .reset_index(drop=True)
)


def build_field_specs() -> list[dict]:
    visible_fields = [field for field in FIELD_ORDER if field in FEATURES and field not in HIDDEN_FIELDS]
    field_specs = []

    for field in visible_fields:
        if field in NUMERIC_FEATURES:
            spec = {
                "name": field,
                "label": FIELD_LABELS.get(field, field.replace("_", " ").title()),
                "type": "number",
                "step": "any",
                "default": FEATURE_DEFAULTS.get(field, ""),
                "help": FIELD_HELP.get(field, ""),
            }
            if field in {"beds", "days_on_zillow", "area"}:
                spec["step"] = "1"
            if field in {"beds", "baths", "area", "days_on_zillow"}:
                spec["min"] = "0"
            field_specs.append(spec)
        elif field in BOOLEAN_FEATURES:
            field_specs.append(
                {
                    "name": field,
                    "label": FIELD_LABELS.get(field, field.replace("_", " ").title()),
                    "type": "checkbox",
                    "default": int(FEATURE_DEFAULTS.get(field, 0)),
                    "help": FIELD_HELP.get(field, ""),
                }
            )

    if "address_query" in FIELD_ORDER:
        insert_at = 3 if len(field_specs) >= 3 else len(field_specs)
        field_specs.insert(
            insert_at,
            {
                "name": "address_query",
                "label": FIELD_LABELS["address_query"],
                "type": "text",
                "default": "",
                "help": FIELD_HELP["address_query"],
            },
        )

    return field_specs


FIELD_SPECS = build_field_specs()
VISIBLE_FIELDS = [spec["name"] for spec in FIELD_SPECS]
MODEL_COMPARISON_FIELDS = list(FEATURES)


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

    for feature in NUMERIC_FEATURES:
        value = data.get(feature)
        if value not in (None, ""):
            row[feature] = float(value)

    for feature in CATEGORICAL_FEATURES:
        value = data.get(feature)
        if value not in (None, ""):
            row[feature] = str(value)

    for feature in BOOLEAN_FEATURES:
        value = data.get(feature)
        if value is not None:
            row[feature] = int(bool(value))

    resolved_coordinates = resolve_address_to_coordinates(data.get("address_query", ""))
    if resolved_coordinates is not None:
        row["latitude"], row["longitude"] = resolved_coordinates
        row["distance_from_northwestern_tech"] = distance_from_northwestern_tech(
            row["latitude"], row["longitude"]
        )

    return row


def find_comparables(row: dict, predicted_price: float, limit: int = 4, offset: int = 0) -> tuple[list[dict], int]:
    df = LISTINGS_DF.copy()
    preferred_df = df[df["area"].notna() & df["image_url"].astype(str).ne("")].copy()
    if len(preferred_df) >= limit:
        df = preferred_df
    scored_columns = []

    for feature in MODEL_COMPARISON_FIELDS:
        if feature not in df.columns:
            continue
        if feature in NUMERIC_FEATURES:
            series = pd.to_numeric(df[feature], errors="coerce")
            target = float(row[feature])
            spread = float(series.std(skipna=True))
            if not spread or pd.isna(spread):
                spread = 1.0
            df[f"score_{feature}"] = (series.fillna(target) - target).abs() / spread
        else:
            target = int(row[feature])
            df[f"score_{feature}"] = (df[feature].fillna(target).astype(int) != target).astype(float)
        scored_columns.append(f"score_{feature}")

    price_spread = float(df["price"].std(skipna=True))
    if not price_spread or pd.isna(price_spread):
        price_spread = 1.0
    df["score_price"] = (df["price"].fillna(predicted_price) - predicted_price).abs() / price_spread

    # The four prediction features are the main similarity signal.
    df["feature_similarity_score"] = df[scored_columns].mean(axis=1)
    # Price stays in the ranking, but only as a lighter tie-breaker.
    df["similarity_score"] = (df["feature_similarity_score"] * 0.85) + (df["score_price"] * 0.15)
    ranked = df.sort_values(["similarity_score", "feature_similarity_score", "price"]).reset_index(drop=True)
    total_count = len(ranked)
    comps = ranked.iloc[offset:offset + limit]

    return (
        [
            {
                "url": comp["url"],
                "address": comp["address"],
                "image_url": comp["image_url"],
                "price": int(comp["price"]) if pd.notna(comp["price"]) else None,
                "beds": float(comp["beds"]) if pd.notna(comp["beds"]) else None,
                "baths": float(comp["baths"]) if pd.notna(comp["baths"]) else None,
                "area": int(comp["area"]) if pd.notna(comp["area"]) else None,
                "distance_from_northwestern_tech_mi": distance_to_northwestern_tech(comp),
            }
            for _, comp in comps.iterrows()
        ],
        total_count,
    )


def distance_to_northwestern_tech(comp) -> float | None:
    latitude = comp.get("latitude")
    longitude = comp.get("longitude")
    if pd.isna(latitude) or pd.isna(longitude):
        return None

    distance = distance_from_northwestern_tech(float(latitude), float(longitude))
    return None if distance is None else round(float(distance), 1)


print(f"Model loaded — MAE: ${MODEL_MAE:,.0f}  R²: {MODEL_R2:.3f}")

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        mae=f"{MODEL_MAE:,.0f}",
        r2=f"{MODEL_R2:.3f}",
        field_specs=FIELD_SPECS,
    )


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json() or {}
    try:
        limit = int(data.get("limit", 4))
        offset = int(data.get("offset", 0))
        row = build_model_row(data)
        new = pd.DataFrame([row])[FEATURES]
        price = float(model.predict(new)[0])
        comparables, total_count = find_comparables(row, price, limit=limit, offset=offset)
        next_offset = offset + len(comparables)
        return jsonify(
            {
                "price": round(price, 2),
                "comparables": comparables,
                "has_more": next_offset < total_count,
                "next_offset": next_offset,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
