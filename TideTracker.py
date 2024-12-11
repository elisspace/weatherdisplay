'''
****************************************************************
****************************************************************

                TideTracker for E-Ink Display

                        by Sam Baker

****************************************************************
****************************************************************
'''
from datetime import datetime
from PIL import ImageFont
import sys
import os
import time
import traceback
import requests, json
from io import BytesIO
import noaa_coops as nc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime as dt
import pandas as pd

sys.path.append('lib')
from waveshare_epd import epd4in26
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
icondir = os.path.join(picdir, 'icon')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'font')

'''
****************************************************************

Location specific info required

****************************************************************
'''

# Optional, displayed on top left
LOCATION = 'New York City'
# NOAA Station Code for tide data
StationID = 12345 # get station ID from NOAA

# For weather data
# Create Account on openweathermap.com and get API key
API_KEY = '<insert API key here>'
# Get LATITUDE and LONGITUDE of location
LATITUDE = '<insert latitude here>'
LONGITUDE = '<insert long here>'
UNITS = 'imperial'

# Create URL for API call
BASE_URL = 'http://api.openweathermap.org/data/3.0/onecall?'
URL = BASE_URL + 'lat=' + LATITUDE + '&lon=' + LONGITUDE + '&units=' + UNITS +'&appid=' + API_KEY


'''
****************************************************************

Functions and defined variables

****************************************************************
'''
from PIL import ImageFont

def get_text_dimensions(text_string, font):
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)


# define funciton for writing image and sleeping for specified time
def write_to_screen(image, sleep_seconds):
    print('Writing to screen.') # for debugging
    # Create new blank image template matching screen resolution
    h_image = Image.new('1', (epd.width, epd.height), 255)
    # Open the template
    screen_output_file = Image.open(os.path.join(picdir, image))
    # Initialize the drawing context with template as background
    h_image.paste(screen_output_file, (0, 0))
    epd.display(epd.getbuffer(h_image))
    # Sleep
    epd.sleep() # Put screen to sleep to prevent damage
    print('Sleeping for ' + str(sleep_seconds) +'.')
    time.sleep(sleep_seconds) # Determines refresh rate on data
    epd.init() # Re-Initialize screen


import requests

def test_noaa_api(station_id):
    url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20240720&end_date=20240721&station={station_id}&product=water_level&datum=MLLW&time_zone=lst_ldt&units=english&format=json"
    response = requests.get(url)
    print(f"NOAA API Test Response Status: {response.status_code}")
    print(f"NOAA API Test Response Content: {response.text[:200]}...")  # Print first 200 characters

# define function for displaying error
def display_error(error_source):
    # Display an error
    print('Error in the', error_source, 'request.')
    # Initialize drawing
    error_image = Image.new('1', (epd.width, epd.height), 255)
    # Initialize the drawing
    draw = ImageDraw.Draw(error_image)
    draw.text((100, 150), error_source +' ERROR', font=font50, fill=black)
    draw.text((100, 300), 'Retrying in 30 seconds', font=font22, fill=black)
    current_time = datetime.now().strftime('%H:%M')
    draw.text((300, 365), 'Last Refresh: ' + str(current_time), font = font50, fill=black)
    # Save the error image
    error_image_file = 'error.png'
    error_image.save(os.path.join(picdir, error_image_file))
    # Close error image
    error_image.close()
    # Write error to screen
    write_to_screen(error_image_file, 30)


# define function for getting weather data
def getWeather(URL):
    # Ensure there are no errors with connection
    error_connect = True
    while error_connect == True:
        try:
            # HTTP request
            print('Attempting to connect to OWM.')
            response = requests.get(URL)
            print('Connection to OWM successful.')
            error_connect = None
        except:
            # Call function to display connection error
            print('Connection error.')
            display_error('CONNECTION')

    # Check status of code request
    if response.status_code == 200:
        print('Connection to Open Weather successful.')
        # get data in jason format
        data = response.json()

        with open('data.txt', 'w') as outfile:
            json.dump(data, outfile)

        return data

    else:
        # Call function to display HTTP error
        display_error('HTTP')

