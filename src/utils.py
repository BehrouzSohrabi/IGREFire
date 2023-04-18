import sys
from shapely.geometry import shape
import numpy as np
import random

# A rough estimation of cloud cover percentage based on cloud type in NREL weather dataset
cloud_cover_mapping = {
    0: 0, # Clear
    1: 10, # Probably Clear
    2: 90, # Fog
    3: 70, # Water
    4: 80, # Super-Cooled Water
    5: 50, # Mixed
    6: 60, # Opaque Ice
    7: 20, # Cirrus
    8: 100, # Overlapping
    9: 100, # Overshooting
    10: 50, # Unknown
    11: 10, # Dust
    12: 10, # Smoke
    -15: 50, # N/A
}

def wind_direction_curve(degree, noise=10):
    # Simulate noisy wind direction
    direction = degree + random.uniform(-noise, noise)
    return direction if direction >= 0 else 360+direction

def wind_speed_curve(hour, base=10, range=10):
    # Simulate wind speed changing gradually, between 20 and 35
    return base + (range * (1 + np.sin((hour - random.uniform(0, 6)) * np.pi / random.uniform(18, 24))) / 2)

def humidity_curve(hour, base=50, range=20, noise=5):
    # Simulate a daily humidity pattern with a sine wave
    day_hour = hour % 24
    daily_humidity_variation = range * np.sin((day_hour - 18) * np.pi / 12) / 2
    return base + range / 2 + daily_humidity_variation + random.uniform(-noise, noise)

def temperature_curve(hour, base=25, range=15, noise=2):
    # Simulate a daily temperature pattern with a sine wave
    day_hour = hour % 24
    daily_temp_variation = range * np.sin((day_hour - 8) * np.pi / 12) / 2
    return base + range / 2 + daily_temp_variation + random.uniform(-noise, noise)

def arrays_to_string(arrays):
    lines = [' '.join(map(str, row)) for row in arrays]
    return '\n'.join(lines)

def max_line_width(string):
    max_width = 0
    for line in string.split('\n'):
        max_width = max(len(line), max_width)
    return max_width

def callback(type, message, width = 80, separator = True):
    max_width = max_line_width(message)
    if type == 'ValueError':
        # value errors
        raise ValueError(message)
    elif type == 'Exception':
        # exception errors
        raise Exception(message)
    elif type == 'header':
        # framework header
        if width < max_width:
            width = int(max_width*1.1)
        space = (width - max_width) // 2
        print('=' * width)
        print(' '*space + message)
        print('=' * width)
    else:
        # status update
        if width < max_width:
            width = int(max_width*1.1)
        if separator:
            print('-' * width)
        print(message)

def progress_bar(iteration, total, prefix='', description='', decimals=1, length=50, fill='█', empty='░'):
    """
    Call in a loop to create terminal progress bar

    iteration: current iteration (Int)
    total: total iterations (Int)
    prefix: prefix string (Str)
    description: description string (Str)
    decimals: positive number of decimals in percent complete (Int)
    length: character length of the progress bar (Int)
    fill: bar fill character (Str)
    """
    percent = f"{100 * (iteration / float(total)):.{decimals}f}"
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + empty * (length - filled_length)
    
    # Update the progress bar
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}%')
    sys.stdout.flush()

    # Move cursor up and to the beginning of the line
    sys.stdout.write('\x1b[A\r')

    # Update the description
    sys.stdout.write(description)
    sys.stdout.flush()

    # Move cursor down and to the beginning of the line
    sys.stdout.write('\n\r')

def traverse_branch(topology, geod, points_number, points_distance):

    points = []

    # loop through features and pick point on branches
    for feature in topology['features']:
        if feature['geometry']['type'] == 'LineString': # check if feature is a branch
            
            branch_points = []
            properties = feature['properties']
            branch_id, fbus, tbus = properties['branch'], properties['fbus'], properties['tbus']
            branch_line = shape(feature['geometry'])

            # Calculate the Geodesic length in meters
            length = 0
            x_0, y_0 = branch_line.coords[0]
            for x, y in branch_line.coords[1:]:
                partial_length = geod.inv(x_0, y_0, x, y)[2]
                length += partial_length
                x_0, y_0 = x, y
            geo_scale = branch_line.length / length

            # Fixed number of ignition points per branch
            if points_number > 0:
                step = length / points_number
                initial_distance = step / 2
            # Fixed length between ignition points on all branches
            else:
                step = points_distance
                initial_distance = (length / 2) % step

            # move over the branch until it's covered
            i = 0
            while True:
                distance = geo_scale * (initial_distance + (i * step))
                if distance > branch_line.length:
                    break
                i += 1

                # find point at this distance along branch
                point = branch_line.interpolate(distance)
                branch_points.append(point)
            
            points.append({"branch_id": branch_id, "branch_points": branch_points, "fbus": fbus, "tbus": tbus})
            
    return points

