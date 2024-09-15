from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import io
import base64
import os
import uuid
from dotenv import load_dotenv
from functions import (
    generate_route_for_cell_site,
    route_to_geojson,
    split_route_into_segments,
    plot_route_with_sectors,
    save_kml,
    save_geojson
)
import logging
logging.basicConfig(level=logging.ERROR)
# Load environment variables
load_dotenv()

# Get dump directory from environment variable
# DUMP_ROUTE_DATA = os.getenv('DUMP_ROUTE_DATA', './dump_route_data')
DUMP_ROUTE_DATA = os.getcwd()

# Ensure the dump directory exists
os.makedirs(DUMP_ROUTE_DATA, exist_ok=True)

app = FastAPI()

class SiteInput(BaseModel):
    lat: float = Field(..., description="Latitude of the cell site")
    lon: float = Field(..., description="Longitude of the cell site")
    azimuths: List[float] = Field(..., description="List of cell azimuths")
    num_circles: int = Field(4, description="Number of circles for point generation")
    points_per_circle_base: int = Field(8, description="Base number of points per circle")
    max_distance: float = Field(1500, description="Maximum distance for point generation")

def generate_request_id():
    return str(uuid.uuid4())

def save_file(content, filename, request_id):
    full_path = os.path.join(DUMP_ROUTE_DATA, f"{request_id}_{filename}")
    with open(full_path, 'wb') as f:
        f.write(content)
    return full_path

@app.post("/navigation_route_geojson")
async def generate_navigation_route_geojson(site_input: SiteInput):
    try:
        route_coords, _, _ = generate_route_for_cell_site(
            site_input.lat,
            site_input.lon,
            site_input.azimuths,
            site_input.num_circles,
            site_input.points_per_circle_base,
            site_input.max_distance
        )
        segments = split_route_into_segments(route_coords)
        geojson_route = route_to_geojson(route_coords, site_input.azimuths, site_input.lat, site_input.lon, segments)
        
        return JSONResponse(content=geojson_route)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.post("/navigation_route")
async def generate_navigation_route(site_input: SiteInput, background_tasks: BackgroundTasks):
    request_id = generate_request_id()
    try:
        route_coords, _, _ = generate_route_for_cell_site(
            site_input.lat,
            site_input.lon,
            site_input.azimuths,
            site_input.num_circles,
            site_input.points_per_circle_base,
            site_input.max_distance
        )
        segments = split_route_into_segments(route_coords)
        geojson_route = route_to_geojson(route_coords, site_input.azimuths, site_input.lat, site_input.lon, segments)
        
        # Save GeoJSON in background using save_geojson function
        geojson_filename = f"{request_id}_navigation_route.geojson"
        geojson_path = os.path.join(DUMP_ROUTE_DATA, geojson_filename)
        background_tasks.add_task(save_geojson, geojson_route, geojson_path)
        
        return JSONResponse(content={"request_id": request_id, "geojson": geojson_route})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/navigation_route_with_plot")
