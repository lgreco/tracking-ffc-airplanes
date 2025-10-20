import requests

def get_airplane_data():
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    data = response.json()
    if data.get("states"):
        # Simplify or clean up the response
        planes = [
            {
                "icao24": p[0],
                "callsign": p[1],
                "origin_country": p[2],
                "longitude": p[5],
                "latitude": p[6],
                "altitude": p[7],
            }
            for p in data["states"] if p[5] and p[6]
        ]
        return planes
    else:
        return []
