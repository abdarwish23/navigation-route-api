import osmnx as ox
import networkx as nx
import numpy as np
import math
import random
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString, box
import logging
import geopandas as gpd
from shapely.ops import nearest_points
import json
import simplekml



# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_road_network(lat, lon, distance):
    """
    Get the road network for the area around the given coordinates.
    """
    G = ox.graph_from_point((lat, lon), dist=distance, network_type='drive_service') #drive_service #drive
    return G

def generate_ripple_points(G, lat, lon, azimuths, num_circles=4, points_per_circle_base=8, max_distance=1500, max_retries=20):
    """
    Generate points in a ripple-like pattern around the cell site, ensuring path connectivity and consistent point count.
    """
    all_points = []
    center_node = ox.nearest_nodes(G, lon, lat)
    
    for circle_idx in range(num_circles):
        radius = max_distance * (circle_idx + 1) / num_circles
        target_points = points_per_circle_base * (circle_idx + 1)
        
        circle_points = []
        retries = 0
        while len(circle_points) < target_points and retries < max_retries:
            angle = random.uniform(0, 360)
            
            # Adjust angle to focus more points in sector directions
            for sector_azimuth in azimuths:
                if abs(angle - sector_azimuth) < 30 or abs(angle - sector_azimuth) > 330:
                    angle = sector_azimuth + random.uniform(-30, 30)
                    break
            
            point = generate_and_validate_point(G, center_node, lat, lon, angle, radius)
            if point:
                if not circle_points or check_path_exists(G, circle_points[-1], point):
                    circle_points.append(point)
                    retries = 0  # Reset retries on successful point addition
                else:
                    retries += 1
            else:
                retries += 1
        
        all_points.extend(circle_points)
        logging.info(f"Circle {circle_idx + 1}: Generated {len(circle_points)} out of {target_points} points")
    
    return all_points

def generate_and_validate_point(G, center_node, lat, lon, angle, distance, max_attempts=10):
    """
    Generate a point and validate that it's reachable by road and suitable for cars.
    """
    for attempt in range(max_attempts):
        new_lat, new_lon = generate_point_at_angle(lat, lon, angle, distance)
        
        # Find the nearest edge on the road network
        nearest_edge = ox.nearest_edges(G, new_lon, new_lat)
        if nearest_edge:
            try:
                u, v, k = nearest_edge
                edge_data = G.get_edge_data(u, v, k)

                # Check if the edge is drivable (filter road types)
                if 'highway' in edge_data:
                    road_type = edge_data['highway']
                    if isinstance(road_type, list):
                        road_type = road_type[0]  # Handle cases where multiple road types exist

                    # Filter for only drivable road types
                    if road_type in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential']:
                        
                        # Get the geometry of the edge (if it exists)
                        edge_geom = edge_data.get('geometry')
                        if edge_geom and isinstance(edge_geom, LineString):
                            # Project the point onto the nearest edge
                            point = Point(new_lon, new_lat)
                            nearest_point = nearest_points(point, edge_geom)[1]
                            new_lon, new_lat = nearest_point.x, nearest_point.y
                        else:
                            # If no geometry, use the midpoint of the edge
                            new_lon = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
                            new_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
                        
                        # Get the nearest node on the road network
                        nearest_node = ox.nearest_nodes(G, new_lon, new_lat)
                        
                        # Ensure the node is reachable from the center node
                        try:
                            nx.shortest_path(G, center_node, nearest_node, weight='length')
                            return (new_lat, new_lon)
                        except nx.NetworkXNoPath:
                            logging.debug(f"Attempt {attempt + 1}: No path to center node")
                            continue
                    else:
                        logging.debug(f"Attempt {attempt + 1}: Nearest edge is not drivable, skipping. Road type: {road_type}")
            except KeyError:
                logging.warning(f"Attempt {attempt + 1}: Unable to access edge data for {nearest_edge}. Skipping this point.")
        else:
            logging.debug(f"Attempt {attempt + 1}: No nearest edge found")
    
    logging.warning(f"Failed to generate valid point after {max_attempts} attempts")
    return None


def generate_point_at_angle(lat, lon, angle, distance):
    """
    Generate a single point at a specific angle and distance from the cell site.
    """
    angle_rad = math.radians(angle)
    dx = distance * math.sin(angle_rad)
    dy = distance * math.cos(angle_rad)
    
    delta_lat = dy / 111111
    delta_lon = dx / (111111 * math.cos(math.radians(lat)))
    
    new_lat = lat + delta_lat
    new_lon = lon + delta_lon
    
    return (new_lat, new_lon)

def check_path_exists(G, point1, point2):
    """
    Check if a path exists between two points on the road network.
    """
    try:
        node1 = ox.nearest_nodes(G, point1[1], point1[0])
        node2 = ox.nearest_nodes(G, point2[1], point2[0])
        
        nx.shortest_path(G, node1, node2, weight='length')
        return True
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return False

