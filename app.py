import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import folium

from streamlit_folium import st_folium
import polyline as polyline_lib

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SmartEV — EV Energy & Range Planner",
    page_icon="⚡",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("⚡ SmartEV")
st.subheader("EV Energy Efficiency & Range Prediction")

st.caption(
    "Machine Learning + route terrain + weather + driving conditions"
)


# ============================================================
# LOAD DATASET
# ============================================================

DATASET = "EV Energy Efficiency Dataset.csv"

try:
    df = pd.read_csv(DATASET)
except FileNotFoundError:
    st.error(
        f"Dataset not found: {DATASET}\n\n"
        "Make sure the CSV is in the same folder as app.py."
    )
    st.stop()


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "Make",
    "Model",
    "Vehicle class",
    "Model year",
    "Motor (kW)",
    "Recharge time (h)",
    "Battery capacity (kWh)",
    "Energy Efficiency (km/kWh)"
]

missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

if missing:
    st.error(
        "The dataset is missing these columns:\n\n"
        + ", ".join(missing)
    )
    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================

numeric_columns = [
    "Model year",
    "Motor (kW)",
    "Recharge time (h)",
    "Battery capacity (kWh)",
    "Energy Efficiency (km/kWh)"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)


# ============================================================
# TRAIN RANDOM FOREST MODEL
# ============================================================

@st.cache_resource
def train_model(data):

    X = data.drop(
        columns=["Energy Efficiency (km/kWh)"]
    ).copy()

    y = data["Energy Efficiency (km/kWh)"]

    encoders = {}

    categorical_columns = [
        "Make",
        "Model",
        "Vehicle class"
    ]

    for col in categorical_columns:
        encoder = LabelEncoder()
        X[col] = encoder.fit_transform(
            X[col].astype(str)
        )
        encoders[col] = encoder

    feature_order = X.columns.tolist()

    # --------------------------------------------------------
    # Train/Test Split
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    r2 = r2_score(y_test, predictions)
    mae = mean_absolute_error(y_test, predictions)
    rmse = np.sqrt(
        mean_squared_error(y_test, predictions)
    )

    # Final model trained using all dataset rows
    final_model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    final_model.fit(X, y)

    return (
        final_model,
        encoders,
        feature_order,
        X_test,
        y_test,
        predictions,
        r2,
        mae,
        rmse
    )


(
    model,
    encoders,
    feature_order,
    X_test,
    y_test,
    test_predictions,
    r2,
    mae,
    rmse
) = train_model(df)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("SmartEV")

page = st.sidebar.radio(
    "Navigation",
    [
        "🚗 EV Prediction",
        "📊 Model Analytics",
        "🗺️ Trip Planner",
        "📋 Dataset"
    ]
)


# ============================================================
# HELPER FUNCTION
# ============================================================

def encode_value(column, value):

    encoder = encoders[column]

    value = str(value)

    if value in encoder.classes_:
        return encoder.transform([value])[0]

    return 0


# ============================================================
# PAGE 1 — EV PREDICTION
# ============================================================

