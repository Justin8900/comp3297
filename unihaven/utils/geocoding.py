import requests
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

def geocode_address(address):
    """
    Convert a Hong Kong address to coordinates using DATA.GOV.HK's ALS API.
    
    Args:
        address (str): Human-readable address (e.g., "Chow Yei Ching Building")
        
    Returns:
        tuple: (latitude, longitude, geo_address) or (None, None, None) if failed
    """
    try:
        # 1. Prepare API request
        encoded_address = quote(address)
        url = f"https://www.als.gov.hk/lookup?q={encoded_address}&n=1"
        headers = {'Accept': 'application/json'}
        
        # 2. Make API call
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad status codes
        
        data = response.json()
        
        # 3. Extract geocoding data
        suggested_address = data.get('SuggestedAddress', [{}])[0]
        premises = suggested_address.get('Address', {}).get('PremisesAddress', {})
        geo_info = premises.get('GeospatialInformation', {})
        
        latitude = geo_info.get('Latitude')
        longitude = geo_info.get('Longitude')
        geo_address = premises.get('GeoAddress')
        
        # Validate all required fields exist
        if latitude and longitude and geo_address:
            return (
                float(latitude), 
                float(longitude), 
                geo_address
            )
            
        logger.warning(f"Incomplete ALS response for address: {address}")
        return None, None, None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"ALS API request failed: {str(e)}")
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Failed to parse ALS response: {str(e)}")
        
    return None, None, None