import requests
import os
import yaml
from PIL import Image
import io

# Define the path for the configuration file (e.g., for API keys)
CONFIG_FILE_PATH = "config.yaml"
COORDINATES_FILE_PATH = "coordinates.yaml"

# Define constants for the Street View API request
FOV = 60
PITCH = 0
SIZE = "600x400"


def get_coordinates_from_yaml(
    yaml_file_path="coordinates.yaml",
):  # Function for getting the coordinate
    """
    Extracts latitude and longitude from a YAML file.Args:
        yaml_file_path (str): The path to the YAML file containing coordinates.
    Returns:
        tuple: A tuple containing latitude (float) and longitude (float).
               Returns (None, None) if an error occurs or data is not found.

    """
    # Attempt to open and read the YAML file
    try:
        with open(yaml_file_path, "r") as file:
            coordinates_data = yaml.safe_load(file)
    except FileNotFoundError:

        # Handle the case where the YAML file does not exist
        print(f"Error: YAML file '{yaml_file_path}' not found.")
        return None, None
    except yaml.YAMLError as e:

        # Handle errors during YAML parsing
        print(f"Error parsing YAML file '{yaml_file_path}': {e}")
        return None, None

        # Check if the loaded data is valid
    if coordinates_data and "Aim 1" in coordinates_data:
        aim_1_data = coordinates_data["Aim 1"]
        latitude_str = aim_1_data.get("latitude")
        longitude_str = aim_1_data.get("longitude")

        try:
            # Convert latitude and longitude strings to float, if they exist
            latitude = float(latitude_str) if latitude_str is not None else None
            longitude = float(longitude_str) if longitude_str is not None else None
            return latitude, longitude
        except (ValueError, TypeError):
            # Handle errors if latitude or longitude values are not valid numbers
            print(f"Error: Invalid latitude or longitude values in '{yaml_file_path}'.")
            return None, None
    else:
        # Handle the case where 'Aim 1' or coordinate data is missing in the YAML file
        print(
            f"Error: 'Aim 1' section or coordinate data not found in '{yaml_file_path}'."
        )
        return None, None


def get_street_view_image(
    location_str, heading, api_key, output_dir, filename
):  # Getting street view image
    """Downloads a Street View image.
     Downloads a Google Street View image for a given location and heading.
    Args:
        location_str (str): The location as a "latitude,longitude" string.
        heading (int): The camera heading (0-359 degrees).
        api_key (str): The Google Street View API key.
        output_dir (str): The directory to save the downloaded image.
        filename (str): The name for the saved image file.
    Returns:
        str: The path to the saved image, or None if an error occurred."""
    url = f"https://maps.googleapis.com/maps/api/streetview?size={SIZE}&location={location_str}&fov={FOV}&heading={heading}&pitch={PITCH}&key={api_key}"

    try:
        # Make the HTTP GET request to the API
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Open the image from the response content and save it
        image = Image.open(io.BytesIO(response.content))
        image_path = os.path.join(output_dir, filename)
        image.save(image_path)
        print(f"Image saved to: {image_path}")
        return image_path

    except requests.exceptions.RequestException as e:
        # Handle errors during the API request (e.g., network issues, invalid API key)
        print(f"Error downloading image: {e}")
        return None
    except Exception as e:
        # Handle other potential errors during image processing
        print(f"Error processing image: {e}")
        return None


def create_panorama(
    image_paths, output_dir
):  # we create the panaorama images from those 6 images
    """Creates a panorama image from the downloaded images.
     Creates a panoramic image by stitching together a list of images horizontally.
    Args:
        image_paths (list): A list of file paths to the images to be stitched.
        output_dir (str): The directory to save the resulting panorama image."""

    # Check if there are any image paths provided
    if not image_paths:
        return

    try:
        # Open all images specified in image_paths, skipping any None values
        images = [Image.open(path) for path in image_paths if path]

        # Assuming all images have the same height, get the height from the first image
        height = images[0].height
        widths = [img.width for img in images]
        total_width = sum(widths)

        height = images[0].height
        panorama = Image.new("RGB", (total_width, height))

        # Paste each image onto the panorama side-by-side
        x_offset = 0
        for img in images:
            panorama.paste(img, (x_offset, 0))
            x_offset += img.width

        # Define the path for the panorama image and save it
        panorama_path = os.path.join(output_dir, "panorama.jpg")
        panorama.save(panorama_path)
        print(f"Panorama saved to: {panorama_path}")

    except Exception as e:
        # Handle any errors that occur during panorama creation
        print(f"Error creating panorama: {e}")

    # Main execution block: This code runs when the script is executed directly


if __name__ == "__main__":

    # Load the API key from the configuration file
    try:
        with open(CONFIG_FILE_PATH, "r") as config_file:
            config = yaml.safe_load(config_file)
            api_key = config.get("api_key")
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE_PATH}' not found.")
        api_key = None
    # Check if API key was successfully loaded
    if not api_key:
        print("Error: API key not found in configuration file.")
        exit()

    # Get coordinates (latitude and longitude) from the YAML file
    lat, lng = get_coordinates_from_yaml(COORDINATES_FILE_PATH)
    # Check if coordinates were successfully loaded
    if not lat or not lng:
        print("Error: Could not load coordinates from coordinates.yaml. Exiting.")
        exit()  # Exit the script if coordinates are not found

    # Ask the user if they want to input specific coordinates or use the ones from the YAML file
    use_specific_coordinates = input(
        "Do you want to enter specific coordinates instead of using you Given Location (yes/no): "
    ).lower()

    # If the user chooses to enter specific coordinates
    if use_specific_coordinates == "yes" or use_specific_coordinates == "y":
        while True:
            try:
                # Prompt user for latitude and longitude
                lat_input = input("Enter Latitude: ")
                lat = float(lat_input)
                lng_input = input("Enter Longitude: ")
                lng = float(lng_input)
                break
            except ValueError:
                # Handle invalid (non-numeric) input
                print(
                    "Invalid input. Please enter numeric values for latitude and longitude."
                )

    # Format the location string using the determined latitude and longitude
    LOCATION = f"{lat},{lng}"
    # Define the output directory path based on the location
    OUTPUT_DIR = os.path.join("data", f"coordinate_{LOCATION}_images")

    # Create the output directory if it doesn't already exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    # List to store paths of downloaded images for panorama creation
    image_paths = []
    # Loop 6 times to get images from different headings (0, 60, 120, 180, 240, 300 degrees)
    for i in range(6):
        heading = i * FOV
        filename = f"street_view_{i}.jpg"
        # Download the Street View image
        image_path = get_street_view_image(
            LOCATION, heading, api_key, OUTPUT_DIR, filename
        )
        image_paths.append(image_path)

    # create_panorama(image_paths, OUTPUT_DIR)