def generate_summary(wind_speed, temp_current, precip):
    # Define thresholds
    WIND_THRESHOLD_HIGH = 15  # example threshold for too windy (in MPH)
    TIDE_THRESHOLD_HIGH = 5.0  # example threshold for high tide (in feet)
    TEMP_THRESHOLD_LOW = 70  # example for too cold (in Fahrenheit)
    TEMP_THRESHOLD_HIGH = 90  # example for too hot (in Fahrenheit)
    PRECIP_THRESHOLD = 15  # example for high precipitation (in percentage)

    # Logic for generating the summary
    summary = []

    if wind_speed > WIND_THRESHOLD_HIGH:
        summary.append("Too windy")
    #if tide_level > TIDE_THRESHOLD_HIGH:
    #    summary.append("Tide too high")
    if temp_current < TEMP_THRESHOLD_LOW:
        summary.append("Too cold")
    elif temp_current > TEMP_THRESHOLD_HIGH:
        summary.append("Too hot")
    if daily_precip_percent > PRECIP_THRESHOLD:
        summary.append("Too much rain")

    # Check for "just right" conditions
    if not summary:
        summary.append("Just right")

    return ", ".join(summary)


# last 24 hour data, add argument for start/end_date
def past24(StationID):
    try:
        # Create Station Object
        stationdata = nc.Station(StationID)

        # Get today date string
        today = dt.datetime.now()
        todaystr = today.strftime("%Y%m%d %H:%M")
        # Get yesterday date string
        yesterday = today - dt.timedelta(days=1)
        yesterdaystr = yesterday.strftime("%Y%m%d %H:%M")

        print(f"Requesting tide data from {yesterdaystr} to {todaystr}")

        # Get water level data
        WaterLevel = stationdata.get_data(
            begin_date=yesterdaystr,
            end_date=todaystr,
            product="water_level",
            datum="MLLW",
            time_zone="lst_ldt")

        print("Raw API response:")
        print(WaterLevel)
        if isinstance(WaterLevel, str):
                print("API returned a string instead of JSON. Content:")
                print(WaterLevel)
                raise ValueError("Invalid API response")

        
        WaterLevel['v'] = WaterLevel['v'].astype(float)

        print("WaterLevel data structure:")
        print(WaterLevel.columns)
        print(WaterLevel.head())

        return WaterLevel
    except Exception as e:
        print(f"Error in past24: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error args: {e.args}")
        raise


def get_tide_data(station_id):
    try:
        # Get today and yesterday's date
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        # Format the URL
        url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={yesterday.strftime('%Y%m%d')}&end_date={today.strftime('%Y%m%d')}&station={station_id}&product=water_level&datum=MLLW&time_zone=lst_ldt&units=english&format=json"
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['data'])
        
        # Convert 't' to datetime and set as index
        df['t'] = pd.to_datetime(df['t'])
        df.set_index('t', inplace=True)
        
        # Convert 'v' to float
        df['v'] = df['v'].astype(float)
        
        print("WaterLevel data structure:")
        print(df.head())
        print(df.dtypes)
        
        return df
    except Exception as e:
        print(f"Error in get_tide_data: {str(e)}")
        raise


def test_noaa_api_direct(station_id):
    today = dt.datetime.now()
    yesterday = today - dt.timedelta(days=1)
    
    url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={yesterday.strftime('%Y%m%d')}&end_date={today.strftime('%Y%m%d')}&station={station_id}&product=water_level&datum=MLLW&time_zone=lst_ldt&units=english&format=json"
    
    try:
        response = requests.get(url)
        print(f"Direct NOAA API Response Status: {response.status_code}")
        print(f"Direct NOAA API Response Content: {response.text[:500]}...")  # Print first 500 characters
    except Exception as e:
        print(f"Error in direct NOAA API request: {str(e)}")


