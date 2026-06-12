import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
 
# ── Load ──────────────────────────────────────────
df = pd.read_csv("fb_data/zillow_evanston_all.csv")
 
FEATURES = ["beds", "baths"]
X = df[FEATURES]
y = df["price"]
 
# ── Train ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
 
model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)
 
# ── Evaluate ──────────────────────────────────────
preds = model.predict(X_test)
print(f"MAE: ${mean_absolute_error(y_test, preds):,.0f}")
print(f"R²:  {r2_score(y_test, preds):.3f}")
 
# ── Predict a new listing ─────────────────────────
new = pd.DataFrame([{"beds": 2, "baths": 1.0}])
price = model.predict(new)[0]
print(f"Predicted price: ${price:,.0f}/mo")
