"""
RosterResilience: Micro-Climate Physics Degradation Engine
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
    Specifically pulls temperature, wind speed, and relative humidity.
    """
    headers = {
        "User-Agent": "RosterResilienceSportsAnalytics/1.0 (adityafrom2007@gmail.com)"
    }
    
    try:
        # Step 1: Resolve lat/long to grid point
        url = f"https://api.weather.gov/points/{latitude},{longitude}"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        point_data = response.json()
        
        # Step 2: Fetch hourly forecast from the resolved grid url
        forecast_url = point_data["properties"]["forecastHourly"]
        forecast_response = requests.get(forecast_url, headers=headers, timeout=5)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        current_period = forecast_data["properties"]["periods"][0]
        
        temp_f = current_period["temperature"]
        
        # Parse Wind Speed (e.g. "12 mph" or "5 to 10 mph")
        wind_str = current_period["windSpeed"]
        wind_digits = [int(s) for s in wind_str.split() if s.isdigit()]
        wind_mph = sum(wind_digits) / len(wind_digits) if wind_digits else 0.0
        
        # Parse Relative Humidity from NOAA response properties
        # NOAA response format: "relativeHumidity": {"unitCode": "wmoUnit:percent", "value": 68}
        humidity = 50.0
        if "relativeHumidity" in current_period and current_period["relativeHumidity"].get("value") is not None:
            humidity = float(current_period["relativeHumidity"]["value"])
        
        return {
            "temperature_f": float(temp_f),
            "wind_speed_mph": float(wind_mph),
            "relative_humidity": humidity,
            "source": "NOAA Forecast API"
        }
        
    except Exception as e:
        print(f"NOAA API warning: {e}. Utilizing fallback weather defaults.")
        return {
            "temperature_f": 59.0,  # standard 15C
            "wind_speed_mph": 5.0,
            "relative_humidity": 50.0,
            "source": "Fallback Defaults"
        }


# =====================================================================
# 3. CORE PHYSICS ENGINE (With Drag and Magnus Spin-Lift Force)
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
    if temp_k < 1.0:
        temp_k = 1.0  # Prevent division by zero or negative absolute temperature
    temp_c = temp_k - 273.15
    
    # Saturation vapor pressure (Tetens equation in Pascals)
    p_sat = 610.78 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    
    # Partial pressure of water vapor (cannot exceed total atmospheric pressure)
    p_vapor = min(pressure_pa, (relative_humidity / 100.0) * p_sat)
    
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


def calculate_magnus_force(rho: float, velocity_mps: float, spin_rpm: float, area_m2: float, ball_radius_m: float) -> float:
    """
    Calculates the magnitude of the Magnus Force (Fm) in Newtons.
    Formula: Fm = 0.5 * rho * v^2 * Cl * A
    Where Cl (Lift Coefficient) is modeled as Cl = 0.4 * SpinParameter (capped at 0.4)
    """
    if velocity_mps <= 0.01:
        return 0.0
        
    # Convert RPM to angular velocity (rad/s)
    omega_rads = spin_rpm * (2 * math.pi / 60.0)
    
    # Dimensionless Spin Parameter: S = (r * omega) / v
    spin_parameter = (ball_radius_m * omega_rads) / velocity_mps
    
    # Empirical lift coefficient calculation based on baseball aerodynamics (Nathan, 2008)
    lift_coeff = min(0.4, 1.5 * spin_parameter)
    
    fm = 0.5 * rho * (velocity_mps ** 2) * lift_coeff * area_m2
    return fm


# =====================================================================
# 4. HANDOFF FUNCTION
# =====================================================================

