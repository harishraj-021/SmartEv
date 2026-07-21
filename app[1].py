"""
Smart EV Range Predictor - Website (with live terrain + weather)
Run locally:  streamlit run app.py

Live data sources (both free):
  - OpenRouteService  -> route distance + total climb   (needs a free API key)
  - Open-Meteo        -> temperature + wind             (no key needed)
"""
import streamlit as st
import pandas as pd
import joblib
import requests

# ---------- load the trained model once ----------
@st.cache_resource
def load_model():
    data = joblib.load("ev_model.pkl")
    return data["model"], data["encoders"], data["feature_order"]

model, encoders, feature_order = load_model()

# ================= LIVE DATA HELPERS =================

@st.cache_data(show_spinner=False)
def geocode(place_name):
    """Turn a place name into (lat, lon) using Open-Meteo geocoding (no key)."""
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
    """
    Ask OpenRouteService for a driving route with elevation.
    start, end = (lat, lon). Returns dict with distance_km and ascent_m.
    """
    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ors_key, "Content-Type": "application/json"}
        # ORS wants [lon, lat] order
        body = {
            "coordinates": [[start[1], start[0]], [end[1], end[0]]],
            "elevation": True,
        }
        r = requests.post(url, json=body, headers=headers, timeout=20)
        data = r.json()
        seg = data["routes"][0]["segments"][0]
        summary = data["routes"][0]["summary"]
        return {
            "distance_km": summary["distance"] / 1000.0,
            "ascent_m": data["routes"][0].get("ascent", seg.get("ascent", 0)),
        }
    except Exception as e:
        return {"error": str(e)}

@st.cache_data(show_spinner=False)
def get_weather(lat, lon):
    """Current temperature + wind from Open-Meteo (no key)."""
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": lat, "longitude": lon,
                                 "current": "temperature_2m,wind_speed_10m"},
                         timeout=10)
        cur = r.json()["current"]
        return {"temp_c": cur["temperature_2m"], "wind_kmh": cur["wind_speed_10m"]}
    except Exception as e:
        return {"error": str(e)}

# ---------- terrain & weather factors ----------
def terrain_factor(total_ascent_m, distance_km):
    climb_per_km = total_ascent_m / max(distance_km, 1)
    factor = 1.0 - (climb_per_km / 10) * 0.04
    return max(0.6, min(1.05, factor))

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
st.set_page_config(page_title="Smart EV Range Predictor", page_icon="🔋", layout="centered")
st.title("🔋 Smart EV Range Predictor")
st.caption("Will your EV make the trip? Now with live terrain + weather.")

# --- session state holds the auto-filled trip values ---
for k, v in {"distance": 120.0, "ascent": 100.0, "temp": 20.0, "wind": 5.0}.items():
    st.session_state.setdefault(k, v)

# ---------------- LIVE TRIP LOOKUP ----------------
with st.expander("🌍 Auto-fill trip from real places (optional)", expanded=True):
    ors_key = st.text_input("OpenRouteService API key",
                            type="password",
                            help="Free key from openrouteservice.org (2000 calls/day)")
    c1, c2 = st.columns(2)
    start_name = c1.text_input("Start place", "Chennai")
    end_name = c2.text_input("Destination", "Bangalore")

    if st.button("🔎 Fetch route + weather", use_container_width=True):
        s = geocode(start_name)
        e = geocode(end_name)
        if not s or not e:
            st.error("Couldn't find one of those places. Check spelling.")
        else:
            # weather at the destination (no key)
            w = get_weather(e[0], e[1])
            if "error" not in w:
                st.session_state.temp = float(w["temp_c"])
                st.session_state.wind = float(w["wind_kmh"])
                st.success(f"Weather at {e[2]}: {w['temp_c']}°C, wind {w['wind_kmh']} km/h")
            else:
                st.warning("Weather lookup failed; keeping manual values.")

            # route (needs ORS key)
            if ors_key:
                route = get_route(ors_key, (s[0], s[1]), (e[0], e[1]))
                if "error" not in route:
                    st.session_state.distance = round(route["distance_km"], 1)
                    st.session_state.ascent = round(route["ascent_m"], 0)
                    st.success(f"Route: {route['distance_km']:.0f} km, "
                               f"{route['ascent_m']:.0f} m total climb")
                else:
                    st.warning("Route lookup failed — enter an ORS key, or type distance manually.")
            else:
                st.info("No ORS key given — weather filled in; type distance & climb manually below.")

# ---------------- INPUTS ----------------
col1, col2 = st.columns(2)
with col1:
    st.subheader("Your car")
    make = st.selectbox("Make", sorted(encoders["Make"].classes_))
    model_name = st.selectbox("Model", sorted(encoders["Model"].classes_))
    vclass = st.selectbox("Vehicle class", sorted(encoders["Vehicle class"].classes_))
    year = st.slider("Model year", 2012, 2026, 2022)
    motor = st.slider("Motor (kW)", 40, 500, 110)
    recharge = st.slider("Recharge time (h)", 1.0, 12.0, 7.0, 0.5)
    battery = st.number_input("Battery capacity (kWh)", 10, 150, 40)
    charge = st.slider("Current charge (%)", 0, 100, 80)

with col2:
    st.subheader("Your trip")
    distance = st.number_input("Trip distance (km)", 1.0, 1000.0,
                               key="distance")
    ascent = st.number_input("Total climb on route (m)", 0.0, 5000.0,
                             key="ascent")
    temp = st.slider("Temperature (°C)", -20.0, 45.0, key="temp")
    wind = st.slider("Wind speed (km/h)", 0.0, 100.0, key="wind")

# ---------------- DECISION ----------------
if st.button("Check my trip", type="primary", use_container_width=True):
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

    st.write(f"Terrain factor **{tf:.2f}** · Weather factor **{wf:.2f}** · "
             f"Trip **{distance:.0f} km** vs safe range **{safe:.0f} km**")

    if distance <= safe:
        st.success("✅ REACHABLE — you can complete this trip.")
    elif distance <= rng:
        st.warning("⚠️ MARGINAL — close to the limit, charging recommended.")
    else:
        st.error("🔴 CHARGE NOW — you will NOT make it. Charge before starting.")

st.divider()
st.caption("Model: Random Forest on Natural Resources Canada EV data (R²≈0.91). "
           "Live route via OpenRouteService, weather via Open-Meteo. "
           "Terrain/weather factors are tunable estimates.")
