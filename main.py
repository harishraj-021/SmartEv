from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "EV Energy Efficiency Dataset.csv"
TARGET = "Energy Efficiency (km/kWh)"
FEATURES = [
    "Model year",
    "Make",
    "Model",
    "Vehicle class",
    "Motor (kW)",
    "Recharge time (h)",
]
CAT = ["Make", "Model", "Vehicle class"]
NUM = ["Model year", "Motor (kW)", "Recharge time (h)"]
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.heigit.org/openrouteservice").rstrip("/")
ORS_API_KEY = os.getenv("OPENROUTE_API_KEY", "").strip()


def load_dataset() -> pd.DataFrame:
    if not DATASET.exists():
        raise RuntimeError(f"Dataset not found: {DATASET}")
    df = pd.read_csv(DATASET)
    required = FEATURES + [TARGET]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError("Dataset is missing: " + ", ".join(missing))
    for col in CAT:
        df[col] = df[col].astype(str).str.strip()
    for col in NUM + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required).reset_index(drop=True)
    return df


def make_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
            ("num", "passthrough", NUM),
        ],
        remainder="drop",
    )
    rf = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", pre), ("model", rf)])


@lru_cache(maxsize=1)
def artifacts():
    df = load_dataset()
    X = df[FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    evaluation_model = make_pipeline()
    evaluation_model.fit(X_train, y_train)
    pred = evaluation_model.predict(X_test)
    metrics = {
        "r2": float(r2_score(y_test, pred)),
        "mae": float(mean_absolute_error(y_test, pred)),
        "rmse": float(mean_squared_error(y_test, pred) ** 0.5),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }
    final_model = make_pipeline()
    final_model.fit(X, y)
    return df, final_model, metrics


app = FastAPI(title="SmartEV API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TripRequest(BaseModel):
    make: str
    model: str
    model_year: int
    motor_kw: float = Field(gt=0)
    recharge_time_h: float = Field(ge=0)
    vehicle_class: str
    battery_kwh: float = Field(gt=0, le=300)
    charge_percent: float = Field(ge=0, le=100)
    reserve_percent: float = Field(ge=5, le=30, default=10)
    start: str
    destination: str
    driving_style: Literal["Gentle", "Normal", "Aggressive"] = "Normal"


class ManualTripRequest(TripRequest):
    distance_km: float = Field(gt=0)
    ascent_m: float = Field(ge=0)
    descent_m: float = Field(ge=0)
    temperature_c: float = 25
    wind_kmh: float = Field(ge=0)
    rain_mm: float = Field(ge=0, default=0)
    city_fraction: float = Field(ge=0, le=1, default=0.3)


def geocode(place: str):
    place = place.strip()
    if not place:
        return None
    try:
        r = requests.get(
            "https://api.heigit.org/pelias/v1/search",
            params={"text": place, "size": 1},
            timeout=10,
        )
        if r.ok:
            features = r.json().get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                props = features[0].get("properties", {})
                return float(coords[1]), float(coords[0]), props.get("label", place)
    except requests.RequestException:
        pass
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        r.raise_for_status()
        item = (r.json().get("results") or [None])[0]
        if item:
            label = ", ".join(
                x for x in [item.get("name"), item.get("admin1"), item.get("country")] if x
            )
            return float(item["latitude"]), float(item["longitude"]), label
    except requests.RequestException:
        pass
    return None


def weather(lat: float, lon: float):
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
            "wind_speed_unit": "kmh",
            "temperature_unit": "celsius",
        },
        timeout=12,
    )
    r.raise_for_status()
    cur = r.json()["current"]
    return {
        "temperature_c": float(cur["temperature_2m"]),
        "apparent_temperature_c": float(cur["apparent_temperature"]),
        "wind_kmh": float(cur["wind_speed_10m"]),
        "wind_direction": float(cur.get("wind_direction_10m", 0)),
        "rain_mm": float(cur.get("precipitation", 0)),
        "weather_code": int(cur.get("weather_code", 0)),
    }