def generate_route_for_cell_site(lat, lon, azimuths, num_circles=4, points_per_circle_base=8, max_distance=1500):
    """
    Generate points around a cell site in a ripple pattern and create a validated navigation route.
    """
    if not azimuths:
        raise ValueError("At least one azimuth must be provided")
    
    if len(azimuths) > 6:
        raise ValueError("Maximum of 6 sectors (azimuths) are supported")
    
    # Adjust points_per_circle_base based on the number of sectors
    points_per_circle_base = max(points_per_circle_base, len(azimuths) * 2)
    
    try:
        G = get_road_network(lat, lon, max_distance)
    except Exception as e:
        logging.error(f"Failed to retrieve road network: {str(e)}")
        raise

    all_points = generate_ripple_points(G, lat, lon, azimuths, num_circles, points_per_circle_base, max_distance)
    
    if not all_points:
        logging.warning("No valid points generated. Attempting to find any valid points on the road network.")
        all_points = find_any_valid_points(G, lat, lon, max_distance, 30)  # Try to find at least 30 points
    
    if not all_points:
        raise ValueError("No valid points could be generated. The site might be in an area with very limited road access.")
    
    route_nodes = [ox.nearest_nodes(G, lon, lat)]  # Start with the cell site
    for point_lat, point_lon in all_points:
        nearest_node = ox.nearest_nodes(G, point_lon, point_lat)
        route_nodes.append(nearest_node)
    
    # Add the cell site at the end to complete the loop
    route_nodes.append(route_nodes[0])
    
    route = []
    for start, end in zip(route_nodes[:-1], route_nodes[1:]):
        try:
            path = nx.shortest_path(G, start, end, weight='length')
            route.extend(path)
        except nx.NetworkXNoPath:
            logging.warning(f"No path found between {start} and {end}. Skipping this segment.")
    
    route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
    
    return route_coords, G, all_points

def find_any_valid_points(G, lat, lon, max_distance, num_points):
    """
    Attempt to find any valid points on the road network within the given distance.
    """
    valid_points = []
    center_node = ox.nearest_nodes(G, lon, lat)
    
    for node, data in G.nodes(data=True):
        if len(valid_points) >= num_points:
            break
        
        node_lat, node_lon = data['y'], data['x']
        distance = ox.distance.great_circle_vec(lat, lon, node_lat, node_lon)
        
        if distance <= max_distance:
            try:
                nx.shortest_path(G, center_node, node, weight='length')
                valid_points.append((node_lat, node_lon))
            except nx.NetworkXNoPath:
                continue
    
    logging.info(f"Found {len(valid_points)} valid points on the road network.")
    return valid_points

def plot_route_with_sectors(lat, lon, route_coords, G, all_points, azimuths):
    """
    Plot the route on a map, including sector directions and all generated points.
    """
    try:
        fig, ax = ox.plot_graph(G, show=False, close=False, edge_color='#999999', edge_linewidth=0.5, node_size=0)
        
        # Plot the cell site
        ax.scatter(lon, lat, c='red', s=100, zorder=5, label='Cell Site')
        
        # Plot sector directions
        for azimuth in azimuths:
            end_lat = lat + 0.01 * math.cos(math.radians(azimuth))
            end_lon = lon + 0.01 * math.sin(math.radians(azimuth))
            ax.plot([lon, end_lon], [lat, end_lat], c='green', linewidth=1, zorder=4)
        
        # Plot the generated points
        point_lons, point_lats = zip(*all_points)
        ax.scatter(point_lons, point_lats, c='blue', s=50, zorder=5, label='Generated Points')
        
        # Plot the route
        route_line = LineString([(coord[1], coord[0]) for coord in route_coords])
        ax.plot(*route_line.xy, c='purple', linewidth=2, zorder=4, label='Route')
        
        plt.title(f"Cell Site with {len(azimuths)} Sectors and Navigation Route")
        plt.legend()
        plt.tight_layout()
        # plt.show()
        # return fig
    except Exception as e:
        logging.error(f"Error in plotting: {str(e)}")
        raise
    
    return fig

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing between two points.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    initial_bearing = math.atan2(y, x)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

def get_turn_instruction(prev_bearing, current_bearing):
    """
    Get a turn instruction based on the change in bearing.
    """
    angle = (current_bearing - prev_bearing + 360) % 360
    if angle < 20:
        return "Continue straight"
    elif 20 <= angle < 60:
        return "Turn slight right"
    elif 60 <= angle < 120:
        return "Turn right"
    elif 120 <= angle < 160:
        return "Turn sharp right"
    elif angle >= 160 and angle <= 200:
        return "Make a U-turn"
    elif 200 < angle < 240:
        return "Turn sharp left"
    elif 240 <= angle < 300:
        return "Turn left"
    elif 300 <= angle < 340:
        return "Turn slight left"
    else:
        return "Continue straight"

