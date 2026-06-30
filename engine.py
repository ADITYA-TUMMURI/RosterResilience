"""
AtmosTrack: Micro-Climate Physics Degradation Engine
AQX Sports Analytics Data Bowl #2
Backend Physics & Data Requisition Engine (engine.py)
"""

import json
import math
import pandas as pd
import requests

# =====================================================================
# 1. SPORTS TELEMETRY INTEGRATION (pybaseball / Statcast)
# =====================================================================

def fetch_player_telemetry(first_name: str, last_name: str, start_date: str = "2024-04-01", end_date: str = "2024-10-01") -> dict:
    """
    Uses pybaseball to fetch a pitcher's Statcast metrics.
    Retrieves average release velocity, spin rate, release height, and release coordinates.
    
    Args:
        first_name (str): Player's first name.
        last_name (str): Player's last name.
        start_date (str): Pitch date range start (YYYY-MM-DD).
        end_date (str): Pitch date range end (YYYY-MM-DD).
        
    Returns:
        dict: Average pitch metrics and coordinates.
    """
    try:
        from pybaseball import playerid_lookup, statcast_pitcher
        
        # 1. Lookup player ID
        print(f"Searching player ID for: {first_name} {last_name}...")
        lookup = playerid_lookup(last_name.lower(), first_name.lower())
        if lookup.empty:
            raise ValueError(f"Player {first_name} {last_name} not found in pybaseball lookup.")
        
        player_id = int(lookup['key_mlbam'].values[0])
        print(f"Found MLBAM Player ID: {player_id}")
        
        # 2. Fetch Statcast pitches
        print(f"Fetching Statcast pitch telemetry from {start_date} to {end_date}...")
        pitches = statcast_pitcher(start_date, end_date, player_id)
        if pitches.empty:
            raise ValueError(f"No pitch telemetry data found for player {player_id} in specified range.")
        
        # 3. Clean and aggregate key parameters
        valid_pitches = pitches.dropna(subset=['release_speed'])
        if valid_pitches.empty:
            raise ValueError("No pitch records found with valid release speeds.")
        
        avg_speed = float(valid_pitches['release_speed'].mean())
        avg_spin = float(valid_pitches['release_spin_rate'].mean()) if 'release_spin_rate' in valid_pitches else 2200.0
        
        # Average release positions (x: horizontal release, y: extension, z: vertical release)
        release_x = float(valid_pitches['release_pos_x'].mean()) if 'release_pos_x' in valid_pitches else 0.0
        release_y = float(valid_pitches['release_pos_y'].mean()) if 'release_pos_y' in valid_pitches else 54.5
        release_z = float(valid_pitches['release_pos_z'].mean()) if 'release_pos_z' in valid_pitches else 6.0
        
        return {
            "player_name": f"{first_name.capitalize()} {last_name.capitalize()}",
            "player_id": player_id,
            "release_speed_mph": avg_speed,
            "spin_rate_rpm": avg_spin,
            "release_pos_x_ft": release_x,
            "release_pos_y_ft": release_y,
            "release_pos_z_ft": release_z,
            "source": "Statcast (pybaseball)"
        }
        
    except Exception as e:
        print(f"Telemetry retrieval warning: {e}. Falling back to baseline pitcher metrics.")
        # Fallback to standard league-average fast pitcher (e.g. Tarik Skubal baseline)
        return {
            "player_name": f"{first_name.capitalize()} {last_name.capitalize()} (Fallback)",
            "player_id": 0,
            "release_speed_mph": 95.0,
            "spin_rate_rpm": 2400.0,
            "release_pos_x_ft": -1.5,
            "release_pos_y_ft": 54.5,
            "release_pos_z_ft": 6.1,
            "source": "Default Baseline"
        }


# =====================================================================
# 2. ATMOSPHERIC DATA ACQUISITION & BAROMETRIC ADJUSTMENTS
# =====================================================================

def get_pressure_for_altitude(altitude_meters: float) -> float:
    """
    Calculates standard barometric pressure in Pascals for a given altitude in meters
    using the barometric formula.
    
    Formula: P = P0 * (1 - L*h/T0) ^ (g*M / R*L)
    """
    P0 = 101325.0  # Sea-level standard pressure in Pa
    # Standard atmosphere equations simplified
    pressure = P0 * ((1.0 - 2.25577e-5 * altitude_meters) ** 5.25588)
    return pressure


