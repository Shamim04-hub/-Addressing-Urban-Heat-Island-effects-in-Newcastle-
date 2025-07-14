import osmnx as ox
import folium
from folium.plugins import HeatMap
import requests
import json
import pandas as pd
import time
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from datetime import datetime
import os

# Function to retrieve historical average temperature for a given latitude, longitude, year, and API key
def get_historical_avg_temperature(latitude, longitude, year, api_key):
    """
    Retrieves the average historical temperature for the given year for given coordinates.using the WorldWeatherOnline API.
    Args:
        latitude (float): Latitude of the location.
        longitude (float): Longitude of the location.
        year (str or int): The year for which to fetch historical data.
        api_key (str): API key for WorldWeatherOnline.
    Returns:
        float or None: The average temperature in Celsius, or None if an error occurs.
    
    """
        # URL for the WorldWeatherOnline past weather API
    base_url = "http://api.worldweatheronline.com/premium/v1/past-weather.ashx"
       # Get current date to form the start and end date for the API request (fetches for the specific day in the given year)
    today = datetime.now()
    start_date = f"{year}-{today.month:02d}-{today.day:02d}"
    end_date = start_date # Fetching data for a single day
     
     # Parameters for the API request
    params = {
        "key": api_key,
        "q": f"{latitude},{longitude}", # Coordinates
        "format": "json",# Response format
        "date": start_date,
        "enddate": end_date,
        "tp": 24 # Interval of temperature data (24 means average for the day)
    }
    try:
         # Make the API request
        response = requests.get(base_url, params=params)
        response.raise_for_status()# Raise an exception for bad status codes
        data = response.json() # Parse JSON response
            
            # Check if weather data is present in the response
        if data and 'weather' in data['data']:
             # Extract daily average temperatures
            daily_temps = [float(day['avgtempC']) for day in data['data']['weather']]
            if daily_temps:
                 # Calculate and return the average of daily temperatures
                return sum(daily_temps) / len(daily_temps)
            else:
                   # Print a warning if no temperature data is found for the coordinates and year
                print(f"Warning: No historical temperature data for {latitude}, {longitude} in {year}.")
                return None
        else:
             # Print a warning if temperature data could not be retrieved
            print(f"Warning: Could not retrieve historical temperature data for {latitude}, {longitude}.")
            return None
    except requests.exceptions.RequestException as e:

        # Handle request-related errors (e.g., network issues)
        print(f"Error fetching historical temperature for {latitude}, {longitude}: {e}")
        return None
    except (KeyError, ValueError) as e:
       
         # Handle errors in parsing the response data
        print(f"Error parsing historical temperature response for {latitude}, {longitude}: {e}")
        return None

