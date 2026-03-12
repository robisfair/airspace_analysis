# Ensure you have the 'requests' library installed:
# pip install requests
import requests

def query_airport_bbox(airport_icao: str) -> dict:
    query = f"""
    [out:json];
    (
    way["aeroway"="aerodrome"]["icao"="{airport_icao}"];
    rel["aeroway"="aerodrome"]["icao"="{airport_icao}"];
    );
    out bb;
    """
    response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
    data = response.json()

    if data['elements']:
        element = data['elements'][0]
        bbox = {
            'minlat': element['bounds']['minlat'],
            'minlon': element['bounds']['minlon'],
            'maxlat': element['bounds']['maxlat'],
            'maxlon': element['bounds']['maxlon']
        }
        return bbox
    else:
        raise ValueError(f"No aerodrome found with ICAO code {airport_icao}")

def main():
    airport_icao = input("Enter an airport ICAO code (e.g., KJFK): ").strip().upper()
    try:
        bbox = query_airport_bbox(airport_icao)
        print(f"Bounding box for {airport_icao}:\nlamin: {bbox['' \
        'minlat']},\nlamax: {bbox['' \
        'maxlat']},\nlomin: {bbox['' \
        'minlon']},\nlomax: {bbox['' \
        'maxlon']}")
    except ValueError as e:
        print(e)


if __name__ == "__main__":
    main()