import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# ── Load ──────────────────────────────────────────
df = pd.read_csv("data/mock_fb_dataset.csv")

# ── Feature Engineering ───────────────────────────
df["is_furnished"]   = (df["Furnished_Status"] == "Furnished").astype(int)
df["is_entire_unit"] = (df["Listing_Type"] == "Entire Unit").astype(int)
df["location_code"]  = df["Location_Area"].astype("category").cat.codes

FEATURES = ["Bedrooms_In_Unit", "Bathrooms", "Total_Roommates",
            "is_furnished", "is_entire_unit", "location_code"]

X = df[FEATURES]
y = df["Price_USD"]

# ── Train ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────
preds = model.predict(X_test)
print(f"MAE: ${mean_absolute_error(y_test, preds):,.0f}")
print(f"R²:  {r2_score(y_test, preds):.3f}")

# ── Predict a new listing ─────────────────────────
new = pd.DataFrame([{
    "Bedrooms_In_Unit": 2,
    "Bathrooms": 1.0,
    "Total_Roommates": 1,
    "is_furnished": 1,
    "is_entire_unit": 0,
    "location_code": 0,
}])

price = model.predict(new)[0]
print(f"Predicted price: ${price:,.0f}/mo")