def get_stadium_weather(latitude: float, longitude: float) -> dict:
    """
    Queries current/forecast weather metrics for a stadium from the NOAA API.
    """
    headers = {
        "User-Agent": "AtmosTrackSportsAnalytics/1.0 (adityafrom2007@gmail.com)"
    }
    
    try:
        url = f"https://api.weather.gov/points/{latitude},{longitude}"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        point_data = response.json()
        
        forecast_url = point_data["properties"]["forecastHourly"]
        forecast_response = requests.get(forecast_url, headers=headers, timeout=5)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        current_period = forecast_data["properties"]["periods"][0]
        
        temp_f = current_period["temperature"]
        wind_str = current_period["windSpeed"]
        wind_digits = [int(s) for s in wind_str.split() if s.isdigit()]
        wind_mph = sum(wind_digits) / len(wind_digits) if wind_digits else 0.0
        
        return {
            "temperature_f": float(temp_f),
            "wind_speed_mph": float(wind_mph),
            "source": "NOAA Forecast API"
        }
        
    except Exception as e:
        print(f"NOAA API warning: {e}. Utilizing fallback weather defaults.")
        return {
            "temperature_f": 59.0,  # standard 15C
            "wind_speed_mph": 5.0,
            "source": "Fallback Defaults"
        }


# =====================================================================
# 3. CORE PHYSICS ENGINE
# =====================================================================

def calculate_air_density(pressure_pa: float, temp_f: float, relative_humidity: float = 50.0) -> float:
    """
    Calculates humid air density (rho) in kg/m^3.
    Formula: rho = (p_dry / (R_dry * T)) + (p_vapor / (R_vapor * T))
    """
    R_DRY = 287.058     # Specific gas constant for dry air in J/(kg*K)
    R_VAPOR = 461.495   # Specific gas constant for water vapor in J/(kg*K)
    
    # Convert Fahrenheit to Kelvin
    temp_k = (temp_f - 32) * (5.0 / 9.0) + 273.15
    temp_c = temp_k - 273.15
    
    # Saturation vapor pressure (Tetens equation in Pascals)
    p_sat = 610.78 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    
    # Partial pressure of water vapor
    p_vapor = (relative_humidity / 100.0) * p_sat
    
    # Partial pressure of dry air
    p_dry = pressure_pa - p_vapor
    
    # Humid air density
    rho = (p_dry / (R_DRY * temp_k)) + (p_vapor / (R_VAPOR * temp_k))
    return rho


def calculate_drag_force(rho: float, velocity_mps: float, drag_coeff: float, area_m2: float) -> float:
    """
    Calculates aerodynamic drag force (Fd) in Newtons.
    Formula: Fd = 0.5 * rho * v^2 * Cd * A
    """
    fd = 0.5 * rho * (velocity_mps ** 2) * drag_coeff * area_m2
    return fd


# =====================================================================
# 4. HANDOFF FUNCTION
# =====================================================================

