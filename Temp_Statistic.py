import requests
import pandas as pd
import numpy as np
import folium
from folium import plugins
import yaml
import os
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns


# Loads configuration settings from a YAML file. Args:
#  config_path (str): The path to the YAML configuration file.
#  Returns:
#   dict: A dictionary containing the configuration settings.
def load_config(config_path: str) -> dict:
    # Open the configuration file in read mode
    with open(config_path, 'r') as config_file:
        # Load YAML content safely
        return yaml.safe_load(config_file)


#  Creates a directory if it does not already exist.
def create_directories(output_path: str):
    # Create the directory, including any necessary parent directories.
    # `exist_ok=True` prevents an error if the directory already exists.
    os.makedirs(output_path, exist_ok=True)


#  Loads and parses coordinates from a YAML file.
def get_coordinates_from_yaml(coordinates_path: str) -> list:
    # Open the coordinates YAML file in read mode
    with open(coordinates_path, 'r') as file:
        # Load YAML content safely
        coordinates_data = yaml.safe_load(file)
        coordinates_list = []
        # Iterate through each item (aim_id and its data) in the loaded YAML data
        for aim_id, data in coordinates_data.items():
            # Append a dictionary with structured coordinate information to the list
            coordinates_list.append({
                'aim_id': aim_id,
                'address': data.get('address'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timestamp': data.get('timestamp')
            })
        return coordinates_list


#Fetches historical daily weather data for the past 5 years for a given
# latitude and longitude using the Open-Meteo archive API.
def get_historical_temperature(lat: float, lng: float) -> pd.DataFrame:
    # Calculate the end date (today) and start date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)  # Approx 5 years of data

    # Construct the API URL for Open-Meteo
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lng}"
        f"&start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"  # Daily temperature metrics
        f"relative_humidity_2m_mean,precipitation_sum"  # Daily humidity and precipitation
        f"&timezone=auto"  # Automatically determine timezone
    )
    # Make the API request
    response = requests.get(url)
    data = response.json()  # Parse the JSON response

    # Check if 'daily' data is present in the response
    if 'daily' in data:
        daily = data['daily']
        # Create a Pandas DataFrame from the daily data
        return pd.DataFrame({
            'date': pd.to_datetime(
                daily['time']),  # Convert time strings to datetime objects
            'temperature_max': daily['temperature_2m_max'],
            'temperature_min': daily['temperature_2m_min'],
            'temperature_mean': daily['temperature_2m_mean'],
            'humidity': daily['relative_humidity_2m_mean'],
            'precipitation': daily['precipitation_sum']
        })


#  Saves detailed temperature data per location to CSV files and compiles
#  seasonal statistics into a summary CSV file.
def create_heatmap(temperature_data: list, output_path: str) -> str:
    lats = [d['lat'] for d in temperature_data]
    lngs = [d['lng'] for d in temperature_data]
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)

    # Create a folium map centered at the specified latitude and longitude
    m = folium.Map(location=[center_lat, center_lng], zoom_start=13)
    # Prepare data for the heatmap: list of [latitude, longitude, average temperature]
    heatmap_data = [[d['lat'], d['lng'], d['avg_temp']]
                    for d in temperature_data]
    # Add the heatmap layer to the folium map
    plugins.HeatMap(heatmap_data).add_to(m)

    # Generate a timestamp for file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Define the path for saving the heatmap HTML file
    file_path = os.path.join(output_path,
                             f"temperature_heatmap_{timestamp}.html")
    # Save the folium map as an HTML file
    m.save(file_path)
    # Return the path to the saved file
    return file_path


def save_temperature_data(all_data, detailed_data, output_path):
    # Create a timestamp for naming files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save overall temperature summary data to JSON
    with open(
            os.path.join(output_path, f"temperature_summary_{timestamp}.json"),
            'w') as f:
        json.dump(all_data, f, indent=2)

# Loop through each location's data to add metadata and save CSV
    for aim_id, df in detailed_data.items():
        location = next((d for d in all_data if d['aim_id'] == aim_id), {})
        df['aim_id'] = aim_id
        df['address'] = location.get('address', '')
        df['latitude'] = location.get('lat')
        df['longitude'] = location.get('lng')
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        # Map each month to its corresponding season
        df['season'] = df['month'].map({
            12: 'Winter',
            1: 'Winter',
            2: 'Winter',
            3: 'Spring',
            4: 'Spring',
            5: 'Spring',
            6: 'Summer',
            7: 'Summer',
            8: 'Summer',
            9: 'Autumn',
            10: 'Autumn',
            11: 'Autumn'
        })
        # Save each location's detailed temperature data to CSV
        df.to_csv(os.path.join(output_path,
                               f"temperature_data_{aim_id}_{timestamp}.csv"),
                  index=False)

    # Generate seasonal statistics for each location
    stats = []
    for aim_id, df in detailed_data.items():
        location = next((d for d in all_data if d['aim_id'] == aim_id), {})
        stats_dict = {
            'aim_id': aim_id,
            'address': location.get('address'),
            'latitude': location.get('lat'),
            'longitude': location.get('lng')
        }
        # Group by season and calculate statistical metrics
        grouped = df.groupby('season').agg({
            'temperature_mean': ['mean', 'min', 'max'],
            'temperature_max': ['mean', 'min', 'max'],
            'temperature_min': ['mean', 'min', 'max'],
            'humidity': ['mean', 'min', 'max'],
            'precipitation': ['sum', 'mean', 'max']
        }).round(2)
        # Flatten multi-index columns and store seasonal stats
        for season in grouped.index:
            for metric, stats_set in grouped.loc[season].items():
                stats_dict[
                    f"{season.lower()}_{metric[0]}_{metric[1]}"] = stats_set
        stats.append(stats_dict)


