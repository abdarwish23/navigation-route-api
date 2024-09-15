# Navigation Route Generation API

This FastAPI application provides endpoints for generating navigation routes, including options for GeoJSON output, plot generation, and KML file creation.

## Table of Contents

1. [Installation](#installation)
2. [Setup](#setup)
3. [Running the Application](#running-the-application)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Testing](#testing)
7. [Contributing](#contributing)
8. [License](#license)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/abdarwish23/navigation-route-api.git
   cd navigation-route-api
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Setup

1. Create a `.env` file in the root directory with the following content:
   ```
   DUMP_ROUTE_DATA=/path/to/your/dump_route_data
   ```
   Replace `/path/to/your/dump_route_data` with the actual path where you want to store generated files.

2. Ensure the `DUMP_ROUTE_DATA` directory exists:
   ```
   mkdir -p /path/to/your/dump_route_data
   ```

## Running the Application

Start the FastAPI server:

```
uvicorn app:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

- `/navigation_route_geojson`: Generate a GeoJSON navigation route in the response only
- `/navigation_route`: Generate a navigation route and save it (dump the geojson file into the path in .env file)
- `/navigation_route_with_plot`: Generate a route with a plot (dump the geojson file and plot into the path in .env file)
- `/navigation_route_with_plot_and_kml`: Generate a route with a plot and KML file (dump the geojson file and plot and kml files into the path in .env file)
- `/download_file/{filename}`: Download a generated file 
- `/save_geojson/{request_id}`: Save a custom GeoJSON file

## Usage Examples

Here are curl commands to test each endpoint:

### Generate GeoJSON Route

```bash
curl -X POST "http://localhost:8000/navigation_route_geojson" \
     -H "Content-Type: application/json" \
     -d '{
           "lat": 35.6271473943848,
           "lon": 139.58538125298406,
           "azimuths": [0, 120, 240],
           "num_circles": 4,
           "points_per_circle_base": 8,
           "max_distance": 1500
         }' \
     -o navigation_route_geojson.json
```

### Generate and Save Route

```bash
curl -X POST "http://localhost:8000/navigation_route" \
     -H "Content-Type: application/json" \
     -d '{
           "lat": 35.6271473943848,
           "lon": 139.58538125298406,
           "azimuths": [0, 120, 240],
           "num_circles": 4,
           "points_per_circle_base": 8,
           "max_distance": 1500
         }' \
     -o navigation_route.json
```

### Generate Route with Plot

```bash
curl -X POST "http://localhost:8000/navigation_route_with_plot" \
     -H "Content-Type: application/json" \
     -d '{
           "lat": 35.6271473943848,
           "lon": 139.58538125298406,
           "azimuths": [0, 120, 240],
           "num_circles": 4,
           "points_per_circle_base": 8,
           "max_distance": 1500
         }' | tee navigation_route_with_plot.json | jq -r '.geojson.properties.plot' | base64 -d > route_plot.png
```

### Generate Route with Plot and KML

```bash
curl -X POST "http://localhost:8000/navigation_route_with_plot_and_kml" \
     -H "Content-Type: application/json" \
     -d '{
           "lat": 35.6271473943848,
           "lon": 139.58538125298406,
           "azimuths": [0, 120, 240],
           "num_circles": 4,
           "points_per_circle_base": 8,
           "max_distance": 1500
         }' | tee navigation_route_with_plot_and_kml.json | jq -r '.geojson.properties.plot' | base64 -d > route_plot_with_kml.png

# Download the KML file
KML_FILENAME=$(jq -r '.geojson.properties.kml_download' navigation_route_with_plot_and_kml.json | sed 's/^\/download_file\///')
curl -X GET "http://localhost:8000/download_file/${KML_FILENAME}" \
     -o downloaded_navigation_route.kml
```

### Save Custom GeoJSON

```bash
REQUEST_ID=$(jq -r '.request_id' navigation_route.json)
curl -X POST "http://localhost:8000/save_geojson/${REQUEST_ID}" \
     -H "Content-Type: application/json" \
     -d @navigation_route_geojson.json \
     -o save_geojson_response.json
```

## Testing

To run the test script:

1. Ensure your FastAPI application is running.
2. Run the test script:
   ```
   python test_api.py
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
