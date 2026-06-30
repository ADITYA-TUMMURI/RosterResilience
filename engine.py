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
# 1. SPORTS TELEMETRY INTEGRATION (pybaseball / nfl-data-py Reference)
# =====================================================================
"""
To integrate actual MLB Statcast pitch tracking or NFL passing trajectories,
install the packages and query them using the patterns below:

--- MLB Statcast (pybaseball) Example ---
from pybaseball import playerid_lookup, statcast_pitcher

# 1. Look up a player's ID (e.g., Tarik Skubal)
player_info = playerid_lookup('skubal', 'tarik')
player_id = player_info['key_mlbam'].values[0] # Returns the MLBAM ID

# 2. Fetch Statcast pitches within a date range
pitch_data = statcast_pitcher('2024-05-01', '2024-05-15', player_id)

# 3. Clean and extract key parameters:
# - release_speed: Initial velocity of the pitch (mph)
# - release_spin_rate: Spin rate of the ball (rpm)
# - release_pos_x, release_pos_y, release_pos_z: Release coordinates (ft)
# - vx0, vy0, vz0: Velocity vectors at y=50ft (ft/s)
# - ax, ay, az: Acceleration vectors (ft/s^2)
"""


# =====================================================================
# 2. ATMOSPHERIC DATA ACQUISITION (NOAA Weather API)
# =====================================================================

def get_stadium_weather(latitude: float, longitude: float) -> dict:
    """
    Fetches real-time/historical weather data for a stadium using the NOAA API.
    
    Args:
        latitude (float): Latitude of the stadium.
        longitude (float): Longitude of the stadium.
        
    Returns:
        dict: Weather parameters including temperature (F), wind speed (mph), and pressure (Pa).
    """
    # NOAA API requires a User-Agent header representing the application
    headers = {
        "User-Agent": "AtmosTrackSportsAnalytics/1.0 (adityafrom2007@gmail.com)"
    }
    
    try:
        # Step 1: Query the endpoints for the specific latitude and longitude grid points
        url = f"https://api.weather.gov/points/{latitude},{longitude}"
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        point_data = response.json()
        
        # Step 2: Fetch forecast hourly or current observation endpoint from response
        forecast_url = point_data["properties"]["forecastHourly"]
        forecast_response = requests.get(forecast_url, headers=headers, timeout=5)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        # Extract latest hourly period
        current_period = forecast_data["properties"]["periods"][0]
        
        temp_f = current_period["temperature"]
        # Extract wind speed (e.g. "12 mph" or "5 to 10 mph")
        wind_str = current_period["windSpeed"]
        wind_digits = [int(s) for s in wind_str.split() if s.isdigit()]
        wind_mph = sum(wind_digits) / len(wind_digits) if wind_digits else 0.0
        
        # NOAA API does not always supply raw station pressure in the basic forecast.
        # We fall back to standard sea-level pressure (101325 Pa) if not present.
        pressure_pa = 101325.0 
        
        return {
            "temperature_f": float(temp_f),
            "wind_speed_mph": float(wind_mph),
            "pressure_pa": pressure_pa,
            "source": "NOAA Forecast API"
        }
        
    except Exception as e:
        # Fallback placeholder values in case API limit is reached or internet is disconnected
        print(f"NOAA API warning: {e}. Utilizing fallback placeholder values.")
        return {
            "temperature_f": 59.0,      # 15 deg C (Standard temp)
            "wind_speed_mph": 5.0,
            "pressure_pa": 101325.0,
            "source": "Fallback Defaults"
        }


# =====================================================================
# 3. CORE PHYSICS ENGINE
# =====================================================================

def calculate_air_density(pressure_pa: float, temp_f: float) -> float:
    """
    Calculates the air density (rho) in kg/m^3.
    Formula: rho = P / (R_specific * T)
    """
    R_SPECIFIC = 287.058  # Specific gas constant for dry air in J/(kg*K)
    
    # Convert Fahrenheit to Kelvin
    temp_k = (temp_f - 32) * (5.0 / 9.0) + 273.15
    
    # Calculate density
    rho = pressure_pa / (R_SPECIFIC * temp_k)
    return rho


def calculate_drag_force(rho: float, velocity_mps: float, drag_coeff: float, area_m2: float) -> float:
    """
    Calculates the aerodynamic drag force (Fd) in Newtons.
    Formula: Fd = 0.5 * rho * v^2 * Cd * A
    """
    fd = 0.5 * rho * (velocity_mps ** 2) * drag_coeff * area_m2
    return fd