def calculate_trajectory(player_id: str, temp_f: float = None, wind_speed_mph: float = None, relative_humidity: float = 50.0, stadium_name: str = "Coors Field") -> pd.DataFrame:
    """
    Calculates the 3D trajectory of a baseball under specific atmospheric conditions
    and returns a pandas DataFrame matching the 'dummy_trajectory.csv' schema.
    """
    # 1. Physics & Ball properties (Defaults representing a baseball)
    DRAG_COEFF = 0.3              # Baseball drag coefficient
    BALL_RADIUS_M = 0.0366        # Baseball radius (meters)
    BALL_AREA_M2 = math.pi * (BALL_RADIUS_M ** 2)
    BALL_MASS_KG = 0.145          # Baseball mass (kg)
    GRAVITY = 9.80665             # Acceleration due to gravity (m/s^2)
    
    # 2. Load Stadium settings (altitude, coordinates)
    try:
        with open("stadiums.json", "r") as f:
            stadiums = json.load(f)
    except Exception:
        stadiums = {}
        
    stadium_info = stadiums.get(stadium_name, {
        "latitude": 39.756,
        "longitude": -104.994,
        "altitude_meters": 1585.0 # Coors Field fallback
    })
    
    lat = stadium_info["latitude"]
    lon = stadium_info["longitude"]
    altitude_m = stadium_info.get("altitude_meters", 0.0)
    
    # 3. Resolve atmospheric parameters (NOAA weather lookup if not overridden)
    if temp_f is None or wind_speed_mph is None:
        weather = get_stadium_weather(lat, lon)
        if temp_f is None:
            temp_f = weather["temperature_f"]
        if wind_speed_mph is None:
            wind_speed_mph = weather["wind_speed_mph"]
            
    pressure_pa = get_pressure_for_altitude(altitude_m)
    rho = calculate_air_density(pressure_pa, temp_f, relative_humidity)
    
    # 4. Fetch telemetry variables
    if player_id and isinstance(player_id, str) and len(player_id.split()) >= 2:
        parts = player_id.split()
        telemetry = fetch_player_telemetry(parts[0], parts[1])
    else:
        # Default fallback
        telemetry = {
            "player_name": "Tarik Skubal (Default)",
            "release_speed_mph": 95.0,
            "spin_rate_rpm": 2400.0,
            "release_pos_x_ft": -1.5,
            "release_pos_y_ft": 54.5,
            "release_pos_z_ft": 6.1
        }
        
    # 5. Initialize simulation parameters
    v0_mph = telemetry["release_speed_mph"]
    v0_mps = v0_mph * 0.44704
    
    # Convert feet release coordinates to meters
    x = telemetry["release_pos_x_ft"] * 0.3048
    y = 0.0 # start mound distance at 0
    z = telemetry["release_pos_z_ft"] * 0.3048
    
    # Velocities
    vx = 0.0
    vy = v0_mps
    vz = -0.5 # downward trajectory angle
    
    # Wind speed
    wind_mps = wind_speed_mph * 0.44704
    
    # Integration steps
    dt = 0.1
    steps = 5
    
    time_sec_list = []
    x_coord_list = []
    y_coord_list = []
    z_coord_list = []
    velocity_mph_list = []
    drag_force_list = []
    
    for i in range(steps):
        t = i * dt
        
        # Calculate velocity relative to wind (assuming headwind blowing against y axis)
        v_relative = math.sqrt(vx**2 + (vy + wind_mps)**2 + vz**2)
        v_scalar_mph = math.sqrt(vx**2 + vy**2 + vz**2) / 0.44704
        
        fd = calculate_drag_force(rho, v_relative, DRAG_COEFF, BALL_AREA_M2)
        
        time_sec_list.append(round(t, 2))
        x_coord_list.append(round(x * 3.28084, 2))
        y_coord_list.append(round(y * 3.28084, 2))
        z_coord_list.append(round(z * 3.28084, 2))
        velocity_mph_list.append(round(v_scalar_mph, 2))
        drag_force_list.append(round(fd, 4))
        
        # Acceleration
        ax = -(fd * (vx / v_relative)) / BALL_MASS_KG
        ay = -(fd * ((vy + wind_mps) / v_relative)) / BALL_MASS_KG
        az = -GRAVITY - (fd * (vz / v_relative)) / BALL_MASS_KG
        
        # Euler step
        x += vx * dt
        y += vy * dt
        z += vz * dt
        
        vx += ax * dt
        vy += ay * dt
        vz += az * dt
        
    df = pd.DataFrame({
        "time_sec": time_sec_list,
        "x_coord": x_coord_list,
        "y_coord": y_coord_list,
        "z_coord": z_coord_list,
        "velocity_mph": velocity_mph_list,
        "drag_force": drag_force_list
    })
    
    return df


if __name__ == "__main__":
    print("Testing Updated AtmosTrack Physics Engine...")
    
    # 1. Test Altitude Adjustment
    denver_pressure = get_pressure_for_altitude(1585.0)
    buffalo_pressure = get_pressure_for_altitude(183.0)
    print(f"Denver (Coors Field) Standard Pressure: {denver_pressure:.1f} Pa")
    print(f"Buffalo (Highmark Stadium) Standard Pressure: {buffalo_pressure:.1f} Pa")
    
    # 2. Test Density with Humidity
    rho_dry = calculate_air_density(101325.0, 59.0, relative_humidity=0.0)
    rho_humid = calculate_air_density(101325.0, 59.0, relative_humidity=100.0)
    print(f"Dry Air Density at 59F: {rho_dry:.4f} kg/m^3")
    print(f"Humid Air Density (100% RH) at 59F: {rho_humid:.4f} kg/m^3")
    
    # 3. Run comparative trajectories using a real player (or fallback)
    print("\nSimulating pitch for 'Tarik Skubal' at Coors Field (Warm/Dry):")
    df_denver = calculate_trajectory(player_id="tarik skubal", temp_f=80.0, wind_speed_mph=0.0, relative_humidity=20.0, stadium_name="Coors Field")
    print(df_denver.to_string(index=False))
    
    print("\nSimulating pitch for 'Tarik Skubal' at Highmark Stadium (Cold/Wet):")
    df_buffalo = calculate_trajectory(player_id="tarik skubal", temp_f=30.0, wind_speed_mph=10.0, relative_humidity=90.0, stadium_name="Highmark Stadium")
    print(df_buffalo.to_string(index=False))
