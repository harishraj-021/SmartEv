"""
Smart EV Range Predictor - Website (live terrain + weather + route map)
Run locally:  streamlit run app.py

Data sources (both free):
  - OpenRouteService  -> route distance, total climb, AND route geometry (needs free key)
  - Open-Meteo        -> temperature + wind, geocoding (no key)
"""
import streamlit as st
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
import requests
import folium
from streamlit_folium import st_folium
import polyline as polyline_lib

# ---------- load the trained model once ----------
@st.cache_resource
def load_model():
    """Train the model once from the CSV at startup (no pickle -> no version issues)."""
    df = pd.read_csv("EV Energy Efficiency Dataset.csv")
    X = df.drop(columns=["Energy Efficiency (km/kWh)"]).copy()
    y = df["Energy Efficiency (km/kWh)"]
    encoders = {}
    for col in ["Make", "Model", "Vehicle class"]:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        encoders[col] = le
    feature_order = X.columns.tolist()
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    return rf, encoders, feature_order

model, encoders, feature_order = load_model()

# ================= LIVE DATA HELPERS =================
@st.cache_data(show_spinner=False)
def geocode(place_name):
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": place_name, "count": 1}, timeout=10)
        results = r.json().get("results")
        if not results:
            return None
        top = results[0]
        return (top["latitude"], top["longitude"], top.get("name", place_name))
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def get_route(ors_key, start, end):
    """ORS driving route with elevation + geometry. start/end = (lat, lon)."""
    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ors_key, "Content-Type": "application/json"}
        body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]],
                "elevation": True}
        r = requests.post(url, json=body, headers=headers, timeout=20)
        data = r.json()
        route = data["routes"][0]
        # geometry is an encoded polyline string -> list of (lat, lon)
        pts = polyline_lib.decode(route["geometry"])   # [(lat, lon), ...]
        return {"distance_km": route["summary"]["distance"] / 1000.0,
                "ascent_m": route.get("ascent", 0),
                "points": pts}
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(show_spinner=False)
def get_weather(lat, lon):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": lat, "longitude": lon,
                                 "current": "temperature_2m,wind_speed_10m"}, timeout=10)
        cur = r.json()["current"]
        return {"temp_c": cur["temperature_2m"], "wind_kmh": cur["wind_speed_10m"]}
    except Exception as e:
        return {"error": str(e)}

# ---------- factors ----------
def terrain_factor(total_ascent_m, distance_km):
    climb_per_km = total_ascent_m / max(distance_km, 1)
    return max(0.6, min(1.05, 1.0 - (climb_per_km / 10) * 0.04))

def weather_factor(temp_c, wind_kmh):
    factor = 1.0
    if temp_c < 15:
        factor -= (15 - temp_c) * 0.01
    if temp_c > 30:
        factor -= (temp_c - 30) * 0.005
    factor -= max(0, wind_kmh - 10) * 0.003
    return max(0.6, min(1.05, factor))

def enc(col, value):
    le = encoders[col]
    return le.transform([value])[0] if value in le.classes_ else 0

# ================= PAGE =================
st.set_page_config(page_title="Smart EV Range Predictor", page_icon="🔋", layout="wide")
st.title("🔋 Smart EV Range Predictor")
st.caption("Will your EV make the trip? Live terrain + weather + route map.")

# session defaults
defaults = {"distance": 120.0, "ascent": 100.0, "temp": 20.0, "wind": 5.0,
            "route_points": None, "start_ll": None, "end_ll": None}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---------------- LIVE TRIP LOOKUP ----------------
with st.expander("🌍 Enter your trip", expanded=True):
    ors_key = st.text_input("OpenRouteService API key", type="password",
                            help="Free key from openrouteservice.org (2000 calls/day). "
                                 "Needed to draw the route; weather works without it.")
    c1, c2 = st.columns(2)
    start_name = c1.text_input("Start place", "Chennai")
    end_name = c2.text_input("Destination", "Bangalore")

    if st.button("🔎 Fetch route + weather", use_container_width=True):
        s, e = geocode(start_name), geocode(end_name)
        if not s or not e:
            st.error("Couldn't find one of those places. Check spelling.")
        else:
            st.session_state.start_ll = (s[0], s[1])
            st.session_state.end_ll = (e[0], e[1])
            w = get_weather(e[0], e[1])
            if "error" not in w:
                st.session_state.temp = float(w["temp_c"])
                st.session_state.wind = float(w["wind_kmh"])
                st.success(f"Weather at {e[2]}: {w['temp_c']}°C, wind {w['wind_kmh']} km/h")
            if ors_key:
                route = get_route(ors_key, (s[0], s[1]), (e[0], e[1]))
                if "error" not in route:
                    st.session_state.distance = round(route["distance_km"], 1)
                    st.session_state.ascent = round(route["ascent_m"], 0)
                    st.session_state.route_points = route["points"]
                    st.success(f"Route: {route['distance_km']:.0f} km, "
                               f"{route['ascent_m']:.0f} m climb")
                else:
                    st.warning("Route lookup failed — check your ORS key.")
            else:
                st.info("No ORS key — weather filled; enter a key to draw the route.")

