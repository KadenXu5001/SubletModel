import pickle
from pathlib import Path

from flask import Flask, jsonify, render_template, request
import pandas as pd

from zillow_data import build_listing_frame


MODEL_PATH = Path("models/zillow_evanston_model.pkl")
HIDDEN_FIELDS = {"zipcode", "home_type", "rent_zestimate"}
FIELD_ORDER = [
    "beds",
    "baths",
    "area",
    "latitude",
    "longitude",
    "days_on_zillow",
    "is_featured",
    "has_units",
    "has_home_info",
]
FIELD_LABELS = {
    "beds": "Bedrooms",
    "baths": "Bathrooms",
    "area": "Square Footage",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "days_on_zillow": "Days on Zillow",
    "rent_zestimate": "Rent Zestimate",
    "zipcode": "Zip Code",
    "home_type": "Home Type",
    "is_featured": "Featured Listing",
    "has_units": "Has Multiple Units",
    "has_home_info": "Has Zillow Home Details",
}
FIELD_HELP = {
    "beds": "Studio = 0, one-bed = 1, and so on.",
    "baths": "Half baths can be entered as 0.5 increments.",
    "area": "Use interior square footage when available.",
    "latitude": "Optional, but helps surface tighter comparables.",
    "longitude": "Optional, pairs with latitude for location matching.",
    "days_on_zillow": "Useful if you want recency-sensitive comps.",
    "is_featured": "Whether the listing is promoted on Zillow.",
    "has_units": "Turn on for buildings with multiple unit types.",
    "has_home_info": "Keep on unless the listing is very sparse.",
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

    return field_specs


FIELD_SPECS = build_field_specs()
VISIBLE_FIELDS = [spec["name"] for spec in FIELD_SPECS]
COMPARABLE_FIELDS = [
    field for field in VISIBLE_FIELDS if field in NUMERIC_FEATURES or field in BOOLEAN_FEATURES
]


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

    return row


def find_comparables(row: dict, predicted_price: float, limit: int = 4) -> list[dict]:
    df = LISTINGS_DF.copy()
    scored_columns = []

    for feature in COMPARABLE_FIELDS:
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
    scored_columns.append("score_price")

    df["similarity_score"] = df[scored_columns].mean(axis=1)
    comps = df.sort_values(["similarity_score", "price"]).head(limit)

    return [
        {
            "url": comp["url"],
            "address": comp["address"],
            "price": int(comp["price"]) if pd.notna(comp["price"]) else None,
            "beds": float(comp["beds"]) if pd.notna(comp["beds"]) else None,
            "baths": float(comp["baths"]) if pd.notna(comp["baths"]) else None,
            "area": int(comp["area"]) if pd.notna(comp["area"]) else None,
        }
        for _, comp in comps.iterrows()
    ]


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
        row = build_model_row(data)
        new = pd.DataFrame([row])[FEATURES]
        price = float(model.predict(new)[0])
        comparables = find_comparables(row, price)
        return jsonify(
            {
                "price": round(price, 2),
                "comparables": comparables,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
