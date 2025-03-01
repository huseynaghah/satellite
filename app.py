import streamlit as st
from skyfield.api import Topos, load, EarthSatellite, wgs84
from datetime import datetime, timedelta
from pytz import utc
import pandas as pd

# === TLE MƏLUMATLARI ===
TLE_LINE1 = "1 25544U 98067A   24044.54861111  .00016717  00000-0  31093-3 0  9991"
TLE_LINE2 = "2 25544  51.6423  86.8571 0005862 353.1438   6.9713 15.50086448430704"

satellite = EarthSatellite(TLE_LINE1, TLE_LINE2, "ISS (ZARYA)", load.timescale())

# === Streamlit UI ===
st.title("📡 Peyk Keçid Hesablama Sistemi")

# İstifadəçi girişlərini alırıq
st.sidebar.header("Yerüstü Stansiya Məlumatları")
GROUND_LAT = st.sidebar.number_input("Enlik (Lat)", value=28.5721, format="%.4f")
GROUND_LON = st.sidebar.number_input("Uzunluq (Lon)", value=-80.648, format="%.4f")
GROUND_ALT = st.sidebar.number_input("Hündürlük (m)", value=0, step=10)

ELEVATION_MASK = st.sidebar.slider("Minimum yüksəklik (°)", min_value=0, max_value=90, value=5)
PREDICTION_DAYS = st.sidebar.slider("Proqnoz günləri", min_value=1, max_value=7, value=2)

# Hesablama düyməsi
if st.sidebar.button("Hesabla"):
    # === Skyfield parametrləri ===
    ts = load.timescale()
    eph = load('de421.bsp')
    ground_station = wgs84.latlon(GROUND_LAT, GROUND_LON, GROUND_ALT)

    # Keçidləri hesablamaq üçün funksiya
    def compute_elevation(time):
        difference = satellite.at(time) - ground_station.at(time)
        alt, az, d = difference.altaz()
        return alt.degrees

    def predict_passes():
        utc_now = datetime.now(utc)
        time_now = ts.utc(utc_now)
        end_time = time_now + timedelta(days=PREDICTION_DAYS)
        time_step = 10  # Addım (saniyə)

        passes = []
        aos_time, los_time = None, None
        time_check = time_now

        while time_check < end_time:
            elevation = compute_elevation(time_check)

            if elevation >= ELEVATION_MASK and aos_time is None:
                aos_time = time_check.utc_datetime()

            if elevation < ELEVATION_MASK and aos_time is not None:
                los_time = time_check.utc_datetime()
                passes.append((aos_time, los_time))
                aos_time, los_time = None, None

            time_check = time_check + timedelta(seconds=time_step)

        return passes

    # === Spinner əlavə et ===
    with st.spinner("Hesablama gedir... Zəhmət olmasa gözləyin..."):
        # Keçidləri hesabla
        predicted_passes = predict_passes()

    # Nəticələri göstər
    if predicted_passes:
        data = []
        for idx, (aos, los) in enumerate(predicted_passes, start=1):
            duration = (los - aos).total_seconds()
            data.append([idx, aos.strftime("%Y-%m-%d %H:%M:%S UTC"), los.strftime("%Y-%m-%d %H:%M:%S UTC"), f"{duration:.0f} saniyə"])

        df = pd.DataFrame(data, columns=["#", "AOS (Başlanğıc)", "LOS (Bitmə)", "Müddət"])
        st.success(f"✅ {PREDICTION_DAYS} gün üçün {len(predicted_passes)} keçid tapıldı.")
        st.dataframe(df)
    else:
        st.warning("⚠️ Heç bir keçid tapılmadı.")