if page == "🚗 EV Prediction":

    st.header("🚗 EV Energy Efficiency Prediction")

    st.info(
        "Vehicle options are taken directly from your supplied "
        "EV Energy Efficiency Dataset."
    )

    col1, col2 = st.columns(2)

    with col1:

        makes = sorted(
            df["Make"].astype(str).unique()
        )

        make = st.selectbox(
            "Manufacturer",
            makes
        )

        make_df = df[
            df["Make"].astype(str) == make
        ]

        models = sorted(
            make_df["Model"].astype(str).unique()
        )

        model_name = st.selectbox(
            "Model",
            models
        )

        model_df = make_df[
            make_df["Model"].astype(str)
            == model_name
        ]

        model_df = model_df.sort_values(
            [
                "Model year",
                "Vehicle class",
                "Motor (kW)",
                "Battery capacity (kWh)"
            ]
        ).reset_index(drop=True)

        if len(model_df) > 1:

            options = []

            for _, row in model_df.iterrows():

                label = (
                    f"{int(row['Model year'])} | "
                    f"{row['Vehicle class']} | "
                    f"{row['Motor (kW)']:.0f} kW | "
                    f"{row['Battery capacity (kWh)']:.1f} kWh"
                )

                options.append(label)

            selected = st.selectbox(
                "Dataset vehicle configuration",
                options
            )

            selected_index = options.index(
                selected
            )

        else:

            selected_index = 0

        vehicle = model_df.iloc[selected_index]

    with col2:

        st.write("### Vehicle Specifications")

        st.metric(
            "Vehicle Class",
            str(vehicle["Vehicle class"])
        )

        st.metric(
            "Model Year",
            int(vehicle["Model year"])
        )

        st.metric(
            "Motor Power",
            f"{vehicle['Motor (kW)']:.1f} kW"
        )

        st.metric(
            "Battery",
            f"{vehicle['Battery capacity (kWh)']:.1f} kWh"
        )

        st.metric(
            "Recharge Time",
            f"{vehicle['Recharge time (h)']:.1f} h"
        )

    st.divider()

    charge = st.slider(
        "Current Battery Charge",
        0,
        100,
        80
    )

    predict_button = st.button(
        "⚡ Predict Efficiency",
        type="primary",
        use_container_width=True
    )

    if predict_button:

        row = pd.DataFrame(
            [[
                vehicle["Make"],
                vehicle["Model"],
                vehicle["Vehicle class"],
                vehicle["Model year"],
                vehicle["Motor (kW)"],
                vehicle["Recharge time (h)"],
                vehicle["Battery capacity (kWh)"]
            ]],
            columns=[
                "Make",
                "Model",
                "Vehicle class",
                "Model year",
                "Motor (kW)",
                "Recharge time (h)",
                "Battery capacity (kWh)"
            ]
        )

        for col in [
            "Make",
            "Model",
            "Vehicle class"
        ]:
            row[col] = encode_value(
                col,
                row[col].iloc[0]
            )

        row = row[feature_order]

        prediction = model.predict(row)[0]

        available_energy = (
            vehicle["Battery capacity (kWh)"]
            * charge
            / 100
        )

        estimated_range = (
            prediction
            * available_energy
        )

        st.success("Prediction completed.")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Predicted Efficiency",
            f"{prediction:.2f} km/kWh"
        )

        c2.metric(
            "Available Energy",
            f"{available_energy:.2f} kWh"
        )

        c3.metric(
            "Estimated Range",
            f"{estimated_range:.0f} km"
        )


# ============================================================
# PAGE 2 — MODEL ANALYTICS
# ============================================================

elif page == "📊 Model Analytics":

    st.header("📊 Machine Learning Model Analytics")

    st.write(
        "The Random Forest model is evaluated using a held-out "
        "20% test set."
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "R² Score",
        f"{r2:.3f}"
    )

    c2.metric(
        "MAE",
        f"{mae:.3f} km/kWh"
    )

    c3.metric(
        "RMSE",
        f"{rmse:.3f} km/kWh"
    )

    c4.metric(
        "Training Samples",
        len(df)
    )

    st.divider()

    # --------------------------------------------------------
    # ACTUAL VS PREDICTED
    # --------------------------------------------------------

    st.subheader("📈 Actual vs Predicted Efficiency")

    graph_df = pd.DataFrame({
        "Actual": y_test.values,
        "Predicted": test_predictions
    })

    fig = px.scatter(
        graph_df,
        x="Actual",
        y="Predicted",
        title="Actual vs Predicted Energy Efficiency",
        labels={
            "Actual": "Actual Efficiency (km/kWh)",
            "Predicted": "Predicted Efficiency (km/kWh)"
        },
        hover_data={
            "Actual": ":.2f",
            "Predicted": ":.2f"
        }
    )

    minimum = min(
        graph_df["Actual"].min(),
        graph_df["Predicted"].min()
    )

    maximum = max(
        graph_df["Actual"].max(),
        graph_df["Predicted"].max()
    )

    fig.add_shape(
        type="line",
        x0=minimum,
        y0=minimum,
        x1=maximum,
        y1=maximum,
        line=dict(
            dash="dash"
        )
    )

    fig.update_layout(
        height=550
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        "Points closer to the diagonal line indicate more accurate predictions."
    )

    # --------------------------------------------------------
    # FEATURE IMPORTANCE
    # --------------------------------------------------------

    st.subheader("🔍 Feature Importance")

    importance_df = pd.DataFrame({
        "Feature": feature_order,
        "Importance": model.feature_importances_
    })

    importance_df = importance_df.sort_values(
        "Importance",
        ascending=True
    )

    fig_importance = px.bar(
        importance_df,
        x="Importance",
        y="Feature",
        orientation="h",
        title="Random Forest Feature Importance"
    )

    fig_importance.update_layout(
        height=500
    )

    st.plotly_chart(
        fig_importance,
        use_container_width=True
    )

    # --------------------------------------------------------
    # ERROR DISTRIBUTION
    # --------------------------------------------------------

    st.subheader("📉 Prediction Error Distribution")

    error_df = pd.DataFrame({
        "Prediction Error": (
            y_test.values - test_predictions
        )
    })

    fig_error = px.histogram(
        error_df,
        x="Prediction Error",
        nbins=25,
        title="Distribution of Prediction Errors"
    )

    fig_error.update_layout(
        height=450
    )

    st.plotly_chart(
        fig_error,
        use_container_width=True
    )


