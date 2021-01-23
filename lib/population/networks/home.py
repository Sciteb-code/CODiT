"""
An attribute for each household
"""

import pandas as pd
import os
import sys
import csv
import numpy as np
REPO_DIR = os.path.dirname(os.getcwd())
sys.path.append(os.path.join(REPO_DIR, 'lib'))
DATA_PATH = os.path.join(REPO_DIR, 'data')
COORDINATES_CSV = os.path.join(DATA_PATH, 'city', 'population', 'coordinates_leeds.csv')
TYPES_CONSTRAINTS_CSV = os.path.join(DATA_PATH, 'city', 'population', 'types_households_constraints_leeds.csv')
COORDINATES_NUM_HOUSEHOLDS_CSV = os.path.join(DATA_PATH, 'city', 'population', 'coordinates_num_households_leeds.csv')
COORDINATE_PER_HOUSEHOLD_CSV = os.path.join(DATA_PATH, 'city', 'population', 'coordinate_per_household_leeds.csv')
building_types = ["apartments",
                 "bungalow",
                 "cabin",
                 "detached",
                 "dormitory",
                 "farm",
                 "ger",
                 "hotel",
                 "house",
                 "houseboat",
                 "residential",
                 "semidetached_house",
                 "static_caravan",
                 "terrace"]

class Home:
    def __init__(self, lon=0.0, lat=0.0, accommodation_type=''):
        self.coordinate = {'lon': lon, 'lat': lat}
        self.type = accommodation_type
        #self.coord_id = coord_id

def get_coords(csvfilename):
    coords  = []
    with open(csvfilename, 'r') as csv_coords_f:
        coords_rd = csv.DictReader(csv_coords_f)
        coords += [[float(coord['lon']), float(coord['lat']), str(coord['building_type'])]
               for coord in coords_rd]
        return coords

def count_coords_for_types(coords):
    types_counts = []
    for building_type in building_types:
        count = 0
        for coord in coords:
            if coord[2] == building_type:
                count += 1
        types_counts += [(building_type, count)]
    return types_counts

def merge_building_types_constraints_to_accommodations(types_count_list, types_constraints_csv):
    df_types_count = pd.DataFrame(types_count_list, columns=['building_type', 'number'])
    df_types_constraints = pd.read_csv(types_constraints_csv)
    return pd.merge(df_types_count, df_types_constraints, on="building_type", how="inner")


def allocate_households_to_each_building(num_of_households, list_types_average_households, list_coords):
    if os.path.isfile(COORDINATES_NUM_HOUSEHOLDS_CSV):
        df_result = pd.read_csv(COORDINATES_NUM_HOUSEHOLDS_CSV)

    else:
        valid = 0
        df_coords_types = pd.DataFrame(list_coords, columns=['lon', 'lat', 'building_type'])
        #df_coords_types['coord_id'] = np.array(range(len(df_coords_types.index))) + 1
        while valid != num_of_households:
            df_result = pd.DataFrame()
            list_num_households = []
            for types_average_households in list_types_average_households:
                list_num_households = list(types_average_households[3] + np.random.poisson(types_average_households[2],
                                                                                           size=types_average_households[
                                                                                               1]))
                df_temp = pd.DataFrame(df_coords_types[df_coords_types['building_type'] == types_average_households[0]])
                df_temp['num_of_households'] = list_num_households
                df_result = pd.concat([df_result, df_temp])
            valid = np.sum(df_result['num_of_households'])

        df_result.to_csv(COORDINATES_NUM_HOUSEHOLDS_CSV, index=False)
    return df_result.values.tolist()


