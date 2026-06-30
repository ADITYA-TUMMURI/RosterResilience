import unittest
from engine import get_pressure_for_altitude, calculate_air_density, calculate_drag_force

class TestAtmosTrackPhysics(unittest.TestCase):
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
        # Let rho = 1.2, v = 40 (m/s), Cd = 0.3, A = 0.0042
        fd = calculate_drag_force(rho=1.2, velocity_mps=40.0, drag_coeff=0.3, area_m2=0.0042)
        expected = 0.5 * 1.2 * (40.0**2) * 0.3 * 0.0042
        self.assertAlmostEqual(fd, expected, places=5)

if __name__ == "__main__":
    unittest.main()
