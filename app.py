from flask import Flask, request, jsonify, render_template
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

app = Flask(__name__)

# ── Train model at startup ─────────────────────────
df = pd.read_csv("fb_data/zillow_evanston_all.csv")

FEATURES = ["beds", "baths"]
X = df[FEATURES]
y = df["price"]

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
                           mae=f"{MODEL_MAE:,.0f}",
                           r2=f"{MODEL_R2:.3f}")


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    try:
        new = pd.DataFrame([{
            "beds":  int(data["beds"]),
            "baths": float(data["baths"]),
        }])
        price = float(model.predict(new)[0])
        return jsonify({"price": round(price, 2)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)