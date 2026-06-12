# Sublet Model

## Contributors
Ethan Chan, Sandaru Balehawa, Kaden Xu

## Repository
https://github.com/KadenXu5001/SubletModel

## Description

A machine learning tool that predicts monthly rent prices for Evanston, IL housing listings. Trained on data scraped from Zillow and Facebook, it uses XGBoost to estimate price from listing features like bedrooms, bathrooms, location, and furnished status.

`main.py` loads the dataset, engineers features, trains an XGBoost regression model, and prints MAE and R² to the terminal.

`app.py` does the same at startup, then serves a web interface at `localhost:5000` where you can enter listing details and get a predicted monthly price.

### Setup

```bash
pip install flask xgboost scikit-learn pandas
```

Place your dataset at `data/mock_dataset.csv` before running.

### Train the model and run the web app

```bash
python app.py
```
Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Train the model only

```bash
python main.py
```