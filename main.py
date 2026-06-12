import pickle
from pathlib import Path

from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from zillow_data import ALL_FEATURES, NUMERIC_FEATURES, build_listing_frame


MODEL_PATH = Path("models/zillow_evanston_model.pkl")
BASELINE_FEATURES = ["beds", "baths", "area"]


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                XGBRegressor(
                    n_estimators=250,
                    learning_rate=0.06,
                    max_depth=4,
                    min_child_weight=2,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    random_state=42,
                    objective="reg:squarederror",
                ),
            ),
        ]
    )


def evaluate_pipeline(pipeline: Pipeline, X_train, X_test, y_train, y_test) -> dict:
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    return {
        "mae": float(mean_absolute_error(y_test, preds)),
        "r2": float(r2_score(y_test, preds)),
    }


def feature_defaults(df) -> dict:
    return {
        feature: float(df[feature].median())
        for feature in NUMERIC_FEATURES
    }


def main() -> None:
    df = build_listing_frame()
    df = df[df["price"].notna()].copy()

    X = df[ALL_FEATURES].copy()
    y = df["price"].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    baseline_pipeline = build_pipeline()
    baseline_metrics = evaluate_pipeline(
        baseline_pipeline,
        X_train[BASELINE_FEATURES],
        X_test[BASELINE_FEATURES],
        y_train,
        y_test,
    )

    improved_pipeline = build_pipeline()
    improved_metrics = evaluate_pipeline(
        improved_pipeline,
        X_train,
        X_test,
        y_train,
        y_test,
    )

    improved_pipeline.fit(X, y)

    artifact = {
        "model": improved_pipeline,
        "features": ALL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": [],
        "boolean_features": [],
        "feature_defaults": feature_defaults(X),
        "metrics": improved_metrics,
        "baseline_metrics": baseline_metrics,
        "training_rows": int(len(df)),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as f:
        pickle.dump(artifact, f)

    print(f"Saved model to {MODEL_PATH}")
    print(f"Training rows: {len(df)}")
    print(
        "Baseline  — "
        f"MAE: ${baseline_metrics['mae']:,.0f}  "
        f"R²: {baseline_metrics['r2']:.3f}"
    )
    print(
        "Retrained — "
        f"MAE: ${improved_metrics['mae']:,.0f}  "
        f"R²: {improved_metrics['r2']:.3f}"
    )


if __name__ == "__main__":
    main()
