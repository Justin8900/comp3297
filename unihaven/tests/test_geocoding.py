import unittest
import math
from unittest.mock import patch
from unihaven.utils.geocoding import calculate_distance

class TestGeocodingDistance(unittest.TestCase):
    """Test cases for the distance calculation function in geocoding module."""
    
    def test_calculate_distance(self):
        """Test the calculate_distance function with known coordinates."""
        # Test case 1: Same point (should return 0)
        # Expected: 0.0 km
        distance = calculate_distance(22.28, 114.15, 22.28, 114.15)
        self.assertAlmostEqual(distance, 0.0, delta=0.001)
    
        # Test case 2: Known distance between two Hong Kong locations
        # HKU (22.2831, 114.1372) to HKUST (22.3363, 114.2634)
        # Expected: ~14.1 km using Equirectangular approximation
        distance = calculate_distance(22.2831, 114.1372, 22.3363, 114.2634)
        self.assertAlmostEqual(distance, 14.1, delta=0.5)
        
        # Test case 3: Distance across a longitude line
        # Expected: ~10.3 km using Equirectangular approximation
        distance = calculate_distance(22.28, 114.15, 22.28, 114.25)
        self.assertAlmostEqual(distance, 10.3, delta=0.1)
        
        # Test case 4: Distance across a latitude line
        # Expected: ~11.1 km using Equirectangular approximation
        distance = calculate_distance(22.28, 114.15, 22.38, 114.15)
        self.assertAlmostEqual(distance, 11.1, delta=0.1)