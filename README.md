# 🏆 RosterResilience (AtmosTrack)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit App](https://static.streamlit.io/badge-gradient-gradient.svg)](https://streamlit.io/)

**AtmosTrack** is a micro-climate physics degradation engine designed to prove how outdoor venue logistics and localized stadium micro-climates alter the physical trajectory of a ball (football/baseball) and degrade player performance under specific atmospheric conditions. 

Standard sports analytics treat every game environment equally, but **AtmosTrack** shatters this cognitive bias: *Weather data is actionable sports data.*

---

## 💡 The Core Hypothesis

When a front office evaluates a free-agent quarterback or pitcher, they assume the athlete's statistical production will perfectly translate to their new home stadium. However, shifts in temperature, wind shear, and barometric pressure drastically alter aerodynamic drag.

AtmosTrack calculates and visualizes this exact micro-climate performance degradation, answering a critical front-office question: 
> **Does this athlete have the physical mechanics to succeed in our specific stadium's atmosphere?**

---

## 🛠️ Dataset Requisition Pipeline

The engine seamlessly merges clean sports telemetry with high-fidelity atmospheric data:

| Data Type | Source / Library | Purpose |
| :--- | :--- | :--- |
| **Sports Telemetry** | `nfl-data-py` & `pybaseball` | Scrapes exact NFL passing trajectories or MLB Statcast pitch tracking and spin rates. |
| **Atmospheric Data** | NOAA Weather API | Pulls historical temperature, wind speed, and air density matched to the exact stadium timestamp and zip code. |

```
                 +-------------------+      +-------------------+
                 |  nfl-data-py /    |      |    NOAA Weather   |
                 |   pybaseball      |      |        API        |
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

## 🧮 The Physics Engine (Backend)

AtmosTrack does not rely on basic historical averages; it utilizes applied physics. The backend calculates an **Aerodynamic Drag Modifier** based on real-time air density ($\rho$). As temperature ($T$) drops and pressure ($P$) shifts, the drag force ($F_d$) on the ball increases, artificially degrading the athlete's metrics.

The core engine runs on the following aerodynamic framework:

### 1. Air Density Calculation ($\rho$)
$$\rho = \frac{P}{R_{\text{specific}} \cdot T}$$

Where:
* $P$ = Barometric Pressure (Pa)
* $R_{\text{specific}}$ = Specific gas constant for dry air ($287.058 \text{ J/(kg·K)}$)
* $T$ = Absolute Temperature (Kelvin)

### 2. Aerodynamic Drag Force ($F_d$)
$$F_d = \frac{1}{2} \rho v^2 C_d A$$

Where:
* $\rho$ = Calculated air density ($\text{kg/m}^3$)
* $v$ = Velocity of the ball relative to the air ($\text{m/s}$)
* $C_d$ = Drag coefficient of the ball (varies with seam structure & spin rate)
* $A$ = Cross-sectional area of the ball ($\text{m}^2$)

---

## 📊 Interactive Frontend Experience

The user interface transforms complex physics into immediate front-office insights:

* **3D Visualizations:** The Streamlit dashboard features interactive 3D Plotly scatter plots that map the exact trajectory of a football or baseball.
* **Dynamic Scenario Testing:** A General Manager can use UI sliders to dynamically drop the ambient temperature from **80°F** to **20°F** or increase wind speed.
* **Actionable Output:** As variables change, the 3D trajectory visually compresses on the screen in real-time. This mathematically proves whether a multi-million dollar free-agent target's arm strength can physically cut through high-density, freezing air in a cold-weather stadium.

---

## 🚀 Actionable Business Impact

AtmosTrack prevents multi-million dollar front-office mistakes. By visualizing the intersection of atmospheric science and sports finance, franchises can:
1. **Mitigate Free Agency Risk:** Avoid signing expensive players whose physical mechanics (e.g., lower spin rates or lower release velocity) are incompatible with their home stadium's micro-climate.
2. **Optimize Game-Plan Tactics:** Tailor passing/pitching strategies based on the projected weather density on game day.
3. **Draft Profiling:** Build target athletic profiles customized to the team's home venue micro-climate (e.g., favoring high-spin pitch profiles in low-temperature/high-density environments).

---

## 🛠️ Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ADITYA-TUMMURI/RosterResilience.git
   cd RosterResilience
   ```

2. **Set Up Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Dashboard:**
   ```bash
   streamlit run app.py
   ```
