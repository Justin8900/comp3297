#!/usr/bin/env python
"""
Test script for the geocoding functionality.
This script tests the geocode_address function with various Hong Kong addresses.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'COMP3297.settings')
django.setup()

from unihaven.utils.geocoding import geocode_address

def test_geocoding(address):
    """Test the geocoding function with a specific address."""
    print(f"\nTesting address: '{address}'")
    
    lat, lng, geo = geocode_address(address)
    
    if lat is not None and lng is not None and geo is not None:
        print(f"✅ Geocoding successful!")
        print(f"Latitude: {lat}")
        print(f"Longitude: {lng}")
        print(f"Geo Address: {geo}")
        return True
    else:
        print(f"❌ Geocoding failed for address: '{address}'")
        return False

def run_tests():
    """Run geocoding tests with various Hong Kong addresses."""
    test_addresses = [
        "The University of Hong Kong",
        "Chow Yei Ching Building, HKU",
        "Central Plaza, 18 Harbour Road, Wan Chai",
        "Hong Kong Science Park, Pak Shek Kok",
        "IFC Mall, 8 Finance Street, Central",
        "Times Square, Hong Kong",
    ]
    
    success_count = 0
    
    for address in test_addresses:
        if test_geocoding(address):
            success_count += 1
    
    print(f"\nSummary: {success_count}/{len(test_addresses)} addresses successfully geocoded")

if __name__ == "__main__":
    # If an address is provided as a command line argument, test just that address
    if len(sys.argv) > 1:
        address = " ".join(sys.argv[1:])
        test_geocoding(address)
    else:
        # Otherwise run all test cases
        run_tests() 