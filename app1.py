import streamlit as st
from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta
from pytz import utc

# === TLE MƏLUMATLARI ===
TLE_LINE1 = "1 25544U 98067A   24044.54861111  .00016717  00000-0  31093-3 0  9991"
TLE_LINE2 = "2 25544  51.6423  86.8571 0005862 353.1438   6.9713 15.50086448430704"

satellite = EarthSatellite(TLE_LINE1, TLE_LINE2, "ISS (ZARYA)", load.timescale())

# === FUNKSİYALAR ===
def compute_elevation(time, ground_station):
    difference = satellite.at(time) - ground_station.at(time)
    alt, az, d = difference.altaz()
    return alt.degrees

def predict_passes(lat, lon, alt, elevation_mask, prediction_days):
    ts = load.timescale()
    eph = load('de421.bsp')
    ground_station = wgs84.latlon(lat, lon, alt)

    utc_now = datetime.now(utc)
    time_now = ts.utc(utc_now)
    end_time = time_now + timedelta(days=prediction_days)
    time_step = 10  # Addım (saniyə)

    passes = []
    aos_time, los_time = None, None
    time_check = time_now

    while time_check < end_time:
        elevation = compute_elevation(time_check, ground_station)

        if elevation >= elevation_mask and aos_time is None:
            aos_time = time_check.utc_datetime()

        if elevation < elevation_mask and aos_time is not None:
            los_time = time_check.utc_datetime()
            passes.append((aos_time, los_time))
            aos_time, los_time = None, None

        time_check = time_check + timedelta(seconds=time_step)

    return passes

# === UI DİZAYNI ===
st.title("📡 Peyk Keçid Hesablama")

# === INPUTLAR ===
lat = st.number_input("Enlik (Lat)", value=28.5721)
lon = st.number_input("Uzunluq (Lon)", value=-80.648)
alt = st.number_input("Hündürlük (m)", value=0)
elevation_mask = st.number_input("Min yüksəklik (°)", value=5)
prediction_days = st.number_input("Proqnoz günləri", value=2)

# === HESABLAMA DÜYMƏSİ ===
if st.button("Hesabla"):
    with st.spinner("Hesablama gedir... Zəhmət olmasa gözləyin..."):
        passes = predict_passes(lat, lon, alt, elevation_mask, prediction_days)

    # === NƏTİCƏLƏR ===
    if passes:
        for idx, (aos, los) in enumerate(passes, start=1):
            duration = (los - aos).total_seconds()
            st.write(f"📡 Keçid {idx}:")
            st.write(f"  AOS: {aos} UTC")
            st.write(f"  LOS: {los} UTC")
            st.write(f"  Müddət: {duration:.0f} saniyə\n")
    else:
        st.write("⚠️ Heç bir keçid tapılmadı.")
