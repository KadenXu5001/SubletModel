# wildcat room finder

## Overview

`wildcat room finder` is a Northwestern-focused housing market map for Evanston listings. A Flask backend serves a trained rent model and graph-ready Zillow data, while a Vite + React frontend renders an interactive scatterplot where:

- `x` = square footage
- `y` = monthly rent
- point color = distance from Northwestern Tech
- the highlighted target node = the user query

Clicking a listing node opens a detail card with the Zillow photo, beds/baths, square footage, distance from Tech, and the Zillow link.

## Backend setup

Install the Python dependencies:

```bash
pip install flask pandas scikit-learn xgboost
```

Retrain the four-feature model:

```bash
python main.py
```

Run the Flask API on `http://127.0.0.1:5000`:

```bash
python app.py
```

The main API endpoint is:

```text
POST /api/market-map
```

## Frontend setup

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

The React app runs on `http://127.0.0.1:5173`.

Vite proxies `/api/*` requests to the Flask backend on port `5000`, so both processes should be running during development.

## Production-style frontend check

To verify the React build locally:

```bash
cd frontend
npm run build
```
