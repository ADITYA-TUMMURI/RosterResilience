import unittest
from engine import get_pressure_for_altitude, calculate_air_density, calculate_drag_force, calculate_magnus_force, calculate_trajectory

class TestRosterResiliencePhysics(unittest.TestCase):
    def test_altitude_pressure(self):
        # Sea level pressure should be 101325.0 Pa
        self.assertAlmostEqual(get_pressure_for_altitude(0.0), 101325.0, places=1)
        # Denver pressure should be significantly lower than sea level (~83.6 kPa)
        self.assertTrue(get_pressure_for_altitude(1585.0) < 90000.0)

    def test_air_density(self):
        # At 15C (59F) and 101325 Pa, dry air density should be approx 1.225 kg/m^3
        density = calculate_air_density(101325.0, 59.0, relative_humidity=0.0)
        self.assertAlmostEqual(density, 1.2250, places=3)
        
        # Humid air is less dense than dry air at the same pressure and temperature
        density_humid = calculate_air_density(101325.0, 59.0, relative_humidity=100.0)
        self.assertTrue(density_humid < density)

    def test_drag_force(self):
        # Fd = 0.5 * rho * v^2 * Cd * A
        fd = calculate_drag_force(rho=1.2, velocity_mps=40.0, drag_coeff=0.3, area_m2=0.0042)
        expected = 0.5 * 1.2 * (40.0**2) * 0.3 * 0.0042
        self.assertAlmostEqual(fd, expected, places=5)

    def test_magnus_force(self):
        # Fm = 0.5 * rho * v^2 * Cl * A
        # Let's test non-zero spin rate produces a positive lift magnitude
        fm = calculate_magnus_force(rho=1.2, velocity_mps=40.0, spin_rpm=2400.0, area_m2=0.0042, ball_radius_m=0.0366)
        self.assertTrue(fm > 0.0)
        
        # Lift coefficient capping test: spin_rpm=0 should yield 0 force
        fm_zero = calculate_magnus_force(rho=1.2, velocity_mps=40.0, spin_rpm=0.0, area_m2=0.0042, ball_radius_m=0.0366)
        self.assertEqual(fm_zero, 0.0)

    def test_trajectory_movements(self):
        # Run a fastball and slider simulation using fallback telemetry (to avoid network API calls during unit testing)
        df_fb = calculate_trajectory(player_id=None, temp_f=70.0, wind_speed_mph=0.0, relative_humidity=50.0, stadium_name="Coors Field", pitch_type="fastball")
        df_sld = calculate_trajectory(player_id=None, temp_f=70.0, wind_speed_mph=0.0, relative_humidity=50.0, stadium_name="Coors Field", pitch_type="slider")
        
        # Fastball should experience upward lift (z coord remains higher than the slider at final step)
        fb_z_final = df_fb.iloc[-1]["z_coord"]
        sld_z_final = df_sld.iloc[-1]["z_coord"]
        self.assertTrue(fb_z_final > sld_z_final)
        
        # Slider should experience lateral horizontal break (x coord drifts to the right)
        fb_x_final = df_fb.iloc[-1]["x_coord"]
        sld_x_final = df_sld.iloc[-1]["x_coord"]
        self.assertTrue(sld_x_final > fb_x_final)

if __name__ == "__main__":
    unittest.main()
