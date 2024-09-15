import requests
import json
import base64
import os

# Set the base URL for your FastAPI application
BASE_URL = "http://localhost:8000"

# Test data
test_data = {
    "lat": 35.6271473943848,
    "lon": 139.58538125298406,
    "azimuths": [0, 120, 240],
    "num_circles": 4,
    "points_per_circle_base": 8,
    "max_distance": 1500
}

def test_navigation_route_geojson():
    print("Testing /navigation_route_geojson endpoint...")
    response = requests.post(f"{BASE_URL}/navigation_route_geojson", json=test_data)
    
    if response.status_code == 200:
        geojson = response.json()
        print("Success! GeoJSON received.")
        print(f"Number of features: {len(geojson['features'])}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_navigation_route():
    print("\nTesting /navigation_route endpoint...")
    response = requests.post(f"{BASE_URL}/navigation_route", json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print("Success! Response received.")
        print(f"Request ID: {data['request_id']}")
        print(f"Number of features in GeoJSON: {len(data['geojson']['features'])}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_navigation_route_with_plot():
    print("\nTesting /navigation_route_with_plot endpoint...")
    response = requests.post(f"{BASE_URL}/navigation_route_with_plot", json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print("Success! Response received.")
        print(f"Request ID: {data['request_id']}")
        print(f"Number of features in GeoJSON: {len(data['geojson']['features'])}")
        
        if 'plot' in data['geojson']['properties']:
            print("Plot data is present in the response.")
            
            # Save the plot image
            plot_data = data['geojson']['properties']['plot']
            with open("test_route_plot.png", "wb") as f:
                f.write(base64.b64decode(plot_data))
            print("Plot image saved as 'test_route_plot.png'")
        else:
            print("Plot data is not present in the response.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_navigation_route_with_plot_and_kml():
    print("\nTesting /navigation_route_with_plot_and_kml endpoint...")
    response = requests.post(f"{BASE_URL}/navigation_route_with_plot_and_kml", json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print("Success! Response received.")
        print(f"Request ID: {data['request_id']}")
        print(f"Number of features in GeoJSON: {len(data['geojson']['features'])}")
        
        if 'plot' in data['geojson']['properties']:
            print("Plot data is present in the response.")
            
            # Save the plot image
            plot_data = data['geojson']['properties']['plot']
            with open("test_route_plot_with_kml.png", "wb") as f:
                f.write(base64.b64decode(plot_data))
            print("Plot image saved as 'test_route_plot_with_kml.png'")
        else:
            print("Plot data is not present in the response.")
        
        if 'kml_download' in data['geojson']['properties']:
            print("KML download link is present in the response.")
            kml_url = f"{BASE_URL}{data['geojson']['properties']['kml_download']}"
            
            # Download the KML file
            kml_response = requests.get(kml_url)
            if kml_response.status_code == 200:
                with open("test_navigation_route.kml", "wb") as f:
                    f.write(kml_response.content)
                print("KML file downloaded as 'test_navigation_route.kml'")
            else:
                print(f"Error downloading KML file: {kml_response.status_code}")
        else:
            print("KML download link is not present in the response.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_download_file():
    print("\nTesting /download_file endpoint...")
    # First, we need to get a valid filename from a previous request
    response = requests.post(f"{BASE_URL}/navigation_route", json=test_data)
    if response.status_code == 200:
        request_id = response.json()['request_id']
        filename = f"{request_id}_navigation_route.geojson"
        
        # Now test the download
        download_response = requests.get(f"{BASE_URL}/download_file/{filename}")
        if download_response.status_code == 200:
            with open(f"test_downloaded_{filename}", "wb") as f:
                f.write(download_response.content)
            print(f"File successfully downloaded as 'test_downloaded_{filename}'")
        else:
            print(f"Error downloading file: {download_response.status_code}")
            print(download_response.text)
    else:
        print("Error in setup for download_file test")

def test_save_geojson():
    print("\nTesting /save_geojson endpoint...")
    # First, generate a request_id
    request_id = "test_" + requests.post(f"{BASE_URL}/navigation_route", json=test_data).json()['request_id']
    
    # Create a sample GeoJSON
    sample_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [125.6, 10.1]
                },
                "properties": {
                    "name": "Test Point"
                }
            }
        ]
    }
    
    # Test saving the GeoJSON
    response = requests.post(f"{BASE_URL}/save_geojson/{request_id}", json=sample_geojson)
    if response.status_code == 200:
        print("GeoJSON successfully saved.")
        print(response.json())
    else:
        print(f"Error saving GeoJSON: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_navigation_route_geojson()
    test_navigation_route()
    test_navigation_route_with_plot()
    test_navigation_route_with_plot_and_kml()
