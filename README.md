# 🏆 AtmosTrack: Micro-Climate Physics Degradation Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit App](https://static.streamlit.io/badge-gradient-gradient.svg)](https://streamlit.io/)

**AtmosTrack** is an advanced micro-climate physics engine designed for front-office sports analytics. It mathematically proves and visualizes how outdoor stadium logistics, altitude, temperature, relative humidity, and wind shear alter the physical trajectory of a ball (football/baseball), degrading player metrics under specific atmospheric conditions.

Standard sports analytics treat every game environment equally, but **AtmosTrack** shatters this cognitive bias: *Weather data is actionable sports data.*

---

## 💡 The Core Hypothesis

When a front office evaluates a free-agent quarterback or pitcher, they assume the athlete's statistical production will perfectly translate to their new home stadium. However, shifts in temperature, wind shear, and barometric pressure drastically alter aerodynamic drag.

AtmosTrack calculates and visualizes this exact micro-climate performance degradation, answering a critical front-office question: 
> **Does this athlete have the physical mechanics to succeed in our specific stadium's atmosphere?**

---

## ⚙️ Core Technical Features

1. **Two-Step Live NOAA Weather Integration**: Queries real-time conditions by first resolving stadium coordinates to grid endpoints, then fetching live temperature, wind speed, and relative humidity values.
2. **Altitude-Based Pressure Scaling**: Uses the barometric equation to dynamically scale base air pressure based on stadium elevation (e.g., Coors Field's lower baseline density vs. Highmark Stadium).
3. **Advanced Flight Aerodynamics (Drag & Magnus Lift)**: Models both the deceleration drag force and the lateral/vertical Magnus breaking force ($\vec{F}_m$) based on spin rate ($RPM$) and pitch type (Fastball backspin rise, Slider sidespin break, Curveball topspin drop).
4. **Live MLB Statcast Telemetry**: Dynamically queries historical pitcher release velocity, spin rate, and 3D coordinate releases (using `pybaseball` Statcast data).
5. **Robust Handoff Data Contract**: Outputs structured dataframes matching the contract layout (`dummy_trajectory.csv`) for seamless integration with frontend 3D dashboards.

---

## 🧮 Theoretical Framework & Physics Equations

The AtmosTrack physics engine runs on the following aerodynamic framework:

### 1. Barometric Pressure Altitude Correction
Standard pressure ($P$) is calculated based on stadium elevation ($h$ in meters) using the barometric formula:
$$P = P_0 \left(1 - \frac{L \cdot h}{T_0}\right)^{\frac{g \cdot M}{R^* \cdot L}} \approx 101325 \left(1 - 2.25577 \times 10^{-5} \cdot h\right)^{5.25588}$$

### 2. Humid Air Density ($\rho$)
Calculates the combined density of dry air and water vapor:
$$\rho = \frac{p_{\text{dry}}}{R_{\text{dry}} \cdot T} + \frac{p_{\text{vapor}}}{R_{\text{vapor}} \cdot T}$$
Where saturation vapor pressure ($p_{\text{sat}}$) is calculated via the Tetens formula:
$$p_{\text{sat}} = 610.78 \cdot e^{\frac{17.27 \cdot T_c}{T_c + 237.3}}, \quad p_{\text{vapor}} = RH_{\text{fraction}} \cdot p_{\text{sat}}, \quad p_{\text{dry}} = P - p_{\text{vapor}}$$

### 3. Aerodynamic Drag Force ($F_d$)
$$F_d = \frac{1}{2} \rho v^2 C_d A$$

### 4. Magnus Lift & Break Force ($\vec{F}_m$)
$$\vec{F}_m = \frac{1}{2} \rho v^2 C_L A \cdot (\hat{\omega} \times \hat{v})$$
* $\hat{\omega}$ = unit vector of the spin axis.
* $C_L$ = lift coefficient, proportional to the dimensionless spin parameter ($S = \frac{r \cdot \omega}{v}$) and capped at $0.4$.

---

## 🛠️ Dataset Requisition Pipeline

The AtmosTrack architecture merges sports telemetry with atmospheric data:

| Data Type | Source / Library | Purpose |
| :--- | :--- | :--- |
| **Sports Telemetry** | `pybaseball` / `nfl-data-py` | Scrapes exact NFL passing trajectories or MLB Statcast pitch tracking and spin rates. |
| **Atmospheric Data** | NOAA Weather API | Pulls temperature, wind speed, and relative humidity matched to coordinates and ZIP code. |

```
                 +-------------------+      +-------------------+
                 |    pybaseball /   |      |    NOAA Weather   |
                 |   nfl-data-py     |      |        API        |
                 +---------+---------+      +---------+---------+
                           |                          |
                           v                          v
                     Sports Telemetry           Atmospheric Data
                           |                          |
                           +------------+-------------+
                                        |
                                        v
                            [ AtmosTrack Physics Engine ]
                                        |
                                        v
                            [ 3D Streamlit Dashboard ]
```

---

## 📁 Repository Structure

* **`engine.py`**: The core backend file containing data fetching functions (`fetch_player_telemetry`, `get_stadium_weather`) and simulation functions (`calculate_trajectory`).
* **`stadiums.json`**: Configuration file mapping test venues with coordinates, ZIPs, and elevation altitudes.
* **`dummy_trajectory.csv`**: Target contract output format mapping columns: `time_sec`, `x_coord`, `y_coord`, `z_coord`, `velocity_mph`, and `drag_force`.
* **`test_physics.py`**: Automated unit tests checking density, altitude pressure, and Magnus lift forces.
* **`requirements.txt`**: Python dependencies list.

---

## 🚀 Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ADITYA-TUMMURI/RosterResilience.git
   cd RosterResilience
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify the Physics Calculations (Unit Tests):**
   ```bash
   python test_physics.py
   ```

4. **Run Simulation Verification:**
   ```bash
   python engine.py
   ```