def route(start, end):
    if not ORS_API_KEY:
        raise HTTPException(503, "OPENROUTE_API_KEY is not configured on the backend.")
    url = f"{ORS_BASE_URL}/v2/directions/driving-car/geojson"
    r = requests.post(
        url,
        headers={
            "Authorization": ORS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/geo+json, application/json",
        },
        json={
            "coordinates": [[start[1], start[0]], [end[1], end[0]]],
            "elevation": True,
            "instructions": True,
        },
        timeout=35,
    )
    try:
        data = r.json()
    except ValueError:
        raise HTTPException(r.status_code, f"Routing service returned HTTP {r.status_code}.")
    if not r.ok or not data.get("features"):
        err = data.get("error", data.get("message", "No route returned"))
        if isinstance(err, dict):
            err = err.get("message", str(err))
        raise HTTPException(r.status_code, f"Routing error: {err}")
    feature = data["features"][0]
    props = feature.get("properties", {})
    summary = props.get("summary", {})
    coords = feature.get("geometry", {}).get("coordinates", [])
    if not coords:
        raise HTTPException(502, "Routing service returned no geometry.")
    elevations = [float(p[2]) for p in coords if len(p) > 2 and p[2] is not None]
    ascent = descent = 0.0
    if len(elevations) >= 2:
        diffs = np.diff(elevations)
        ascent = float(np.sum(diffs[diffs > 0]))
        descent = float(-np.sum(diffs[diffs < 0]))
    distance = float(summary.get("distance", 0)) / 1000
    duration = float(summary.get("duration", 0)) / 60
    steps = sum(len(seg.get("steps", [])) for seg in props.get("segments", []))
    city_fraction = max(0.0, min(1.0, (steps / max(distance, 1.0) - 0.2) / 1.8))
    # GeoJSON -> Leaflet friendly [lat, lon].
    points = [[float(p[1]), float(p[0])] for p in coords]
    return {
        "distance_km": distance,
        "duration_min": duration,
        "ascent_m": ascent,
        "descent_m": descent,
        "city_fraction": city_fraction,
        "points": points,
    }


def terrain_factor(ascent_m, distance_km):
    return max(0.70, min(1.02, 1.0 - 0.012 * (ascent_m / max(distance_km, 1.0))))


def weather_factor(temp_c, wind_kmh, rain_mm):
    f = 1.0
    if temp_c < 15:
        f -= min(0.15, (15 - temp_c) * 0.008)
    elif temp_c > 30:
        f -= min(0.12, (temp_c - 30) * 0.006)
    f -= min(0.12, max(0.0, wind_kmh - 10) * 0.003)
    f -= min(0.04, max(0.0, rain_mm) * 0.008)
    return max(0.72, min(1.02, f))


def driving_factor(city_fraction, style):
    penalties = {"Gentle": 0.65, "Normal": 1.0, "Aggressive": 1.45}
    return max(0.72, min(1.02, 1.0 - city_fraction * 0.16 * penalties[style]))


def prediction_result(payload: TripRequest, distance_km, ascent_m, descent_m, temp_c, wind_kmh, rain_mm, city_fraction, route_points=None, duration_min=None):
    df, model, metrics = artifacts()
    vehicle = df[
        (df["Make"] == payload.make)
        & (df["Model"] == payload.model)
        & (df["Vehicle class"] == payload.vehicle_class)
        & (df["Model year"] == payload.model_year)
    ]
    if vehicle.empty:
        # Allow a valid dataset row when the frontend record has a minor display mismatch.
        vehicle = df[(df["Make"] == payload.make) & (df["Model"] == payload.model)]
    if vehicle.empty:
        raise HTTPException(404, "Selected vehicle is not present in the supplied dataset.")
    row = pd.DataFrame([{
        "Model year": payload.model_year,
        "Make": payload.make,
        "Model": payload.model,
        "Vehicle class": payload.vehicle_class,
        "Motor (kW)": payload.motor_kw,
        "Recharge time (h)": payload.recharge_time_h,
    }])
    base_eff = float(model.predict(row)[0])
    tf = terrain_factor(ascent_m, distance_km)
    wf = weather_factor(temp_c, wind_kmh, rain_mm)
    dfac = driving_factor(city_fraction, payload.driving_style)
    real_eff = max(0.1, base_eff * tf * wf * dfac)
    usable_energy = payload.battery_kwh * payload.charge_percent / 100
    reserve_energy = payload.battery_kwh * payload.reserve_percent / 100
    energy_required = distance_km / real_eff
    range_km = real_eff * usable_energy
    safe_range_km = real_eff * max(0.0, usable_energy - reserve_energy)
    arrival_energy = usable_energy - energy_required
    arrival_soc = max(0.0, min(100.0, arrival_energy / payload.battery_kwh * 100))
    status = "REACHABLE" if distance_km <= safe_range_km else ("MARGINAL" if distance_km <= range_km else "CHARGE_REQUIRED")
    required_with_reserve = energy_required + reserve_energy
    charge_needed = max(0.0, required_with_reserve - usable_energy)
    return {
        "vehicle": {
            "make": payload.make,
            "model": payload.model,
            "model_year": payload.model_year,
            "vehicle_class": payload.vehicle_class,
            "motor_kw": payload.motor_kw,
            "recharge_time_h": payload.recharge_time_h,
            "dataset_efficiency": float(vehicle.iloc[0][TARGET]),
        },
        "route": {
            "distance_km": distance_km,
            "duration_min": duration_min,
            "ascent_m": ascent_m,
            "descent_m": descent_m,
            "city_fraction": city_fraction,
            "points": route_points or [],
        },
        "weather": {"temperature_c": temp_c, "wind_kmh": wind_kmh, "rain_mm": rain_mm},
        "prediction": {
            "base_efficiency_km_kwh": base_eff,
            "real_efficiency_km_kwh": real_eff,
            "energy_required_kwh": energy_required,
            "available_energy_kwh": usable_energy,
            "estimated_range_km": range_km,
            "safe_range_km": safe_range_km,
            "arrival_soc_percent": arrival_soc,
            "charge_needed_kwh": charge_needed,
            "status": status,
            "factors": {"terrain": tf, "weather": wf, "driving": dfac},
        },
        "model": metrics,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "ors_configured": bool(ORS_API_KEY)}