# ---------------- INPUTS ----------------
left, right = st.columns(2)
with left:
    st.subheader("Your car")
    make = st.selectbox("Make", sorted(encoders["Make"].classes_))
    model_name = st.selectbox("Model", sorted(encoders["Model"].classes_))
    vclass = st.selectbox("Vehicle class", sorted(encoders["Vehicle class"].classes_))
    year = st.slider("Model year", 2012, 2026, 2022)
    motor = st.slider("Motor (kW)", 40, 500, 110)
    recharge = st.slider("Recharge time (h)", 1.0, 12.0, 7.0, 0.5)
    battery = st.number_input("Battery capacity (kWh)", 10, 150, 40)
    charge = st.slider("Current charge (%)", 0, 100, 80)
with right:
    st.subheader("Your trip")
    distance = st.number_input("Trip distance (km)", 1.0, 2000.0, key="distance")
    ascent = st.number_input("Total climb on route (m)", 0.0, 8000.0, key="ascent")
    temp = st.slider("Temperature (°C)", -20.0, 45.0, key="temp")
    wind = st.slider("Wind speed (km/h)", 0.0, 100.0, key="wind")

go = st.button("Check my trip", type="primary", use_container_width=True)

# ---------------- DECISION + MAP ----------------
if go:
    row = pd.DataFrame([[year, enc("Make", make), enc("Model", model_name),
                         enc("Vehicle class", vclass), motor, recharge]],
                       columns=feature_order)
    base_eff = model.predict(row)[0]
    tf = terrain_factor(ascent, distance)
    wf = weather_factor(temp, wind)
    real_eff = base_eff * tf * wf
    usable = battery * (charge / 100.0)
    rng = real_eff * usable
    safe = rng * 0.9

    m1, m2, m3 = st.columns(3)
    m1.metric("Base efficiency", f"{base_eff:.2f} km/kWh")
    m2.metric("Real efficiency", f"{real_eff:.2f} km/kWh", f"{(real_eff-base_eff):.2f}")
    m3.metric("Predicted range", f"{rng:.0f} km")
    st.write(f"Terrain **{tf:.2f}** · Weather **{wf:.2f}** · "
             f"Trip **{distance:.0f} km** vs safe range **{safe:.0f} km**")

    if distance <= safe:
        st.success("✅ REACHABLE — you can complete this trip.")
    elif distance <= rng:
        st.warning("⚠️ MARGINAL — close to the limit, charging recommended.")
    else:
        st.error("🔴 CHARGE NOW — you will NOT make it. Charge before starting.")

    # ---- the map ----
    pts = st.session_state.route_points
    if pts:
        st.subheader("🗺️ Route — green = reachable, red = beyond range")
        mid = pts[len(pts) // 2]
        fmap = folium.Map(location=[mid[0], mid[1]], zoom_start=7)

        # split the line at the fraction of distance the range covers
        covered = min(1.0, rng / max(distance, 1))
        split = max(1, int(len(pts) * covered))

        folium.PolyLine(pts[:split], color="green", weight=6,
                        tooltip="Reachable on current charge").add_to(fmap)
        if split < len(pts):
            folium.PolyLine(pts[split-1:], color="red", weight=6,
                            tooltip="Beyond range — charge needed").add_to(fmap)
            # mark where charge runs out
            folium.Marker(pts[split-1], tooltip="Charge runs out here",
                          icon=folium.Icon(color="orange", icon="bolt", prefix="fa")).add_to(fmap)

        if st.session_state.start_ll:
            folium.Marker(st.session_state.start_ll, tooltip="Start",
                          icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(fmap)
        if st.session_state.end_ll:
            folium.Marker(st.session_state.end_ll, tooltip="Destination",
                          icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(fmap)

        fmap.fit_bounds([pts[0], pts[-1]])
        st_folium(fmap, width=900, height=500, returned_objects=[])
    elif st.session_state.start_ll:
        st.info("Add your OpenRouteService key and re-fetch to draw the route line.")

st.divider()
st.caption("Model: Random Forest, Natural Resources Canada EV data (R²≈0.91). "
           "Route: OpenRouteService · Weather: Open-Meteo. Factors are tunable estimates.")