# Plot last 24 hours of tide
def plotTide(TideData):
    water_level_column = 'v'

    # Ensure the index is datetime
    if not isinstance(TideData.index, pd.DatetimeIndex):
        TideData.index = pd.to_datetime(TideData.index)

    # Filter data to include only the last 12 hours
    end_time = TideData.index.max()
    start_time = end_time - timedelta(hours=12)
    TideData = TideData.loc[start_time:end_time]

    # Adjust data for negative values
    minlevel = TideData[water_level_column].min()
    TideData[water_level_column] = TideData[water_level_column].astype(float) - minlevel

    # Create Plot - adjust figure size to match your e-ink display dimensions
    fig, axs = plt.subplots(figsize=(8, 3))  # Adjust these values as needed

    # Adjust subplot parameters
    plt.subplots_adjust(left=0.00, right=0.95, top=0.9, bottom=0.2)

    # Convert datetime to matplotlib date numbers
    dates = mdates.date2num(TideData.index.to_pydatetime())

    # Plot using matplotlib's plot function
    axs.fill_between(dates, 0, TideData[water_level_column], color='black', alpha=0.1)
    axs.plot(dates, TideData[water_level_column], color='black', linewidth=2)

    # Add vertical line for current time
    current_time = datetime.now()
    axs.axvline(x=mdates.date2num(current_time), color='black', linestyle='--', linewidth=4)

    # Format x-axis to show only hours
    axs.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
    axs.xaxis.set_major_locator(mdates.HourLocator(interval=6))

    # Remove top and right spines
    axs.spines['top'].set_visible(False)
    axs.spines['right'].set_visible(False)

    # Add labels
    #plt.ylabel('Tide (ft)', fontsize=8)
    #plt.xlabel('Hour', fontsize=8)

    # Increase tick label font size
    axs.tick_params(axis='both', which='major', labelsize=8)

    # Tight layout
    plt.tight_layout()

    # Save and close
    plt.savefig('images/TideLevel.png', dpi=80, bbox_inches='tight', pad_inches=0.0)
    plt.close(fig)  # Close the figure to free up memory


def get_hilo_data(station_id):
    try:
        # Get today and tomorrow's date
        today = dt.datetime.now()
        tomorrow = today + dt.timedelta(days=1)
        
        # Format the URL
        url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={today.strftime('%Y%m%d')}&end_date={tomorrow.strftime('%Y%m%d')}&station={station_id}&product=predictions&datum=MLLW&interval=hilo&time_zone=lst_ldt&units=english&format=json"
        
        # Make the request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse the JSON response
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['predictions'])
        
        # Convert 't' to datetime and set as index
        df['t'] = pd.to_datetime(df['t'])
        df.set_index('t', inplace=True)
        
        print("HiLo data structure:")
        print(df.columns)
        print(df.head())
        
        return df
    except Exception as e:
        print(f"Error in get_hilo_data: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error args: {e.args}")
        raise

def HiLo(StationID): # trying to replace this with get_hilo_data
    try:
        # Create Station Object
        stationdata = nc.Station(StationID)

        # Get today date string
        today = dt.datetime.now()
        todaystr = today.strftime("%Y%m%d")
        # Get tomorrow date string
        tomorrow = today + dt.timedelta(days=1)
        tomorrowstr = tomorrow.strftime("%Y%m%d")

        print(f"Requesting tide prediction data from {todaystr} to {tomorrowstr}")

        # Get Hi and Lo Tide info
        TideHiLo = stationdata.get_data(
            begin_date=todaystr,
            end_date=tomorrowstr,
            product="predictions",
            datum="MLLW",
            interval="hilo",
            time_zone="lst_ldt")

        print("TideHiLo data structure:")
        print(TideHiLo.columns)
        print(TideHiLo.head())

        # Print the first few rows of data
        print("First few rows of TideHiLo data:")
        print(TideHiLo.head().to_string())
        print("Data types of TideHiLo columns:")
        print(TideHiLo.dtypes)

        return TideHiLo
    except Exception as e:
        print(f"Error in HiLo: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error args: {e.args}")
        raise


# Set the font sizes
font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
font20 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 20)
font22 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 22)
font30 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 30)
font35 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 35)
font50 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 50)
font60 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 60)
font100 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 100)
font160 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 160)

# Set the colors
black = 'rgb(0,0,0)'
white = 'rgb(255,255,255)'
grey = 'rgb(235,235,235)'


'''
****************************************************************

Main Loop

****************************************************************
'''

# Initialize and clear screen
print('Initializing and clearing screen.')
epd = epd4in26.EPD() # Create object for display functions
epd.init()
epd.Clear()

while True:
    # test_noaa_api(StationID) #testing for Claude