@app.get("/api/overview")
def overview():
    df, _, metrics = artifacts()
    return {
        "dataset_rows": int(len(df)),
        "makes": int(df["Make"].nunique()),
        "models": int(df["Model"].nunique()),
        "classes": int(df["Vehicle class"].nunique()),
        "efficiency_mean": float(df[TARGET].mean()),
        "efficiency_min": float(df[TARGET].min()),
        "efficiency_max": float(df[TARGET].max()),
        "model": metrics,
    }


@app.get("/api/vehicles")
def vehicles(search: str = "", make: str = "", limit: int = 250):
    df, _, _ = artifacts()
    out = df.copy()
    if make:
        out = out[out["Make"].eq(make)]
    if search:
        q = search.strip().lower()
        mask = out.apply(lambda row: q in " ".join(str(x).lower() for x in row[FEATURES]), axis=1)
        out = out[mask]
    out = out.sort_values(["Make", "Model", "Model year"]).head(max(1, min(limit, 1000)))
    return {"items": out[FEATURES + [TARGET]].to_dict(orient="records")}


@app.get("/api/vehicle-options")
def vehicle_options():
    df, _, _ = artifacts()
    return {
        "makes": sorted(df["Make"].unique().tolist()),
        "records": df[FEATURES + [TARGET]].sort_values(["Make", "Model", "Model year"]).to_dict(orient="records"),
    }


@app.get("/api/analytics")
def analytics():
    df, model, metrics = artifacts()
    # Permutation importance is computed on a deterministic sample to keep the endpoint responsive.
    sample = df.sample(min(300, len(df)), random_state=42)
    X = sample[FEATURES]
    y = sample[TARGET]
    pi = permutation_importance(model, X, y, n_repeats=3, random_state=42, scoring="r2", n_jobs=-1)
    importance = sorted(
        [{"feature": f, "importance": float(v)} for f, v in zip(FEATURES, pi.importances_mean)],
        key=lambda x: x["importance"], reverse=True,
    )
    distribution = (
        df.groupby("Vehicle class")[TARGET].mean().sort_values(ascending=False).head(10)
        .reset_index().rename(columns={TARGET: "efficiency"}).to_dict(orient="records")
    )
    return {"model": metrics, "feature_importance": importance, "class_efficiency": distribution}


@app.post("/api/trip/analyze")
def analyze_trip(payload: TripRequest):
    start = geocode(payload.start)
    end = geocode(payload.destination)
    if not start or not end:
        raise HTTPException(400, "Could not find the start or destination. Try a city and country.")
    rt = route(start, end)
    sw = weather(start[0], start[1])
    ew = weather(end[0], end[1])
    temp = (sw["temperature_c"] + ew["temperature_c"]) / 2
    wind = (sw["wind_kmh"] + ew["wind_kmh"]) / 2
    rain = (sw["rain_mm"] + ew["rain_mm"]) / 2
    result = prediction_result(
        payload,
        rt["distance_km"], rt["ascent_m"], rt["descent_m"], temp, wind, rain,
        rt["city_fraction"], rt["points"], rt["duration_min"],
    )
    result["locations"] = {
        "start": {"label": start[2], "lat": start[0], "lon": start[1]},
        "destination": {"label": end[2], "lat": end[0], "lon": end[1]},
    }
    return result


@app.post("/api/trip/analyze-manual")
def analyze_manual(payload: ManualTripRequest):
    return prediction_result(
        payload,
        payload.distance_km, payload.ascent_m, payload.descent_m,
        payload.temperature_c, payload.wind_kmh, payload.rain_mm,
        payload.city_fraction,
    )