# =====================================================================
# 4. HANDOFF FUNCTION
# =====================================================================

def calculate_trajectory(player_id: str, temp_f: float, wind_speed_mph: float) -> pd.DataFrame:
    """
    Calculates the 3D trajectory of a ball under specific atmospheric conditions
    and returns a pandas DataFrame matching the 'dummy_trajectory.csv' schema.
    
    Args:
        player_id (str): Player ID or identifier.
        temp_f (float): Temperature in Fahrenheit.
        wind_speed_mph (float): Wind speed in mph.
        
    Returns:
        pd.DataFrame: Dataframe with time_sec, x_coord, y_coord, z_coord, velocity_mph, drag_force.
    """
    # 1. Physics & Ball properties (Defaults representing a baseball)
    DRAG_COEFF = 0.3              # Baseball drag coefficient
    BALL_RADIUS_M = 0.0366        # Baseball radius (meters)
    BALL_AREA_M2 = math.pi * (BALL_RADIUS_M ** 2)
    BALL_MASS_KG = 0.145          # Baseball mass (kg)
    GRAVITY = 9.80665             # Acceleration due to gravity (m/s^2)
    
    # 2. Get atmospheric density
    # Assume standard pressure (101325 Pa) for calculations
    pressure_pa = 101325.0
    rho = calculate_air_density(pressure_pa, temp_f)
    
    # 3. Initial state values (simulating a standard fast release)
    # Convert wind speed to m/s
    wind_mps = wind_speed_mph * 0.44704
    
    # Let's say initial release velocity is 95 mph -> convert to m/s
    initial_velocity_mph = 95.0
    v0_mps = initial_velocity_mph * 0.44704
    
    # Initial release positions in meters (release height ~ 6 ft -> 1.83 m)
    x = 0.0
    y = 0.0
    z = 1.83
    
    # Simple pitch release angles (straight pitch down the zone)
    vx = 0.0
    vy = v0_mps
    vz = -0.5 # slight downward slope
    
    # Simulation settings
    dt = 0.1 # time step in seconds
    steps = 5
    
    time_sec_list = []
    x_coord_list = []
    y_coord_list = []
    z_coord_list = []
    velocity_mph_list = []
    drag_force_list = []
    
    for i in range(steps):
        t = i * dt
        
        # Calculate current scalar velocity relative to the air (with wind blowing directly against/with the ball)
        # For simplicity, assume wind is a headwind blowing against the y-axis movement
        v_relative = math.sqrt(vx**2 + (vy + wind_mps)**2 + vz**2)
        v_scalar_mph = math.sqrt(vx**2 + vy**2 + vz**2) / 0.44704
        
        # Calculate drag force in Newtons
        fd = calculate_drag_force(rho, v_relative, DRAG_COEFF, BALL_AREA_M2)
        
        # Record state at time t
        time_sec_list.append(round(t, 2))
        x_coord_list.append(round(x * 3.28084, 2)) # Convert meters to feet for baseball coords
        y_coord_list.append(round(y * 3.28084, 2))
        z_coord_list.append(round(z * 3.28084, 2))
        velocity_mph_list.append(round(v_scalar_mph, 2))
        drag_force_list.append(round(fd, 4))
        
        # Update physics state (Euler integration)
        # Drag direction acts opposite to velocity vector relative to air
        ax = -(fd * (vx / v_relative)) / BALL_MASS_KG
        ay = -(fd * ((vy + wind_mps) / v_relative)) / BALL_MASS_KG
        az = -GRAVITY - (fd * (vz / v_relative)) / BALL_MASS_KG
        
        # Update position
        x += vx * dt
        y += vy * dt
        z += vz * dt
        
        # Update velocity
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
    # Test script: run simple simulation for Coors Field (high altitude / lower air density)
    print("Testing AtmosTrack Physics Engine...")
    print(f"Standard Air Density at 80F: {calculate_air_density(101325.0, 80.0):.4f} kg/m^3")
    print(f"Standard Air Density at 20F: {calculate_air_density(101325.0, 20.0):.4f} kg/m^3")
    
    df_warm = calculate_trajectory(player_id="skubal_tarik", temp_f=80.0, wind_speed_mph=0.0)
    df_cold = calculate_trajectory(player_id="skubal_tarik", temp_f=20.0, wind_speed_mph=15.0)
    
    print("\n--- Warm Game Trajectory (80F, 0mph wind) ---")
    print(df_warm.to_string(index=False))
    
    print("\n--- Cold/Windy Game Trajectory (20F, 15mph wind) ---")
    print(df_cold.to_string(index=False))