#    try:
#        WaterLevel = get_tide_data(StationID)
#        print("Water Level Data:")
#        print(WaterLevel.head())
#        print(WaterLevel.dtypes)
#        plotTide(WaterLevel)
#    except Exception as e:
#        print(f"Error: {str(e)}")
#        print(f"Error type: {type(e).__name__}")
#        print(f"Error args: {e.args}")

    # Get weather data
    data = getWeather(URL)

    # get current dict block
    current = data['current']
    # get current
    temp_current = current['temp']
    # get feels like
    feels_like = current['feels_like']
    # get wind speed
    wind_speed = current['wind_speed']
    # get humidity
    humidity = current['humidity']
    # get pressure
    wind = current['wind_speed']
    # get description
    weather = current['weather']
    report = weather[0]['description']
    # get icon url
    icon_code = weather[0]['icon']

    # get daily dict block
    daily = data['daily']
    # get daily precip
    daily_precip_float = daily[0]['pop']
    #format daily precip
    daily_precip_percent = daily_precip_float * 100
    # get min and max temp
    daily_temp = daily[0]['temp']
    temp_max = daily_temp['max']
    temp_min = daily_temp['min']

    # Generate simple text summary
    summary = generate_summary(wind_speed, temp_current, daily_precip_percent)
    print(summary)

    # Set strings to be printed to screen
    string_location = LOCATION
    string_temp_current = format(temp_current, '.0f') + u'\N{DEGREE SIGN}F'
    string_feels_like = 'Feels like: ' + format(feels_like, '.0f') +  u'\N{DEGREE SIGN}F'
    string_humidity = 'Humidity: ' + str(humidity) + '%'
    string_wind = 'Wind: ' + format(wind, '.1f') + ' MPH'
    string_report = 'Now: ' + report.title()
    string_temp_max = 'High: ' + format(temp_max, '>.0f') + u'\N{DEGREE SIGN}F'
    string_temp_min = 'Low:  ' + format(temp_min, '>.0f') + u'\N{DEGREE SIGN}F'
    string_precip_percent = 'Precip: ' + str(format(daily_precip_percent, '.0f'))  + '%'

    # get min and max temp
    nx_daily_temp = daily[1]['temp']
    nx_temp_max = nx_daily_temp['max']
    nx_temp_min = nx_daily_temp['min']
    # get daily precip
    nx_daily_precip_float = daily[1]['pop']
    #format daily precip
    nx_daily_precip_percent = nx_daily_precip_float * 100

    # get min and max temp
    nx_nx_daily_temp = daily[2]['temp']
    nx_nx_temp_max = nx_nx_daily_temp['max']
    nx_nx_temp_min = nx_nx_daily_temp['min']
    # get daily precip
    nx_nx_daily_precip_float = daily[2]['pop']
    #format daily precip
    nx_nx_daily_precip_percent = nx_nx_daily_precip_float * 100

    # Tomorrow Forcast Strings
    nx_day_high = 'High: ' + format(nx_temp_max, '>.0f') + u'\N{DEGREE SIGN}F'
    nx_day_low = 'Low: ' + format(nx_temp_min, '>.0f') + u'\N{DEGREE SIGN}F'
    nx_precip_percent = 'Precip: ' + str(format(nx_daily_precip_percent, '.0f'))  + '%'
    nx_weather_icon = daily[1]['weather']
    nx_icon = nx_weather_icon[0]['icon']

    # Overmorrow Forcast Strings
    nx_nx_day_high = 'High: ' + format(nx_nx_temp_max, '>.0f') + u'\N{DEGREE SIGN}F'
    nx_nx_day_low = 'Low: ' + format(nx_nx_temp_min, '>.0f') + u'\N{DEGREE SIGN}F'
    nx_nx_precip_percent = 'Precip: ' + str(format(nx_nx_daily_precip_percent, '.0f'))  + '%'
    nx_nx_weather_icon = daily[2]['weather']
    nx_nx_icon = nx_nx_weather_icon[0]['icon']

    # Last updated time
    now = dt.datetime.now()
    current_time = now.strftime("%H:%M")
    last_update_string = 'Last Updated: ' + current_time

    test_noaa_api_direct(StationID) #testing

    # Tide Data
    # Get water level
    wl_error = True
    while wl_error == True:
        try:
            WaterLevel = get_tide_data(StationID) #trying to replace past24
            #WaterLevel = past24(StationID)
            wl_error = False
        except Exception as e:
            print(f"Error retrieving tide data: {str(e)}")
            display_error('Tide Data')
            time.sleep(30)  # Wait for 30 seconds before retrying

    try:
        plotTide(WaterLevel)
    except Exception as e:
        print(f"Error in plotTide: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error args: {e.args}")


    # Open template file
    template = Image.open(os.path.join(picdir, 'template.png'))
    # Initialize the drawing context with template as background
    draw = ImageDraw.Draw(template)

    # Current weather
    ## Open icon file
    icon_file = icon_code + '.png'
    icon_image = Image.open(os.path.join(icondir, icon_file))
    icon_image = icon_image.resize((130,130))
    template.paste(icon_image, (50, 50))

    draw.text((125,10), LOCATION, font=font35, fill=black)

    # Center current weather report
    w, h = get_text_dimensions(string_report, font20)
    
    #print(w)
    if w > 250:
        string_report = 'Now:\n' + report.title()

    center = int(120-(w/2))
    draw.text((center,175), string_report, font=font20, fill=black)

    # Data
    draw.text((250,55), string_temp_current, font=font35, fill=black)
    y = 100
    draw.text((250,y), string_feels_like, font=font15, fill=black)
    draw.text((250,y+20), string_wind, font=font15, fill=black)
    draw.text((250,y+40), string_precip_percent, font=font15, fill=black)
    draw.text((250,y+60), string_temp_max, font=font15, fill=black)
    draw.text((250,y+80), string_temp_min, font=font15, fill=black)

    draw.text((125,218), last_update_string, font=font15, fill=black)

    # Weather Forcast
    # Tomorrow
    icon_file = nx_icon + '.png'
    icon_image = Image.open(os.path.join(icondir, icon_file))
    icon_image = icon_image.resize((130,130))
    template.paste(icon_image, (435, 50))
    draw.text((450,20), 'Tomorrow', font=font22, fill=black)
    draw.text((415,180), nx_day_high, font=font15, fill=black)
    draw.text((515,180), nx_day_low, font=font15, fill=black)
    draw.text((460,200), nx_precip_percent, font=font15, fill=black)

    # Next Next Day Forcast
    icon_file = nx_nx_icon + '.png'
    icon_image = Image.open(os.path.join(icondir, icon_file))
    icon_image = icon_image.resize((130,130))
    template.paste(icon_image, (635, 50))
    draw.text((625,20), 'Next-Next Day', font=font22, fill=black)
    draw.text((615,180), nx_nx_day_high, font=font15, fill=black)
    draw.text((715,180), nx_nx_day_low, font=font15, fill=black)
    draw.text((660,200), nx_nx_precip_percent, font=font15, fill=black)


    ## Dividing lines
    draw.line((400,10,400,220), fill='black', width=3)
    draw.line((600,20,600,210), fill='black', width=2)


    # Tide Info
    # Graph
    tidegraph = Image.open('images/TideLevel.png')
    # template.paste(tidegraph, (125, 240)) Original Numbers
    template.paste(tidegraph, (160, 250))

    # Large horizontal dividing line
    h = 240
    draw.line((25, h, 775, h), fill='black', width=3)

    # Daily tide times
    draw.text((30,260), "Today's Tide", font=font22, fill=black)

    # Get tide time predictions
    hilo_error = True
    while hilo_error == True:
        try:
            hilo_daily = get_hilo_data(StationID)
            # hilo_daily = HiLo(StationID) #replaced with new function get_hilo_data
            print("HiLo function completed successfully") # Claude troubleshooting
            hilo_error = False
        except:
            print(f"Error in HiLo: {str(e)}")
            display_error('Tide Prediction')
            time.sleep(30)  # Wait for 30 seconds before retrying

    # Display tide preditions
    y_loc = 300 # starting location of list
    if 'type' in hilo_daily.columns:
        # Iterate over predictions
        current_time = datetime.now()
        future_tides = hilo_daily[hilo_daily.index > current_time]

        for index, row in future_tides.head(4).iterrows():
            # For high tide
            if row['type'] == 'H':
                tide_time = index.strftime("%H:%M")
                tidestr = "High: " + tide_time
            # For low tide
            elif row['type'] == 'L':
                tide_time = index.strftime("%H:%M")
                tidestr = "Low:  " + tide_time

            # Draw to display image
            draw.text((40,y_loc), tidestr, font=font15, fill=black)
            y_loc += 25 # This bumps the next prediction down a line
    else:
        print("'type' column not found in tide prediction data")
        print("Available columns:", hilo_daily.columns)
        # You might want to add some error handling or alternative display here
        draw.text((40,y_loc), "Tide data unavailable", font=font15, fill=black)


    # Save the image for display as PNG
    screen_output_file = os.path.join(picdir, 'screen_output.png')
    template.save(screen_output_file)
    # Close the template file
    template.close()

    write_to_screen(screen_output_file, 600)
    #epd.Clear()
