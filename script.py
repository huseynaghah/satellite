import requests
from skyfield.api import Topos, load, EarthSatellite, utc
from datetime import datetime, timedelta

# === INPUT PARAMETERS ===
GROUND_LAT = 28.5721  # Example: Kennedy Space Center
GROUND_LON = -80.648
GROUND_ALT = 0
ELEVATION_MASK = 5  # Elevation mask angle in degrees
PREDICTION_DAYS = 2  # Days to predict passes

# === LOAD SKYFIELD TIME AND EPHEMERIS FILE ===
ts = load.timescale()
eph = load('de421.bsp')  # Load planetary ephemeris file

# === FUNCTION TO FETCH TLE DATA USING NORAD CATALOG NUMBER ===
import requests

# === FUNCTION TO FETCH TLE DATA USING N2YO API ===
def fetch_tle(norad_catalog_number):
    url = f"https://api.n2yo.com/rest/v1/satellite/tle/{norad_catalog_number}&apiKey=QCXV33-DM4QEP-ZL7KRD-5FFE"

    response = requests.get(url)
    
    if response.status_code == 200:
        try:
            # JSON formatında məlumat alırıq
            data = response.json()
            
            print("TEST")
            # 'tle' məlumatını tapırıq
            if 'tle' in data:
                tle_lines = data['tle'].strip().split('\n')
                
                if len(tle_lines) == 2:
                    return tle_lines
                else:
                    print("Error: Invalid TLE data in response.")
                    return None
            else:
                print("Error: 'tle' data not found in the response.")
                return None
        except ValueError as e:
            print(f"Error: Failed to parse JSON response - {e}")
            return None
    else:
        print(f"Error: Failed to fetch TLE data. Status code: {response.status_code}")
        return None


# === FUNCTION TO LOAD SATELLITE (TLE OR EPHEMERIS) ===
def load_satellite(use_tle=True, tle_lines=None, ephemeris_file=None, satellite_id=None):
    if use_tle:
        # Load satellite using TLE
        if tle_lines is None or len(tle_lines) < 2:
            raise ValueError("TLE lines must be provided for TLE mode.")
        return EarthSatellite(tle_lines[0], tle_lines[1], satellite_id, ts)
    else:
        # Load satellite using Ephemeris file
        if ephemeris_file is None or satellite_id is None:
            raise ValueError("Ephemeris file and satellite ID must be provided for Ephemeris mode.")
        satellite_ephemeris = load(ephemeris_file)
        return satellite_ephemeris[satellite_id]

# === SELECT MODE (TLE OR Ephemeris) ===
mode = input("Choose mode (TLE or Ephemeris): ").strip().lower()

if mode == "tle":
    # Input satellite NORAD catalog number
    norad_catalog_number = input("Enter NORAD Catalog Number: ").strip()

    # Fetch TLE data for the satellite using NORAD catalog number
    tle_lines = fetch_tle(norad_catalog_number)

    if tle_lines:
        satellite = load_satellite(use_tle=True, tle_lines=tle_lines, satellite_id="Unknown")
    else:
        print("Error: Could not fetch TLE data.")
        exit()

elif mode == "ephemeris":
    # Input Ephemeris file and satellite ID (example: ISS from JPL Horizons)
    ephemeris_file = "path/to/satellite.bsp"  # Replace with the path to your ephemeris file
    satellite_id = "ISS"  # Replace with the actual satellite ID in the ephemeris file
    satellite = load_satellite(use_tle=False, ephemeris_file=ephemeris_file, satellite_id=satellite_id)
else:
    print("Invalid mode selected. Choose either 'TLE' or 'Ephemeris'.")
    exit()

# Define Earth and ground station
earth = eph['earth']
ground_station = Topos(latitude_degrees=GROUND_LAT, longitude_degrees=GROUND_LON, elevation_m=GROUND_ALT)

# === FUNCTION TO COMPUTE ELEVATION ANGLE ===
def compute_elevation(time):
    # Satellitin və yer stansiyasının mövqelərini GEOSENTRIK çərçivədə hesabla
    satellite_pos = satellite.at(time)
    ground_station_pos = ground_station.at(time)
    
    difference = satellite_pos - ground_station_pos  # İndi hər iki vektor GEOSENTRIK-dir
    alt, az, d = difference.altaz()
    return alt.degrees

# === FUNCTION TO PREDICT MULTIPLE PASSES ===TLE
def predict_passes():
    time_now = ts.from_datetime(datetime.now(utc))  # Timezone-aware datetime
    end_time = time_now + PREDICTION_DAYS

    passes = []
    aos_time, los_time = None, None
    time_check = time_now

    while time_check.tt < end_time.tt:
        elevation = compute_elevation(time_check)

        if elevation >= ELEVATION_MASK and aos_time is None:
            aos_time = time_check.utc_datetime()

        if elevation < ELEVATION_MASK and aos_time is not None:
            los_time = time_check.utc_datetime()
            passes.append((aos_time, los_time))
            aos_time, los_time = None, None

        time_check = time_check + 10 / 86400

    return passes

# === OUTPUT RESULTS ===
predicted_passes = predict_passes()

if predicted_passes:
    print(f"Upcoming passes in the next {PREDICTION_DAYS} days:")
    for idx, (aos, los) in enumerate(predicted_passes, start=1):
        duration = (los - aos).total_seconds()
        print(f"Pass {idx}:")
        print(f"  AOS: {aos} UTC")
        print(f"  LOS: {los} UTC")
        print(f"  Duration: {duration:.0f} seconds\n")
else:
    print("No passes found within the prediction period.")