# Save aggregated statistics for all locations to a CSV file
    pd.DataFrame(stats).to_csv(os.path.join(
        output_path, f"temperature_statistics_{timestamp}.csv"),
                               index=False)


def create_trend_plots(detailed_data: dict, output_path: str):
    # Generate a timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Loop through each location's detailed data
    for aim_id, df in detailed_data.items():
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        df['season'] = df['month'].map({
            12: 'Winter',
            1: 'Winter',
            2: 'Winter',
            3: 'Spring',
            4: 'Spring',
            5: 'Spring',
            6: 'Summer',
            7: 'Summer',
            8: 'Summer',
            9: 'Autumn',
            10: 'Autumn',
            11: 'Autumn'
        })
        # Set up the figure layout
        fig = plt.figure(figsize=(20, 12))
        # Subplot 1: Yearly temperature trends with error shading
        ax1 = plt.subplot(2, 2, 1)
        yearly = df.groupby('year').agg({
            'temperature_mean': ['mean', 'std'],
            'temperature_max': ['mean', 'std'],
            'temperature_min': ['mean', 'std']
        })
        for metric in [
                'temperature_mean', 'temperature_max', 'temperature_min'
        ]:
            mean = yearly[metric]['mean']
            std = yearly[metric]['std']
            ax1.plot(mean.index, mean.values, marker='o', label=metric)
            ax1.fill_between(mean.index,
                             mean - 1.96 * std,
                             mean + 1.96 * std,
                             alpha=0.2)
        ax1.set_title('Yearly Temperature Trends')
        ax1.legend()
        ax1.grid(True)

        # Subplot 2: Seasonal temperature distribution using violin and box plots
        ax2 = plt.subplot(2, 2, 2)
        sns.violinplot(data=df, x='season', y='temperature_mean', ax=ax2)
        sns.boxplot(data=df,
                    x='season',
                    y='temperature_mean',
                    ax=ax2,
                    color='white')
        ax2.set_title('Seasonal Temperature Distribution')

        # Subplot 3: Monthly temperature trends for each year
        ax3 = plt.subplot(2, 2, 3)
        monthly = df.groupby(['year', 'month'
                              ])['temperature_mean'].mean().reset_index()
        for year in monthly['year'].unique():
            y_data = monthly[monthly['year'] == year]
            ax3.plot(y_data['month'],
                     y_data['temperature_mean'],
                     label=str(year))
            z = np.polyfit(y_data['month'], y_data['temperature_mean'], 1)
            ax3.plot(y_data['month'],
                     np.poly1d(z)(y_data['month']),
                     linestyle='--')
        ax3.set_title('Monthly Temperature Patterns by Year')
        ax3.legend()
        ax3.grid(True)

        # Subplot 4: Heatmap of average monthly temperatures by year
        ax4 = plt.subplot(2, 2, 4)
        pivot = df.pivot_table(values='temperature_mean',
                               index='year',
                               columns='month',
                               aggfunc='mean')
        sns.heatmap(pivot,
                    cmap=sns.diverging_palette(220, 10, as_cmap=True),
                    ax=ax4,
                    annot=True,
                    fmt='.1f')
        ax4.set_title('Temperature Changes Heatmap')
        # Adjust layout and save the plot to file
        plt.tight_layout()
        plot_path = os.path.join(
            output_path, f"temperature_trends_{aim_id}_{timestamp}.png")
        plt.savefig(plot_path, dpi=300)
        plt.close()


def process_temperature_pipeline(config_path: str = 'config.yaml',
                                 coordinates_path: str = 'coordinates.yaml'):
    # Load configuration settings
    config = load_config(config_path)
    output_path = config.get('directories', {}).get(
        'temperature_output', os.path.join('data', 'temperature_heatmaps'))
    # Create necessary directories
    create_directories(output_path)

    # Load coordinates from YAML file
    coordinates_list = get_coordinates_from_yaml(coordinates_path)
    # Initialise data storage structures
    temperature_data = []
    detailed_data = {}

    # Loop through each coordinate location to fetch and process temperature data
    for coord in coordinates_list:
        lat, lng = coord['latitude'], coord['longitude']
        aim_id = coord['aim_id']
        df = get_historical_temperature(lat, lng)
        if df is not None:
            avg_temp = df['temperature_mean'].mean()
            temperature_data.append({
                'lat': lat,
                'lng': lng,
                'avg_temp': avg_temp,
                'aim_id': aim_id,
                'address': coord['address']
            })
            detailed_data[aim_id] = df
# If temperature data was collected, create visualisations and save outputs
    if temperature_data:
        heatmap_file = create_heatmap(temperature_data, output_path)
        create_trend_plots(detailed_data, output_path)
        save_temperature_data(temperature_data, detailed_data, output_path)


# Run the pipeline if this file is executed directly
if __name__ == '__main__':
    process_temperature_pipeline()

