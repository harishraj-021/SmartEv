"""
================================================================================
 SMART EV RANGE PREDICTOR  —  India Edition
 Preventing mid-trip charge failure with Machine Learning + real-world factors
================================================================================
 Run locally:   streamlit run app.py
 Needs in the same folder:  EV Energy Efficiency Dataset.csv

 THREE-STAGE DESIGN
   Stage 1 (ML)      car specifications      -> base efficiency (km/kWh)
   Stage 2 (factors) base x terrain x weather x driving -> real efficiency
   Stage 3 (decide)  range = real eff x battery x charge%  ->  Reachable / Charge Now

 DATA SOURCES (all free)
   Terrain  : OpenRouteService  (route distance, ascent, descent, geometry)
   Weather  : Open-Meteo        (live temperature + wind, no API key)
   Route map: OpenRouteService polyline drawn with Folium
================================================================================
"""

import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
import polyline as polyline_lib

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error


# ==============================================================================
# STAGE 1 — MACHINE LEARNING MODEL  (trained once from CSV, then cached)
# Training from the CSV instead of a saved .pkl avoids any library-version
# mismatch between Colab and the deployment server.
# ==============================================================================
@st.cache_resource
def load_model():
    df = pd.read_csv("EV Energy Efficiency Dataset.csv")

    X = df.drop(columns=["Energy Efficiency (km/kWh)"]).copy()
    y = df["Energy Efficiency (km/kWh)"]

    encoders = {}
    for col in ["Make", "Model", "Vehicle class"]:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        encoders[col] = le

    feature_order = X.columns.tolist()

    # held-out split only to report an honest accuracy score
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    rf = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_tr, y_tr)
    pred = rf.predict(X_te)
    score = {"r2": r2_score(y_te, pred), "mae": mean_absolute_error(y_te, pred)}

    # final model trained on ALL rows for actual predictions
    rf_final = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)
    return rf_final, encoders, feature_order, score


model, encoders, feature_order, score = load_model()


def enc(col, value):
    """Turn one text value into the number the model was trained on."""
    le = encoders[col]
    return le.transform([value])[0] if value in le.classes_ else 0


# ==============================================================================
# INDIAN EV REFERENCE TABLE
# No open Indian EV efficiency dataset exists (public sources are registration
# counts or synthetic data). Indian specs are published as ARAI (MIDC cycle)
# figures, which are ~33% optimistic vs real-world tests. So this table supplies
# battery size and motor power only; efficiency still comes from the ML model.
# ==============================================================================
ARAI_REALISM = 0.67   # mean real-world / ARAI across the models below

INDIAN_EVS = {
    "— use dataset car below —": None,
    "Tata Tiago EV (24 kWh)":            dict(battery=24.0, motor=45,  arai=293, vclass="Subcompact"),
    "Tata Punch EV (35 kWh)":            dict(battery=35.0, motor=90,  arai=421, vclass="Subcompact"),
    "Tata Nexon EV MR (30 kWh)":         dict(battery=30.0, motor=95,  arai=275, vclass="Sport utility vehicle: Small"),
    "Tata Nexon EV Max (40.5 kWh)":      dict(battery=40.5, motor=105, arai=437, vclass="Sport utility vehicle: Small"),
    "Tata Nexon EV LR (45 kWh)":         dict(battery=45.0, motor=106, arai=489, vclass="Sport utility vehicle: Small"),
    "Tata Curvv EV (55 kWh)":            dict(battery=55.0, motor=123, arai=585, vclass="Sport utility vehicle: Small"),
    "Mahindra XUV400 EL Pro (39.4 kWh)": dict(battery=39.4, motor=110, arai=456, vclass="Sport utility vehicle: Small"),
    "MG Comet EV (17.3 kWh)":            dict(battery=17.3, motor=30,  arai=230, vclass="Minicompact"),
    "MG Windsor EV (38 kWh)":            dict(battery=38.0, motor=100, arai=332, vclass="Mid-size"),
    "MG ZS EV (50.3 kWh)":               dict(battery=50.3, motor=130, arai=461, vclass="Sport utility vehicle: Small"),
    "Hyundai Creta Electric (51.4 kWh)": dict(battery=51.4, motor=126, arai=473, vclass="Sport utility vehicle: Small"),
}


