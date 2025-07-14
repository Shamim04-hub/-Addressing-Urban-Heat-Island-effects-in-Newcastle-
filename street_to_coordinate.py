import requests  # For making HTTP requests to the Google Geocoding API
import json  # For working with JSON data (though response.json() handles parsing)
import yaml  # For reading the API key from a YAML config file and saving coordinates

# Define the path to the configuration file that holds the API key
CONFIG_FILE_PATH = "config.yaml"

#api_key = "AIzaSyCARAbHz2Mr3gl5-nN0apQNN_pyYYcgk6w"

try:
    # Attempt to open and read the configuration file
    with open(CONFIG_FILE_PATH,
              'r') as config_file:  # Acccess the api key from config.yaml
        # Load the YAML content from the file
        config = yaml.safe_load(config_file)
        # Retrieve the API key from the loaded configuration dictionary
        api_key = config.get('api_key')

except FileNotFoundError:
    # Handle the case where the configuration file is not found
    print(f"Error: Configuration file '{CONFIG_FILE_PATH}' not found.")
    # Set api_key to None because it could not be loaded from the file.
    api_key = None
    # Terminate the script execution because the API key is essential for proceeding.
    exit()

# This 'if' statement checks if the api_key is still None or an empty string.
# This would be true if the FileNotFoundError occurred or if 'api_key' was missing or empty in the config file.
if not api_key:
    # Print an error message indicating the API key is missing or was not loaded
    print("Error: API key not found in configuration file.")
    # Terminate the script execution.
    exit()


# Define a function to get geographic coordinates (latitude and longitude) for a given address.
def get_coordinates(address, api_key):  # Function for getting API coordinates
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    # Make an HTTP GET request to the constructed URL.
    response = requests.get(url)
    # Parse the JSON response received from the API into a Python dictionary.
    data = response.json()  # Data retrieve in data variable

    # Check if the API request status is "OK", indicating success.
    if data["status"] == "OK":  # Get  the lat and lng from that data variable
        # Extract the latitude from the first result in the API response.
        latitude = data["results"][0]["geometry"]["location"]["lat"]
        # Extract the longitude from the first result in the API response.
        longitude = data["results"][0]["geometry"]["location"]["lng"]
        # Return the extracted latitude and longitude.
        return latitude, longitude
    else:
        # If the API request status is not "OK", print the error status provided by the API.
        print(f"Error: {data['status']}")
        # Return None for both latitude and longitude to indicate that coordinates could not be retrieved.
        return None, None


# Prompt the user to enter an address.
# The example format guides the user on how to structure the address input.
address = input("Enter address like (Ouseburn Road,Newcastle upon Tyne,UK)"
                )  # input the address

# Call the get_coordinates function with the user-provided address and the loaded API key.
# Store the returned latitude and longitude in variables 'lat' and 'lng'.
lat, lng = get_coordinates(address, api_key)  # call the function

# Check if both latitude ('lat') and longitude ('lng') were successfully retrieved
if lat and lng:  # record that coordinates in yaml file
    # Print the retrieved latitude and longitude to the console
    print(f"Latitude: {lat}, Longitude: {lng}")

    # Define the filename for the YAML file where the coordinates will be saved.
    COORDINATES_FILE_PATH = "coordinates.yaml"

    # Create a dictionary structure for storing the coordinates data.
    coordinates_data = {
        'Aim 1': {
            'address': address,
            'latitude': lat,
            'longitude': lng
        }
    }

    try:
        # Attempt to open the specified YAML file in write mode ('w').
        # This will create the file if it doesn't exist, or overwrite it if it does.
        with open(COORDINATES_FILE_PATH, 'w') as coordinates_file:
            yaml.dump(coordinates_data, coordinates_file)
            # Print a confirmation message indicating that the coordinates have been saved and where.
        print(f"Coordinates saved to '{COORDINATES_FILE_PATH}'")

    except Exception as e:
        # If any error occurs during the file writing process (e.g., permission issues),
        print(f"Error saving coordinates to '{COORDINATES_FILE_PATH}': {e}")

else:
    # meaning the get_coordinates function failed to retrieve them.
    print("Could not retrieve coordinates for the given address.")