def calculate_trajectory(player_id: str, temp_f: float = None, wind_speed_mph: float = None, relative_humidity: float = None, stadium_name: str = "Coors Field", pitch_type: str = "fastball") -> pd.DataFrame:
    """
    Calculates the 3D trajectory of a baseball incorporating air density, altitude,
    headwind/tailwind, and Magnus spin-break effects.
    
    Returns:
        pd.DataFrame matching the 'dummy_trajectory.csv' schema.
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
    if temp_f is None or wind_speed_mph is None or relative_humidity is None:
        weather = get_stadium_weather(lat, lon)
        if temp_f is None:
            temp_f = weather["temperature_f"]
        if wind_speed_mph is None:
            wind_speed_mph = weather["wind_speed_mph"]
        if relative_humidity is None:
            relative_humidity = weather["relative_humidity"]
            
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
    spin_rpm = telemetry["spin_rate_rpm"]
    
    # Convert feet release coordinates to meters
    x = telemetry["release_pos_x_ft"] * 0.3048
    y = 0.0 # start mound distance at 0
    z = telemetry["release_pos_z_ft"] * 0.3048
    
    # Initial velocity vectors
    vx = 0.0
    vy = v0_mps
    vz = -0.5 # downward trajectory angle
    
    # Wind speed (headwind blowing in -y direction)
    wind_mps = wind_speed_mph * 0.44704
    
    # Define spin axis vector based on pitch type
    # For a pitch traveling primarily in the +y direction:
    pitch_type = pitch_type.lower()
    if pitch_type == "fastball":
        # Backspin: spin axis points in +x direction. Force points upwards (+z)
        spin_axis = [1.0, 0.0, 0.0]
    elif pitch_type in ["curveball", "curve"]:
        # Topspin: spin axis points in -x direction. Force points downwards (-z)
        spin_axis = [-1.0, 0.0, 0.0]
    elif pitch_type in ["slider", "sweeper"]:
        # Sidespin: spin axis points in -z direction. Force points right (+x)
        spin_axis = [0.0, 0.0, -1.0]
    else:
        # Generic neutral spin
        spin_axis = [0.0, 0.0, 0.0]
        
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
        v_relative_y = vy + wind_mps
        v_relative = math.sqrt(vx**2 + v_relative_y**2 + vz**2)
        v_scalar_mph = math.sqrt(vx**2 + vy**2 + vz**2) / 0.44704
        
        # Force calculations
        fd = calculate_drag_force(rho, v_relative, DRAG_COEFF, BALL_AREA_M2)
        fm_magnitude = calculate_magnus_force(rho, v_relative, spin_rpm, BALL_AREA_M2, BALL_RADIUS_M)
        
        # Record state
        time_sec_list.append(round(t, 2))
        x_coord_list.append(round(x * 3.28084, 2))
        y_coord_list.append(round(y * 3.28084, 2))
        z_coord_list.append(round(z * 3.28084, 2))
        velocity_mph_list.append(round(v_scalar_mph, 2))
        drag_force_list.append(round(fd, 4))
        
        # 1. Acceleration due to Drag (opposite to velocity vector relative to air)
        ax_drag = -(fd * (vx / v_relative)) / BALL_MASS_KG
        ay_drag = -(fd * (v_relative_y / v_relative)) / BALL_MASS_KG
        az_drag = -(fd * (vz / v_relative)) / BALL_MASS_KG
        
        # 2. Acceleration due to Magnus Effect (cross product of spin axis and velocity direction)
        # Force direction = spin_axis x velocity_direction
        v_dir_x = vx / v_relative
        v_dir_y = v_relative_y / v_relative
        v_dir_z = vz / v_relative
        
        # Cross product components: spin_axis x v_dir
        fm_dir_x = spin_axis[1] * v_dir_z - spin_axis[2] * v_dir_y
        fm_dir_y = spin_axis[2] * v_dir_x - spin_axis[0] * v_dir_z
        fm_dir_z = spin_axis[0] * v_dir_y - spin_axis[1] * v_dir_x
        
        ax_magnus = (fm_magnitude * fm_dir_x) / BALL_MASS_KG
        ay_magnus = (fm_magnitude * fm_dir_y) / BALL_MASS_KG
        az_magnus = (fm_magnitude * fm_dir_z) / BALL_MASS_KG
        
        # Total Acceleration (Drag + Magnus + Gravity)
        ax = ax_drag + ax_magnus
        ay = ay_drag + ay_magnus
        az = az_drag + az_magnus - GRAVITY
        
        # Euler integration step
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
    print("Testing Fully Featured RosterResilience Physics Engine (Drag + Magnus Effect)...")
    
    # Test NOAA weather lookup relative humidity inclusion
    stadium_weather = get_stadium_weather(39.756, -104.994)
    print(f"Live Coors Field NOAA Weather: {stadium_weather}")
    
    # Compare Magnus breaking effects for a Fastball vs a Slider
    print("\nSimulating Fastball (Backspin) at Coors Field (Warm/Dry):")
    df_fb = calculate_trajectory(player_id="tarik skubal", temp_f=80.0, wind_speed_mph=0.0, relative_humidity=20.0, stadium_name="Coors Field", pitch_type="fastball")
    print(df_fb.to_string(index=False))
    
    print("\nSimulating Slider (Sidespin) at Coors Field (Warm/Dry):")
    df_sld = calculate_trajectory(player_id="tarik skubal", temp_f=80.0, wind_speed_mph=0.0, relative_humidity=20.0, stadium_name="Coors Field", pitch_type="slider")
    print(df_sld.to_string(index=False))