def split_route_into_segments(route_coords, segment_length=500):
    """
    Split the route into smaller segments with navigation instructions.
    """
    segments = []
    current_segment = [route_coords[0]]
    current_length = 0
    prev_bearing = None

    for i in range(1, len(route_coords)):
        prev_point = route_coords[i-1]
        current_point = route_coords[i]
        
        # Calculate distance between points
        distance = ox.distance.great_circle_vec(prev_point[0], prev_point[1], current_point[0], current_point[1])
        current_length += distance

        current_bearing = calculate_bearing(prev_point[0], prev_point[1], current_point[0], current_point[1])
        
        if current_length >= segment_length or i == len(route_coords) - 1:
            current_segment.append(current_point)
            
            # Generate navigation instruction
            if prev_bearing is not None:
                instruction = get_turn_instruction(prev_bearing, current_bearing)
            else:
                instruction = "Start route"

            segments.append({
                "coordinates": current_segment,
                "length": current_length,
                "instruction": instruction
            })

            current_segment = [current_point]
            current_length = 0

        else:
            current_segment.append(current_point)

        prev_bearing = current_bearing

    return segments

def route_to_geojson(route_coords, azimuths, lat, lon, segments):
    """
    Convert the route coordinates to a GeoJSON FeatureCollection with enhanced properties.
    """
    features = []

    # Add the complete route as a LineString feature
    route_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [(coord[1], coord[0]) for coord in route_coords]
        },
        "properties": {
            "name": "Complete Navigation Route",
            "total_distance": sum(segment['length'] for segment in segments),
            "num_segments": len(segments)
        }
    }
    features.append(route_feature)

    # Add each route segment as a separate feature
    for i, segment in enumerate(segments):
        segment_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [(coord[1], coord[0]) for coord in segment['coordinates']]
            },
            "properties": {
                "name": f"Segment {i+1}",
                "length": segment['length'],
                "instruction": segment['instruction']
            }
        }
        features.append(segment_feature)

    # Add the cell site as a Point feature
    cell_site_feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "name": "Cell Site",
            "azimuths": azimuths
        }
    }
    features.append(cell_site_feature)

    # Create the GeoJSON structure
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson

def save_kml(route_coords, azimuths, lat, lon, segments, filename):
    """
    Save the route as a KML file.
    """
    kml = simplekml.Kml()

    # Add the complete route
    linestring = kml.newlinestring(name="Complete Navigation Route")
    linestring.coords = [(coord[1], coord[0]) for coord in route_coords]
    linestring.style.linestyle.color = simplekml.Color.blue
    linestring.style.linestyle.width = 4

    # Add each route segment
    for i, segment in enumerate(segments):
        seg = kml.newlinestring(name=f"Segment {i+1}")
        seg.coords = [(coord[1], coord[0]) for coord in segment['coordinates']]
        seg.style.linestyle.color = simplekml.Color.red
        seg.style.linestyle.width = 4
        seg.description = f"Length: {segment['length']:.2f} m\nInstruction: {segment['instruction']}"

    # Add the cell site
    point = kml.newpoint(name="Cell Site")
    point.coords = [(lon, lat)]
    point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/target.png'

    # Add sector lines
    for azimuth in azimuths:
        sector = kml.newlinestring(name=f"Sector {azimuth}")
        end_lat = lat + 0.01 * math.cos(math.radians(azimuth))
        end_lon = lon + 0.01 * math.sin(math.radians(azimuth))
        sector.coords = [(lon, lat), (end_lon, end_lat)]
        sector.style.linestyle.color = simplekml.Color.green
        sector.style.linestyle.width = 2

    kml.save(filename)


def save_geojson(geojson, filename):
    """
    Save the GeoJSON to a file.
    """
    with open(filename, 'w') as f:
        json.dump(geojson, f)

        
def main():
    lat, lon = 35.6271473943848, 139.58538125298406
    azimuths = [0, 120, 240]  # Example azimuths for three sectors

    try:
        route_coords, G, all_points = generate_route_for_cell_site(lat, lon, azimuths)
        
        # Split route into segments
        segments = split_route_into_segments(route_coords)
        
        # Convert route to GeoJSON
        geojson_route = route_to_geojson(route_coords, azimuths, lat, lon, segments)
        
        # Save GeoJSON to file
        save_geojson(geojson_route, 'navigation_route.geojson')
        logging.info("GeoJSON route saved to 'navigation_route.geojson'")
        
        # Save KML to file
        save_kml(route_coords, azimuths, lat, lon, segments, 'navigation_route.kml')
        logging.info("KML route saved to 'navigation_route.kml'")
        
        # Plot the route (optional, you can comment this out if not needed)
        plot_route_with_sectors(lat, lon, route_coords, G, all_points, azimuths)
    except ValueError as e:
        logging.error(f"Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()