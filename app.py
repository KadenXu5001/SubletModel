from flask import Flask, request, jsonify, render_template
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

app = Flask(__name__)

# ── Train model at startup ─────────────────────────
df = pd.read_csv("data/mock_fb_dataset.csv")

df["is_furnished"]   = (df["Furnished_Status"] == "Furnished").astype(int)
df["is_entire_unit"] = (df["Listing_Type"] == "Entire Unit").astype(int)
location_cat         = df["Location_Area"].astype("category")
df["location_code"]  = location_cat.cat.codes
LOCATION_MAP         = dict(enumerate(location_cat.cat.categories))  # code → name
LOCATION_NAMES       = list(location_cat.cat.categories)             # for the UI

FEATURES = ["Bedrooms_In_Unit", "Bathrooms", "Total_Roommates",
            "is_furnished", "is_entire_unit", "location_code"]

X = df[FEATURES]
y = df["Price_USD"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)

preds     = model.predict(X_test)
MODEL_MAE = mean_absolute_error(y_test, preds)
MODEL_R2  = r2_score(y_test, preds)

print(f"Model ready — MAE: ${MODEL_MAE:,.0f}  R²: {MODEL_R2:.3f}")


# ── Routes ─────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           locations=LOCATION_NAMES,
                           mae=f"{MODEL_MAE:,.0f}",
                           r2=f"{MODEL_R2:.3f}")


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    try:
        location_name = data["location"]
        location_code = LOCATION_NAMES.index(location_name) if location_name in LOCATION_NAMES else 0

        new = pd.DataFrame([{
            "Bedrooms_In_Unit":  int(data["bedrooms"]),
            "Bathrooms":         float(data["bathrooms"]),
            "Total_Roommates":   int(data["roommates"]),
            "is_furnished":      1 if data["furnished"] == "true" else 0,
            "is_entire_unit":    1 if data["listing_type"] == "Entire Unit" else 0,
            "location_code":     location_code,
        }])

        price = float(model.predict(new)[0])
        return jsonify({"price": round(price, 2)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)