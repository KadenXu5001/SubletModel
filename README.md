# Wildcat Apartment Finder

## Contributors

Ethan Jared-Chan, Sandaru Balahewa, Kaden Xu, Andrew Elias

## Heroku link

https://nu-apartment-finder-30c223e44676.herokuapp.com/

## Youtube Demo

https://youtu.be/8iHWPLlFhQ8

## Presentation

https://docs.google.com/presentation/d/1wz8PeCTB9rBxq86wsDBNK57bPQD4dPbOWfnOv7GHWAk/edit?usp=sharing

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
pip install -r requirements.txt
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
npm install
npm run build
cd ..
gunicorn app:app
```

Open `http://127.0.0.1:8000/` — you should see the scatterplot UI (not JSON).

## Heroku deployment

Production serves the built React app from Flask on `/`. API routes stay under `/api/*`; use `GET /api/health` for a health check.

The root [`package.json`](package.json) runs `heroku-postbuild` to build `frontend/dist` during deploy. Configure the Heroku app with **Node first, then Python**:

```bash
heroku buildpacks:clear -a <app-name>
heroku buildpacks:add -i 1 heroku/nodejs -a <app-name>
heroku buildpacks:add -i 2 heroku/python -a <app-name>
heroku config:set NPM_CONFIG_PRODUCTION=false -a <app-name>
```

`NPM_CONFIG_PRODUCTION=false` ensures Vite (a devDependency) is installed for the frontend build.

Deploy:

```bash
git push heroku main
```
