import streamlit as st
import requests
import pandas as pd
from skyfield.api import Topos, load, EarthSatellite, utc
from datetime import datetime, timedelta
import json

# Streamlit konfiqurasiyası
st.set_page_config(page_title="Satellite Pass Predictor", page_icon="🛰️")

# TLE alma funksiyası
def fetch_tle(norad_id):
    url = f"https://api.n2yo.com/rest/v1/satellite/tle/{norad_id}&apiKey=QCXV33-DM4QEP-ZL7KRD-5FFE"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['tle'].split('\n')[:2]
        return None
    except:
        return None

# Yüksəklik bucağının hesablanması
def compute_elevation(satellite, ground_station, time):
    difference = satellite.at(time) - ground_station.at(time)
    return difference.altaz()[0].degrees

# Görüşlərin proqnozlaşdırılması
def predict_passes(satellite, ground_station, start_time, days, elevation_mask):
    ts = load.timescale()
    end_time = start_time + timedelta(days=days)
    time_step = timedelta(minutes=1)
    
    passes = []
    current_time = start_time
    in_pass = False
    
    while current_time <= end_time:
        t = ts.from_datetime(current_time)
        elev = compute_elevation(satellite, ground_station, t)
        
        if elev >= elevation_mask and not in_pass:
            aos = current_time
            in_pass = True
        elif elev < elevation_mask and in_pass:
            los = current_time
            passes.append({
                "AOS": aos.strftime('%Y-%m-%d %H:%M:%S UTC'),
                "LOS": los.strftime('%Y-%m-%d %H:%M:%S UTC'),
                "Duration": (los - aos).total_seconds()
            })
            in_pass = False
        
        current_time += time_step
    
    return passes

# Streamlit UI
st.title("🛰️ Satellite Pass Predictor")

# Parametrlər
with st.sidebar:
    st.header("⚙️ Parametrlər")
    ground_lat = st.number_input("En dərəcəsi", value=28.5721)
    ground_lon = st.number_input("Uzunluq dərəcəsi", value=-80.648)
    ground_alt = st.number_input("Hündürlük (metr)", value=0)
    elevation_mask = st.slider("Minimum yüksəklik bucağı (°)", 0, 10, 5)
    prediction_days = st.slider("Proqnoz müddəti (gün)", 1, 7, 2)
    mode = st.radio("Rejim", ['TLE', 'Ephemeris'])

# Əsas hissə
if mode == 'TLE':
    norad_id = st.text_input("🔢 NORAD ID", "25544")
    with st.expander("📝 TLE-ləri əl ilə daxil edin"):
        manual_tle1 = st.text_input("TLE Satır 1")
        manual_tle2 = st.text_input("TLE Satır 2")
elif mode == 'Ephemeris':
    st.info("⏳ Ephemeris rejimi hazırlıq mərhələsindədir")

# Xəritə
with st.expander("🗺️ Yer stansiyasının mövqeyi", expanded=True):
    st.map(pd.DataFrame({'lat': [ground_lat], 'lon': [ground_lon]}))

# Hesablama
if st.button("🚀 Proqnozu hesabla"):
    if mode == 'TLE':
        tle_lines = None
        
        # Manual TLE yoxlanışı
        if manual_tle1.strip() and manual_tle2.strip():
            if manual_tle1.startswith('1 ') and manual_tle2.startswith('2 '):
                tle_lines = [manual_tle1, manual_tle2]
            else:
                st.error("❌ TLE formatı yanlış! Satırlar '1 ' və '2 ' ilə başlamalıdır.")
        
        # NORAD ID ilə TLE alma
        else:
            if not norad_id.strip():
                st.error("❌ Zəhmət olmasa NORAD ID və ya TLE daxil edin")
            else:
                with st.spinner("📡 Peyk məlumatları yüklənir..."):
                    tle_lines = fetch_tle(norad_id)

        if tle_lines:
            with st.spinner("🔭 Görüşlər hesablanır..."):
                satellite = EarthSatellite(tle_lines[0], tle_lines[1], "Satellite", load.timescale())
                ground_station = Topos(
                    latitude_degrees=ground_lat,
                    longitude_degrees=ground_lon,
                    elevation_m=ground_alt
                )
                
                passes = predict_passes(
                    satellite, 
                    ground_station,
                    datetime.now(utc), 
                    prediction_days, 
                    elevation_mask
                )
            
            if passes:
                df = pd.DataFrame(passes)
                st.markdown("""
                <style>
                .results-table {font-size:14px !important;}
                .download-btn {margin-top:10px !important;}
                </style>
                """, unsafe_allow_html=True)

                with st.container():
                    st.subheader(f"📅 Nəticələr ({len(passes)} görüş)")
                    st.markdown('<div class="results-table">', unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 CSV Yüklə",
                            data=df.to_csv(index=False).encode('utf-8'),
                            file_name=f"satellite_passes_{norad_id}.csv",
                            mime='text/csv',
                            key='csv-download'
                        )
                    with col2:
                        st.download_button(
                            label="📥 JSON Yüklə",
                            data=json.dumps(passes, indent=2),
                            file_name=f"satellite_passes_{norad_id}.json",
                            mime='application/json',
                            key='json-download'
                        )
            else:
                st.warning("🤷‍♂️ Seçilmiş parametrlərlə görüş tapılmadı")
        else:
            st.error("❌ TLE məlumatları alına bilmədi")

# Kömək bölməsi
with st.expander("❓ Təlimat", expanded=False):
    st.markdown("""
    1. NORAD ID daxil edin (məs: ISS üçün 25544) VƏ ya TLE-ləri əl ilə əlavə edin
    2. Parametrləri tənzimləyin
    3. "Proqnozu hesabla" düyməsini basın
    4. Nəticələri cədvəldə görün və ya yükləyin
    """)

st.caption("Made with ❤️ using Streamlit | Skyfield | N2YO API")