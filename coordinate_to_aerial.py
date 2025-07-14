import os
import sys
import time
import requests
import yaml  

# Function to download a static map image from Google Static Maps API
def download_static_map_image(api_key, location, filename, zoom=18, maptype='satellite', size='600x300', markers_list=None, path=None):
    """Downloads a static map image with optional markers and path.
     Args:
        api_key (str): The Google Cloud API key.
        location (str): The center of the map (address string or "latitude,longitude").
        filename (str): The path and name of the file to save the image to.
        zoom (int, optional): Zoom level of the map. Defaults to 18.
        maptype (str, optional): Type of map (e.g., 'satellite', 'roadmap'). Defaults to 'satellite'.
        size (str, optional): Dimensions of the image in pixels (e.g., '600x300'). Defaults to '600x300'.
        markers_list (list, optional): A list of marker strings (e.g., ["color:blue|label:S|40.702147,-74.015794"]). Defaults to None.
        path (str, optional): A path string (e.g., "color:0x0000ff|weight:5|40.737102,-73.990318|40.749825,-73.987963"). Defaults to None.
    Returns:
        bool: True if download was successful, False otherwise."""
      # Base URL for the Google Static Maps API
    url = "https://maps.googleapis.com/maps/api/staticmap"
     # Parameters for the API request
    params = {
        'center': location,
        'zoom': zoom,
        'size': size,
        'maptype': maptype,
        'key': api_key  
    }
    # Add markers to parameters if provided
    if markers_list:
        params['markers'] = markers_list

    if path:
        params['path'] = path
 
      # Make the HTTP GET request to the API
    try:
        response = requests.get(url, params=params, stream=True)
        response.raise_for_status()# Raise an HTTPError for bad responses

      # Write the image content to the specified file
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Static map image downloaded successfully: {filename}")
        return True

    except requests.exceptions.RequestException as e:
         # Handle errors during the API request
        print(f"Error downloading static map image: {e}")
        print("Response Content:", response.text)
        return False
    
    # Main part of the script starts here
try:
     # Attempt to open and load configuration from 'config.yaml'
    with open("config.yaml", 'r') as config_yaml_file:
        config = yaml.safe_load(config_yaml_file)
        # Get API key and output directory from the config
        api_key = config.get('api_key')
        output_dir = config.get('satellite_output_directory') # Directory to save satellite images

 # Check if API key or output directory is missing in the config
        if not api_key or not output_dir:
            raise ValueError("API key or output_directory not found in config.yaml")

except FileNotFoundError:
      # Handle case where config.yaml is not found
    print("Error: config.yaml file not found. Make sure it exists in the same directory as the script.")
    sys.exit(1) # Exit the script
except yaml.YAMLError as e: 
    # Handle errors during YAML parsing
    print(f"Error parsing config.yaml: {e}")
except ValueError as e:
     # Handle specific ValueError raised above for missing config keys
    print(f"Configuration Error in config.yaml: {e}")
    sys.exit(1)

# Create the output directory for satellite images 
try:
    # Attempt to open and load coordinates from 'coordinates.yaml'
    with open("coordinates.yaml", 'r') as coordinates_yaml_file:
        coordinates_config = yaml.safe_load(coordinates_yaml_file)
     # Check if the coordinates file is empty or malformed
        if not coordinates_config:
            raise ValueError("No data found in coordinates.yaml")

        for aim, details in coordinates_config.items():
             # Get latitude and longitude for the current item
            latitude = details.get('latitude')
            longitude = details.get('longitude')
           
            # If latitude or longitude is missing for an item, skip it
            if not latitude or not longitude:
                print(f"Skipping {aim}: Latitude or longitude not found.")
                continue
            # Format the location string for the API request
            location = f"{latitude},{longitude}"
            # Create a filename for the satellite image 
            filename = os.path.join(output_dir, f"{aim.replace(' ', '_').replace(':', '')}.jpg")

            print(f"Downloading satellite image for {aim}...")
             # Call the function to download the static map image
            success = download_static_map_image(
                api_key=api_key,
                location=location,
                filename=filename,
                zoom=19, # Higher zoom level for more detail
                maptype="satellite",# Request a satellite map
                size='600x600' # Specify image size
            )
             # Print status based on whether the download was successful
            if success:
                print(f"Image for {aim} saved as {filename}")
            else:
                print(f"Failed to download image for {aim}")

except FileNotFoundError:
     # Handle case where coordinates.yaml is not found
    print("Error: coordinates.yaml file not found. Make sure it exists in the same directory as the script.")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Error parsing coordinates.yaml: {e}")
    sys.exit(1)
except ValueError as e:
     # Handle specific ValueError raised for issues in coordinates.yaml content
    print(f"Configuration Error in coordinates.yaml: {e}")
    sys.exit(1)