# ============================================================
# PAGE 3 — TRIP PLANNER
# ============================================================

elif page == "🗺️ Trip Planner":

    st.header("🗺️ EV Trip Energy Planner")

    st.write(
        "Estimate whether your selected EV can complete a trip "
        "using route distance, terrain, weather and battery charge."
    )

    col1, col2 = st.columns(2)

    with col1:

        start = st.text_input(
            "Start Location",
            "Chennai"
        )

    with col2:

        destination = st.text_input(
            "Destination",
            "Hyderabad"
        )

    distance = st.number_input(
        "Trip Distance (km)",
        min_value=1.0,
        max_value=5000.0,
        value=630.0
    )

    ascent = st.number_input(
        "Total Climb (m)",
        min_value=0.0,
        max_value=8000.0,
        value=0.0
    )

    temperature = st.slider(
        "Temperature (°C)",
        -20.0,
        50.0,
        28.0
    )

    wind = st.slider(
        "Wind Speed (km/h)",
        0.0,
        120.0,
        10.0
    )

    battery = st.number_input(
        "Battery Capacity (kWh)",
        min_value=1.0,
        max_value=200.0,
        value=24.0
    )

    charge = st.slider(
        "Current Charge (%)",
        0,
        100,
        80
    )

    if st.button(
        "⚡ Analyze Trip",
        type="primary",
        use_container_width=True
    ):

        # Basic trip adjustment factors
        terrain_factor = max(
            0.60,
            min(
                1.05,
                1.0 - ((ascent / max(distance, 1)) / 10.0) * 0.04
            )
        )

        weather_factor = 1.0

        if temperature < 15:
            weather_factor -= (
                15 - temperature
            ) * 0.01

        if temperature > 30:
            weather_factor -= (
                temperature - 30
            ) * 0.005

        weather_factor -= max(
            0,
            wind - 10
        ) * 0.003

        weather_factor = max(
            0.60,
            min(1.05, weather_factor)
        )

        # Use median dataset efficiency as a neutral baseline
        base_efficiency = df[
            "Energy Efficiency (km/kWh)"
        ].median()

        real_efficiency = (
            base_efficiency
            * terrain_factor
            * weather_factor
        )

        available_energy = (
            battery
            * charge
            / 100
        )

        estimated_range = (
            real_efficiency
            * available_energy
        )

        safe_range = estimated_range * 0.90

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Base Efficiency",
            f"{base_efficiency:.2f} km/kWh"
        )

        c2.metric(
            "Adjusted Efficiency",
            f"{real_efficiency:.2f} km/kWh"
        )

        c3.metric(
            "Estimated Range",
            f"{estimated_range:.0f} km"
        )

        c4.metric(
            "Trip Distance",
            f"{distance:.0f} km"
        )

        if distance <= safe_range:

            st.success(
                f"✅ REACHABLE — approximately "
                f"{safe_range:.0f} km safe range."
            )

        elif distance <= estimated_range:

            st.warning(
                "⚠️ MARGINAL — the vehicle may complete "
                "the trip, but there is little reserve."
            )

        else:

            st.error(
                f"🔴 CHARGE REQUIRED — approximately "
                f"{distance - estimated_range:.0f} km short."
            )

        st.subheader("Trip Factors")

        f1, f2 = st.columns(2)

        f1.metric(
            "Terrain Factor",
            f"{terrain_factor:.3f}"
        )

        f2.metric(
            "Weather Factor",
            f"{weather_factor:.3f}"
        )


# ============================================================
# PAGE 4 — DATASET
# ============================================================

elif page == "📋 Dataset":

    st.header("📋 EV Energy Efficiency Dataset")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Vehicles",
        len(df)
    )

    c2.metric(
        "Manufacturers",
        df["Make"].nunique()
    )

    c3.metric(
        "Vehicle Classes",
        df["Vehicle class"].nunique()
    )

    st.divider()

    st.dataframe(
        df,
        use_container_width=True,
        height=600
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "SmartEV | Random Forest | Scikit-learn | "
    "OpenRouteService | Open-Meteo"
)