# ==============================================================================
# LIVE DATA HELPERS
# ==============================================================================
@st.cache_data(show_spinner=False)
def geocode(place_name):
    """Place name -> (lat, lon, clean_name).  Source: Open-Meteo (no key)."""
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": place_name, "count": 1}, timeout=10)
        results = r.json().get("results")
        if not results:
            return None
        t = results[0]
        return (t["latitude"], t["longitude"], t.get("name", place_name))
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def get_weather(lat, lon):
    """Live temperature + wind.  Source: Open-Meteo (no key)."""
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": lat, "longitude": lon,
                                 "current": "temperature_2m,wind_speed_10m"}, timeout=10)
        cur = r.json()["current"]
        return {"temp_c": float(cur["temperature_2m"]),
                "wind_kmh": float(cur["wind_speed_10m"])}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(show_spinner=False)
def get_route(ors_key, start, end):
    """Driving route with elevation + geometry.  Source: OpenRouteService."""
    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ors_key, "Content-Type": "application/json"}
        body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]],
                "elevation": True, "instructions": True}
        r = requests.post(url, json=body, headers=headers, timeout=25)
        data = r.json()
        if "routes" not in data:
            msg = data.get("error", "no route returned")
            msg = msg.get("message", str(msg)) if isinstance(msg, dict) else str(msg)
            return {"error": msg}

        route = data["routes"][0]
        distance_km = route["summary"]["distance"] / 1000.0

        # ORS with elevation=True returns a 3D polyline (lat, lon, elevation)
        try:
            raw = polyline_lib.decode(route["geometry"], geojson=False, precision=5)
            pts = [(p[0], p[1]) for p in raw]
        except Exception:
            pts = []
        if not pts:
            return {"error": "could not decode route geometry"}

        # city fraction from navigation-step density (many short steps = urban)
        steps = []
        for seg in route.get("segments", []):
            steps.extend(seg.get("steps", []))
        steps_per_km = len(steps) / max(distance_km, 1)
        city_fraction = max(0.0, min(1.0, (steps_per_km - 0.2) / (2.0 - 0.2)))

        return {"distance_km": distance_km,
                "ascent_m": float(route.get("ascent", 0)),
                "descent_m": float(route.get("descent", 0)),
                "city_fraction": city_fraction,
                "points": pts}
    except Exception as e:
        return {"error": str(e)}


# ==============================================================================
# STAGE 2 — THE THREE REAL-WORLD FACTORS  (each returns a multiplier near 1.0)
# ==============================================================================
def terrain_factor(total_ascent_m, distance_km):
    """Climbing spends energy lifting the car uphill (E = m*g*h)."""
    climb_per_km = total_ascent_m / max(distance_km, 1)
    return max(0.60, min(1.05, 1.0 - (climb_per_km / 10.0) * 0.04))


def weather_factor(temp_c, wind_kmh):
    """Cold: cabin heater + slow chemistry + capped regen. Heat: AC. Wind: drag."""
    f = 1.0
    if temp_c < 15:
        f -= (15 - temp_c) * 0.01
    if temp_c > 30:
        f -= (temp_c - 30) * 0.005
    f -= max(0.0, wind_kmh - 10) * 0.003
    return max(0.60, min(1.05, f))


def driving_factor(city_fraction, style, descent_m, distance_km):
    """Braking loss in stop-start traffic, partly recovered by regen on descents."""
    penalty = city_fraction * 0.18 * {"Gentle": 0.6, "Normal": 1.0, "Aggressive": 1.6}[style]
    regen = {"Gentle": 0.70, "Normal": 0.65, "Aggressive": 0.55}[style]
    downhill_share = min(1.0, (descent_m / max(distance_km, 1)) / 20.0)
    return max(0.60, min(1.05, 1.0 - penalty + downhill_share * 0.10 * regen))


# ==============================================================================
# PAGE
# ==============================================================================
st.set_page_config(page_title="Smart EV Range Predictor", page_icon="🔋", layout="wide")
st.title("🔋 Smart EV Range Predictor")
st.caption("Will your EV make the trip? Machine learning + live terrain, weather & driving.")

