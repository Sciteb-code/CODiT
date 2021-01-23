import overpy
import csv
import time
import operator
import pandas as pd
import numpy as np
import random

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

def sumproduct(vec1, vec2):
    return sum(map(operator.mul, vec1, vec2))

def request_germany(csvfilename):
    api = overpy.Overpass()
   
    r = api.query("""
    area["ISO3166-1"="DE"][admin_level=2];
    (node["amenity"="biergarten"](area);
     way["amenity"="biergarten"](area);
     rel["amenity"="biergarten"](area);
    );
    out center;
    """)
    coords  = []
    coords += [(float(node.lon), float(node.lat)) 
               for node in r.nodes]
    coords += [(float(way.center_lon), float(way.center_lat)) 
               for way in r.ways]
    coords += [(float(rel.center_lon), float(rel.center_lat)) 
               for rel in r.relations]
    
    header_name = ['lon', 'lat']
    with open(csvfilename, 'w') as csv_coords_w:
        coords_wr = csv.writer(csv_coords_w)
        coords_wr.writerow(header_name)
   
        for coord in coords:
            coords_wr.writerow(coord)
#area["ISO3166-1"="GB"][admin_level=2];           
def request_coords_to_csv(csvfilename):
    api = overpy.Overpass()
    coords  = []
    for building_type in building_types:
        r = api.query(f"""
        area["ISO3166-2"="GB-LDS"][admin_level=8];
        (nwr["building"="{building_type}"](area);         
        );
        out center;
        """)        
        coords += [(float(node.lon), float(node.lat), building_type) 
                   for node in r.nodes]
        coords += [(float(way.center_lon), float(way.center_lat), building_type) 
                   for way in r.ways]
        coords += [(float(rel.center_lon), float(rel.center_lat), building_type) 
                   for rel in r.relations]   
        time.sleep(5)
    header_name = ['lon', 'lat','building_type']
    with open(csvfilename, 'w', newline='') as csv_coords_w:
        coords_wr = csv.writer(csv_coords_w)
        coords_wr.writerow(header_name)   
        for coord in coords:
            coords_wr.writerow(coord)
            
def get_coords(csvfilename):
    coords  = []
    with open(csvfilename, 'r') as csv_coords_f:
        coords_rd = csv.DictReader(csv_coords_f)
        coords += [[float(coord['lon']), float(coord['lat']), str(coord['building_type'])] 
               for coord in coords_rd]
        return coords

def count_coords_for_types(coords, types_count_csv):
    header_name = ['building_type', 'number']
    types_counts = []
    for building_type in building_types:
        count = 0        
        for coord in coords:
            if coord[2] == building_type:
                count += 1
        types_counts += [(building_type, count)]
    with open(types_count_csv, 'w', newline='') as csv_types_count_w:
        csv_types_count_wr = csv.writer(csv_types_count_w)
        csv_types_count_wr.writerow(header_name)
        for types_count in types_counts:
            csv_types_count_wr.writerow(types_count)
    return types_counts

def merge_building_types_constraints_to_accommodations(types_count_csv, types_constraints_csv):
    df_types_count = pd.read_csv(types_count_csv)
    df_types_constraints = pd.read_csv(types_constraints_csv)
    return pd.merge(df_types_count, df_types_constraints,on="building_type",how="inner")

def write_list_to_csv(record_list, output_csv, header_name):
    with open(output_csv, 'w') as w:
        wr = csv.writer(w)
        wr.writerow(header_name)
        for record in record_list:
            wr.writerow(record)

def allocate_households_to_each_building(num_of_households, list_types_average_households, list_coords):
    valid = 0
    df_coords_types = pd.DataFrame(list_coords, columns=['lon', 'lat', 'building_type'])


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
    return df_result.values.tolist()
def test_merge_building_types_constraints_to_accommodations(types_count_list, types_constraints_csv):
    df_types_count = pd.DataFrame(types_count_list, columns=['building_type', 'number'])
    df_types_constraints = pd.read_csv(types_constraints_csv)
    return pd.merge(df_types_count, df_types_constraints, on="building_type", how="inner")
def next_household_home(homes_list):
    next_home = random.choice(homes_list)
    homes_list.remove(next_home)
    return next_home