# Function to create heatmaps based on historical temperature data for a specified place and polygon
def create_heatmap(place, polygon_coords, api_keys, api_limit_per_key, output_dir="heatmaps"):
    """
    Creates heatmaps for specified years within a given polygon for a place.
    Fetches historical temperature data for nodes within the polygon and generates
    CSV files, JSON files, Folium heatmaps, and HTML files for displaying Google Maps heatmaps.
    Args:
        place (str): The name of the place (e.g., "Newcastle upon Tyne, UK").
        polygon_coords (list of tuples): Coordinates defining the polygon [(lat, lon), ...].
        api_keys (dict): A dictionary mapping years (str/int) to API keys (str).
        api_limit_per_key (int): Maximum number of API requests to make per key/year.
        output_dir (str): The directory to save output files.
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
   
     # Create a Shapely Polygon object from the provided coordinates
    polygon = Polygon([(lon, lat) for lat, lon in polygon_coords])
    G = ox.graph_from_place(place, network_type="drive")
    nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
    num_nodes = len(nodes)
    print(f"Total number of nodes: {num_nodes}")
  
    # Filter nodes to include only those within the specified polygon
    nodes_within_polygon = []
    for _, node in nodes.iterrows():
        point = Point(node['x'], node['y'])
        if polygon.contains(point):
            nodes_within_polygon.append(node)
   
    # Create a DataFrame from the filtered nodes
    nodes_filtered = pd.DataFrame(nodes_within_polygon)
    num_nodes_in_polygon = len(nodes_filtered)
    print(f"Number of nodes within the polygon: {num_nodes_in_polygon}")

   # Sample nodes if the number of nodes within the polygon exceeds the API limit per key
    sampled_nodes = pd.DataFrame()
    if num_nodes_in_polygon > 0:
        if num_nodes_in_polygon > api_limit_per_key:
            sampled_nodes = nodes_filtered.sample(n=api_limit_per_key, random_state=42)
            print(f"Sampling {api_limit_per_key} nodes within the polygon due to API limit per key.")
        else:
            sampled_nodes = nodes_filtered
            print("Number of nodes within the polygon is within API limit.")
    else:
        print("No nodes found within the specified polygon. Skipping temperature data collection and heatmap generation.")
        return

       # List to store all temperature data collected across all years
    all_temp_data = []
     # Iterate over each year and its corresponding API key
    for year, key in api_keys.items():
        heat_data_historical = [] # List to store heatmap data for the current year
        requests_made = 0  # Counter for API requests made for the current key/year
        print(f"\n--- Collecting data for year: {year} ---")
       
       # Proceed only if there are sampled nodes 
        if not sampled_nodes.empty:
             # Iterate over each sampled node to get its historical temperature
            for index, node in sampled_nodes.iterrows():
                if requests_made < api_limit_per_key:
                    # Get the average historical temperature for the node's coordinates and current year
                    avg_temp = get_historical_avg_temperature(node['y'], node['x'], year, key)
                    if avg_temp is not None:
                         # Append data for Folium heatmap
                        heat_data_historical.append([node['y'], node['x'], avg_temp])
                        all_temp_data.append({
                              # Append data for CSV/JSON logging
                            'latitude': node['y'],
                            'longitude': node['x'],
                            'avg_temperature': avg_temp,
                            'year': year,
                            'api_key_used': key[-8:] # Log last 8 chars of API key for reference
                        })
                    requests_made += 1
                    time.sleep(0.3)  #  Pause to be respectful to the API server
                else:
                     # Stop data collection for the current year if API limit is reached
                    print(f"API limit reached for year {year} (key ending in: {key[-8:]}). Stopping data collection for this year.")
                    break
                 # Save the collected temperature data for the current year to a CSV file
            csv_filename = os.path.join(output_dir, f"newcastle_{year}_avg_temperature_within_polygon_sampled.csv")
            df_historical = pd.DataFrame(all_temp_data)
            df_historical_year = df_historical[df_historical['year'] == year]
            df_historical_year.to_csv(csv_filename, index=False)
            print(f"Average temperature data for {year} saved as {csv_filename}")

            # Create JSON file per year
            json_filename = os.path.join(output_dir, f"heatmap_data_{year}.json")
             # Select relevant columns and convert to dictionary format
            year_json = df_historical_year[['latitude', 'longitude', 'avg_temperature', 'year']].to_dict(orient='records')
            with open(json_filename, 'w') as f:
                json.dump(year_json, f, indent=2)
            print(f"JSON data for {year} saved to {json_filename}")

            # Generate and save a Folium heatmap if data was collected for the current year
            if heat_data_historical:
                  # Create a Folium map centered around the mean coordinates of sampled nodes
                m_historical = folium.Map(location=[sampled_nodes['y'].mean(), sampled_nodes['x'].mean()], zoom_start=12,
                                        tiles="Satellite", attr="Map data © contributors")
                 # Add a HeatMap layer to the Folium map
                HeatMap(heat_data_historical, radius=12, blur=10, min_opacity=0.5).add_to(m_historical)
                
                # Save the Folium heatmap as an HTML file
                map_filename_historical = os.path.join(output_dir, f"newcastle_{year}_avg_temperature_heatmap_within_polygon_sampled.html")
                m_historical.save(map_filename_historical)
                print(f"Average temperature heatmap for {year} saved as {map_filename_historical} using key ending in: {key[-8:]}")
            else:
                print(f"No average temperature data was collected for {year} within the polygon (key ending in: {key[-8:]}), so the heatmap was not created.")
        else:
            print("No nodes within the specified polygon to sample or get historical average temperature data for.")
    
     # After processing all years, save all collected temperature data to a single CSV file
    all_temp_df = pd.DataFrame(all_temp_data)
    all_temp_csv_filename = os.path.join(output_dir, "newcastle_all_years_avg_temperature_within_polygon_sampled.csv")
    all_temp_df.to_csv(all_temp_csv_filename, index=False)
    print(f"\nAll years' average temperature data saved to: {all_temp_csv_filename}")

    # Create the final combined JSON file.
    json_filename = os.path.join(output_dir, "heatmap_data_all_years.json")
    all_years_json = all_temp_df[['latitude', 'longitude', 'avg_temperature', 'year']].to_dict(orient='records')  # create json
    with open(json_filename, 'w') as f:
        json.dump(all_years_json, f, indent=2)
    print(f"Combined data for all years saved to {json_filename}")

    # HTML for displaying the map (moved inside the if __name__ block)
    # This HTML structure includes JavaScript to initialize Google Maps and load heatmap data from the year-specific JSON file
    for year in api_keys.keys():
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google Maps Heatmap - {year}</title>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                }}
                #map {{
                    height: 100%;
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                let map;
                let heatmap;

                function initMap() {{
                    map = new google.maps.Map(document.getElementById('map'), {{
                        center: {{ lat: 54.977, lng: -1.618 }},  //  Newcastle upon Tyne
                        zoom: 12
                    }});

                    // Fetch heatmap data
                    fetch('heatmap_data_{year}.json')
                        .then(response => {{
                            if (!response.ok) {{
                                throw new Error(`HTTP error! status: ${"""response.status"""}`);
                            }}
                            return response.json();
                        }})
                        .then(data => {{
                            let heatmapData = data.map(item => {{
                                return {{
                                    location: new google.maps.LatLng(item.latitude, item.longitude),
                                    weight: item.avg_temperature  //  Use the correct key for your data
                                }};
                            }});

                            heatmap = new google.maps.visualization.HeatmapLayer({{
                                data: heatmapData,
                                map: map,
                                radius: 15,
                                opacity: 0.7
                            }});
                        }})
                        .catch(error => {{
                            console.error('Error fetching heatmap data:', error);
                            // Display a user-friendly message on the page
                            const mapElement = document.getElementById('map');
                            mapElement.innerHTML = `<div style="color: red; padding: 10px; border: 1px solid red;">
                                <strong>Error:</strong> Could not load heatmap data.  Please check:
                                <ul>
                                    <li>1. Is the 'heatmap_data_{year}.json' file in the same directory as the HTML file?</li>
                                    <li>2. Is the 'heatmap_data_{year}.json' file correctly formatted?</li>
                                    </ul>
                                <p>Error details: ${"""error.message"""}</p>
                            </div>`;
                        }});
                }}
            </script>
            <script async defer
                    src="https://maps.googleapis.com/maps/api/js?key=[YOUR API KEY]&callback=initMap&libraries=visualization"></script>
        </body>
        </html>
        """
        # Write the HTML content to a file
        html_file_path = os.path.join(output_dir, f"heatmap_{year}.html")
        with open(html_file_path, "w") as html_file:
            html_file.write(html_content)
        print(f"HTML file created: {html_file_path}")

    print("\nCompleted data collection, CSV saving, JSON saving, and heatmap generation for each year.")

if __name__ == "__main__":
        # Define the place for which to generate heatmaps
    place = "Newcastle upon Tyne, UK"
    polygon_coords = [
        # Define the coordinates of the polygon to filter data
        (55.05, -1.75),
        (55.00, -1.60),
        (54.95, -1.65),
        (54.98, -1.78)
    ]
    api_keys = {
        # Dictionary of API keys, with years as keys
        "2025": "[YOUR API KEY]",
        "2024": "[YOUR API KEY]",
        "2023": "[YOUR API KEY]",
        "2022": "[YOUR API KEY]",
        "2021": "[YOUR API KEY]"
    }
     # Limit for API requests per key (to avoid exceeding usage quotas)
    api_limit_per_key = 1
    output_directory = "heatmaps"  #  creates directory for heatmap.

 # Call the main function to create heatmaps
    create_heatmap(place, polygon_coords, api_keys, api_limit_per_key, output_directory)