# values written by the Fetch button (v_ prefix so they are NOT widget keys)
defaults = {"v_distance": 120.0, "v_ascent": 100.0, "v_descent": 100.0,
            "v_temp": 20.0, "v_wind": 5.0, "v_city": 0.3,
            "route_points": None, "start_ll": None, "end_ll": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---------------- STEP 1 : trip lookup ----------------
with st.expander("🌍 Step 1 — enter your trip (auto-fills terrain, weather & driving)", expanded=True):
    ors_key = st.text_input("OpenRouteService API key", type="password",
                            help="Free key from openrouteservice.org (2000 calls/day). "
                                 "Needed for the route and map; weather works without it.")
    c1, c2 = st.columns(2)
    start_name = c1.text_input("Start place", "Chennai")
    end_name = c2.text_input("Destination", "Bangalore")

    if st.button("🔎 Fetch route + weather", use_container_width=True):
        s, e = geocode(start_name), geocode(end_name)
        if not s or not e:
            st.error("Couldn't find one of those places — check the spelling.")
        else:
            st.session_state.start_ll = (s[0], s[1])
            st.session_state.end_ll = (e[0], e[1])

            w = get_weather(e[0], e[1])
            if "error" not in w:
                st.session_state.v_temp = w["temp_c"]
                st.session_state.v_wind = w["wind_kmh"]

            if ors_key:
                route = get_route(ors_key, (s[0], s[1]), (e[0], e[1]))
                if "error" not in route:
                    st.session_state.v_distance = float(round(route["distance_km"], 1))
                    st.session_state.v_ascent = float(round(route["ascent_m"], 0))
                    st.session_state.v_descent = float(round(route["descent_m"], 0))
                    st.session_state.v_city = float(route["city_fraction"])
                    st.session_state.route_points = route["points"]
                else:
                    st.warning(f"Route lookup failed: {route['error']}")
            st.rerun()

# ---------------- STEP 2 : inputs ----------------
left, right = st.columns(2)

with left:
    st.subheader("🚗 Your car")

    india_pick = st.selectbox(
        "🇮🇳 Indian EV quick-select",
        list(INDIAN_EVS.keys()),
        help="Fills battery size, motor power and class for popular Indian EVs. "
             "Efficiency is still predicted by the ML model — ARAI figures are not "
             "used for training because the MIDC cycle is ~33% optimistic.")
    spec = INDIAN_EVS[india_pick]
    if spec:
        st.caption(f"ARAI claim: **{spec['arai']} km**  ·  realistic estimate: "
                   f"**{spec['arai'] * ARAI_REALISM:.0f} km** (×{ARAI_REALISM} cycle correction)")

    make = st.selectbox("Make", sorted(encoders["Make"].classes_))
    model_name = st.selectbox("Model", sorted(encoders["Model"].classes_))

    vclass_opts = sorted(encoders["Vehicle class"].classes_)
    vclass_idx = vclass_opts.index(spec["vclass"]) if spec and spec["vclass"] in vclass_opts else 0
    vclass = st.selectbox("Vehicle class", vclass_opts, index=vclass_idx)

    year = st.slider("Model year", 2012, 2026, 2022)
    motor = st.slider("Motor (kW)", 40, 500, int(spec["motor"]) if spec else 110)
    recharge = st.slider("Recharge time (h)", 1.0, 12.0, 7.0, 0.5)
    battery = st.number_input("Battery capacity (kWh)", 10.0, 150.0,
                              float(spec["battery"]) if spec else 40.0)
    charge = st.slider("Current charge (%)", 0, 100, 80)

with right:
    st.subheader("🛣️ Your trip")
    distance = st.number_input("Trip distance (km)", 1.0, 3000.0, value=st.session_state.v_distance)
    ascent = st.number_input("Total climb (m)  ← terrain", 0.0, 8000.0, value=st.session_state.v_ascent)
    descent = st.number_input("Total descent (m)  ← regen", 0.0, 8000.0, value=st.session_state.v_descent)
    temp = st.slider("Temperature (°C)  ← weather", -20.0, 45.0, value=st.session_state.v_temp)
    wind = st.slider("Wind speed (km/h)  ← weather", 0.0, 120.0, value=st.session_state.v_wind)

    st.markdown("**Driving / braking**")
    city_fraction = st.slider("City driving share (0 = all highway, 1 = all city)",
                              0.0, 1.0, value=st.session_state.v_city,
                              help="Auto-estimated from the route's navigation-step density.")
    style = st.select_slider("Driving style", options=["Gentle", "Normal", "Aggressive"], value="Normal")

go = st.button("⚡ Check my trip", type="primary", use_container_width=True)

# ---------------- STEP 3 : decision + map ----------------
if go:
    # STAGE 1 — model predicts what the car can do
    row = pd.DataFrame([[year, enc("Make", make), enc("Model", model_name),
                         enc("Vehicle class", vclass), motor, recharge]],
                       columns=feature_order)
    base_eff = model.predict(row)[0]

    # STAGE 2 — adjust for the trip
    tf = terrain_factor(ascent, distance)
    wf = weather_factor(temp, wind)
    dfac = driving_factor(city_fraction, style, descent, distance)
    real_eff = base_eff * tf * wf * dfac

    # STAGE 3 — range + decision
    usable = battery * (charge / 100.0)
    rng = real_eff * usable
    safe = rng * 0.9

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Base efficiency", f"{base_eff:.2f} km/kWh")
    m2.metric("Real efficiency", f"{real_eff:.2f} km/kWh", f"{real_eff - base_eff:+.2f}")
    m3.metric("Usable energy", f"{usable:.1f} kWh")
    m4.metric("Predicted range", f"{rng:.0f} km")

    f1, f2, f3 = st.columns(3)
    f1.metric("🏔️ Terrain", f"{tf:.3f}", f"{(tf-1)*100:+.1f}%")
    f2.metric("🌡️ Weather", f"{wf:.3f}", f"{(wf-1)*100:+.1f}%")
    f3.metric("🛑 Driving", f"{dfac:.3f}", f"{(dfac-1)*100:+.1f}%")

    st.caption(f"real efficiency = {base_eff:.2f} × {tf:.3f} (terrain) × {wf:.3f} (weather) "
               f"× {dfac:.3f} (driving) = **{real_eff:.2f} km/kWh**")

    if distance <= safe:
        st.success(f"✅ REACHABLE — {distance:.0f} km trip, {safe:.0f} km safe range.")
    elif distance <= rng:
        st.warning(f"⚠️ MARGINAL — {distance:.0f} km trip vs {rng:.0f} km range. "
                   "No safety margin; charge if you can.")
    else:
        st.error(f"🔴 CHARGE NOW — you are about {distance - rng:.0f} km short. "
                 "Charge before starting.")

    # route map
    pts = st.session_state.route_points
    if pts:
        st.subheader("🗺️ Route — green = reachable, red = beyond your charge")
        mid = pts[len(pts) // 2]
        fmap = folium.Map(location=[mid[0], mid[1]], zoom_start=7)

        covered = min(1.0, rng / max(distance, 1))
        split = max(1, int(len(pts) * covered))

        folium.PolyLine(pts[:split], color="green", weight=6,
                        tooltip="Reachable on current charge").add_to(fmap)
        if split < len(pts):
            folium.PolyLine(pts[split-1:], color="red", weight=6,
                            tooltip="Beyond range — charge needed").add_to(fmap)
            folium.Marker(pts[split-1], tooltip="⚡ Charge runs out near here",
                          icon=folium.Icon(color="orange", icon="bolt", prefix="fa")).add_to(fmap)

        if st.session_state.start_ll:
            folium.Marker(st.session_state.start_ll, tooltip="Start",
                          icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(fmap)
        if st.session_state.end_ll:
            folium.Marker(st.session_state.end_ll, tooltip="Destination",
                          icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(fmap)

        fmap.fit_bounds([pts[0], pts[-1]])
        st_folium(fmap, width=1000, height=500, returned_objects=[])
    else:
        st.info("Add your OpenRouteService key above and fetch a route to see the map.")

# ---------------- footer ----------------
st.divider()
with st.expander("ℹ️ How this works / data sources"):
    st.markdown(f"""
**Stage 1 — Machine Learning.** A Random Forest (100 trees) learns
`car specs → base efficiency` from 1197 real BEVs (Natural Resources Canada).
Held-out accuracy: **R² = {score['r2']:.3f}**, **MAE = {score['mae']:.3f} km/kWh**.

**Stage 2 — Real-world factors.** The dataset describes cars, not trips, so terrain,
weather and driving are applied *after* the model as multipliers:
`real efficiency = base × terrain × weather × driving`.

| Factor | Captures | Data source |
|---|---|---|
| 🏔️ Terrain | Energy lifting the car uphill | OpenRouteService ascent (Copernicus DEM) |
| 🌡️ Weather | Cabin heater, cold chemistry, headwind | Open-Meteo (free, no key) |
| 🛑 Driving | Braking losses, regen recovery | ORS step density + your style |
| 🇮🇳 Indian EVs | Battery & motor for Indian models | Manufacturer spec sheets |

**Stage 3 — Decision.** `range = real efficiency × battery × charge%`, compared with
trip distance and a 10% reserve → Reachable / Marginal / Charge Now.

**On braking data:** no public dataset links generic driver braking to car specs — it is
estimated from route composition plus driver style, as production systems do without live
telemetry. Factor constants are physically-motivated estimates, not fitted from driving logs.
""")
st.caption("Route: OpenRouteService · Weather & geocoding: Open-Meteo · Map: Folium/OpenStreetMap · "
           "Model: scikit-learn Random Forest")
