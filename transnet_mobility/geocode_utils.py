import requests

def get_location_name(latitude, longitude, provider='osm'):
    """
    Convert latitude and longitude to a human-readable location name using OpenStreetMap Nominatim API.
    Returns a string with the area/city/country or 'Unknown location' if not found.
    """
    try:
        url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=10&addressdetails=1'
        headers = {'User-Agent': 'TransnetMobilityApp/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            # Try to get a meaningful area name
            for key in ['city', 'town', 'village', 'county', 'state', 'region', 'country']:
                if key in address:
                    return address[key]
            return data.get('display_name', 'Unknown location')
        else:
            return 'Unknown location'
    except Exception:
        return 'Unknown location'