async def generate_navigation_route_with_plot(site_input: SiteInput, background_tasks: BackgroundTasks):
    request_id = generate_request_id()
    try:
        route_coords, G, all_points = generate_route_for_cell_site(
            site_input.lat,
            site_input.lon,
            site_input.azimuths,
            site_input.num_circles,
            site_input.points_per_circle_base,
            site_input.max_distance
        )
        segments = split_route_into_segments(route_coords)
        geojson_route = route_to_geojson(route_coords, site_input.azimuths, site_input.lat, site_input.lon, segments)
        
        # Generate plot
        fig = plot_route_with_sectors(site_input.lat, site_input.lon, route_coords, G, all_points, site_input.azimuths)
        
        # Save plot to a BytesIO object
        img_bytesio = io.BytesIO()
        fig.savefig(img_bytesio, format='png')
        img_bytesio.seek(0)
        plt.close(fig)
        
        # Ensure 'properties' key exists in geojson_route
        if 'properties' not in geojson_route:
            geojson_route['properties'] = {}
        
        # Add plot data to GeoJSON properties
        geojson_route['properties']['plot'] = base64.b64encode(img_bytesio.getvalue()).decode('utf-8')
        
        # Save GeoJSON using save_geojson function
        geojson_filename = f"{request_id}_navigation_route_with_plot.geojson"
        geojson_path = os.path.join(DUMP_ROUTE_DATA, geojson_filename)
        background_tasks.add_task(save_geojson, geojson_route, geojson_path)
        
        # Save plot image
        plot_filename = f"{request_id}_route_plot.png"
        plot_path = os.path.join(DUMP_ROUTE_DATA, plot_filename)
        background_tasks.add_task(save_file, img_bytesio.getvalue(), plot_filename, request_id)
        
        return JSONResponse(content={"request_id": request_id, "geojson": geojson_route})
    except Exception as e:
        logging.error(f"Error in generate_navigation_route_with_plot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/navigation_route_with_plot_and_kml")
async def generate_navigation_route_with_plot_and_kml(site_input: SiteInput, background_tasks: BackgroundTasks):
    request_id = generate_request_id()
    try:
        route_coords, G, all_points = generate_route_for_cell_site(
            site_input.lat,
            site_input.lon,
            site_input.azimuths,
            site_input.num_circles,
            site_input.points_per_circle_base,
            site_input.max_distance
        )
        segments = split_route_into_segments(route_coords)
        geojson_route = route_to_geojson(route_coords, site_input.azimuths, site_input.lat, site_input.lon, segments)
        
        # Generate plot
        fig = plot_route_with_sectors(site_input.lat, site_input.lon, route_coords, G, all_points, site_input.azimuths)
        
        # Save plot to a BytesIO object
        img_bytesio = io.BytesIO()
        fig.savefig(img_bytesio, format='png')
        img_bytesio.seek(0)
        plt.close(fig)
        
        # Ensure 'properties' key exists in geojson_route
        if 'properties' not in geojson_route:
            geojson_route['properties'] = {}
        
        # Add plot data to GeoJSON properties
        geojson_route['properties']['plot'] = base64.b64encode(img_bytesio.getvalue()).decode('utf-8')
        
        # Generate KML
        kml_filename = f"{request_id}_navigation_route.kml"
        kml_path = os.path.join(DUMP_ROUTE_DATA, kml_filename)
        save_kml(route_coords, site_input.azimuths, site_input.lat, site_input.lon, segments, kml_path)
        
        # Add KML download link to GeoJSON properties
        geojson_route['properties']['kml_download'] = f"/download_file/{kml_filename}"
        
        # Save GeoJSON using save_geojson function
        geojson_filename = f"{request_id}_navigation_route_with_plot_and_kml.geojson"
        geojson_path = os.path.join(DUMP_ROUTE_DATA, geojson_filename)
        background_tasks.add_task(save_geojson, geojson_route, geojson_path)
        
        # Save plot image
        plot_filename = f"{request_id}_route_plot_with_kml.png"
        plot_path = os.path.join(DUMP_ROUTE_DATA, plot_filename)
        background_tasks.add_task(save_file, img_bytesio.getvalue(), plot_filename, request_id)
        
        return JSONResponse(content={"request_id": request_id, "geojson": geojson_route})
    except Exception as e:
        logging.error(f"Error in generate_navigation_route_with_plot_and_kml: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/download_file/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(DUMP_ROUTE_DATA, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

@app.post("/save_geojson/{request_id}")
async def save_geojson_file(request_id: str, geojson: dict):
    try:
        filename = f"{request_id}_custom_geojson.geojson"
        file_path = os.path.join(DUMP_ROUTE_DATA, filename)
        save_geojson(geojson, file_path)
        return JSONResponse(content={"message": f"GeoJSON saved as {filename}", "file_path": file_path})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)