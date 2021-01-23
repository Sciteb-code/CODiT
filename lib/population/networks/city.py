import random
import numpy as np
import pandas as pd
import logging

from population.population import FixedNetworkPopulation
from population.networks import household_workplace
from population.networks import home
from population.networks.home import Home, COORDINATES_CSV, TYPES_CONSTRAINTS_CSV
from population.networks.city_config.city_cfg import MINIMUM_WORKING_AGE, MAXIMUM_WORKING_AGE, MAXIMUM_CLASS_AGE, MINIMUM_CLASS_AGE, AVERAGE_HOUSEHOLD_SIZE
from population.networks.city_config.typical_households import build_characteristic_households

EPHEMERAL_CONTACT = 0.1  # people per day


class CityPopulation(FixedNetworkPopulation):
    def reset_people(self, society):
        # logging.info("CityPopulation.reset_people")
        # count = 0
        for person in self.people:
            #if count < 5:
                #logging.info(f"reset person's home to {person.home.type}, {person.home.coordinate['lon']} and {person.home.coordinate['lat']}")
            #count += 1
            person.__init__(society, config=society.cfg.__dict__, name=person.name, home=person.home)
    def fix_cliques(self, encounter_size):
        """
        :param encounter_size: not used
        :return:
        """
        static_cliques = self.build_city_cliques()
        logging.info(f"Adding {len(static_cliques)} permanent contact groups")
        dynamic_cliques = FixedNetworkPopulation.fix_cliques(self, EPHEMERAL_CONTACT)
        logging.info(f"Adding {len(dynamic_cliques)} ephemeral contact pairs")
        return static_cliques + dynamic_cliques


    def build_city_cliques(self):
        """
        :param people: a list of population.covid.PersonCovid() objects
        :return: a list of little sets, each is a 'clique' in the graph, some are households, some are workplaces
        each individual should belong to exactly one household and one workplace
        for example: [{person_0, person_1, person_2}, {person_0, person_10, person_54, person_88, person_550, person_270}]
        - except not everyone is accounted for of course
        """
        households = self.build_households()
        report_size(households, 'households')

        classrooms = build_class_groups(self.people)

        working_age_people = [p for p in self.people if MINIMUM_WORKING_AGE < p.age < MAXIMUM_WORKING_AGE]
        teachers = random.sample(working_age_people, len(classrooms))
        classrooms = [clss | {teachers[i]} for i, clss in enumerate(classrooms)]
        report_size(classrooms, 'classrooms')

        care_homes = [h for h in households if is_care_home(h)]
        carers = assign_staff(care_homes, working_age_people)

        working_age_people = list(set(working_age_people) - set(teachers) - set(carers))
        random.shuffle(working_age_people)
        workplaces = build_workplaces(working_age_people)
        report_size(workplaces, 'workplaces')

        return households + workplaces + classrooms + care_homes

    def build_households(self):
        """
        :param people: a list of population.covid.PersonCovid() objects
        :return: a list of households, where households are a list of person objects. now with an assigned age.
        """
        n_individuals = len(self.people)
        assigned = 0
        households = []

        num_h = int(n_individuals / AVERAGE_HOUSEHOLD_SIZE)
        household_examples = build_characteristic_households(num_h)
        homes_list = build_households_home_list(num_h)
        logging.info(f"There are {len(homes_list)} households generated for accommodation buildings")
        #logging.info(f"longitude: {homes_list[0][0]} latitude: {homes_list[0][1]}")
        while assigned < n_individuals:
            ages = next_household_ages(household_examples)
            home = next_household_home(homes_list)
            #if len(households) < 5:
                #logging.info(f"Coordinates: {home[0]}, {home[1]}")
            size = len(ages)

            if assigned + size > n_individuals:
                ages = ages[:n_individuals - assigned - size]
                size = len(ages)

            hh = []
            for j, age in enumerate(ages):
                indiv = self.people[j + assigned]
                indiv.age = age
                self.people[j + assigned].home = Home(home[0], home[1], home[2])
                #logging.info(f"person's coordinates: longitude={indiv.home.coordinate['lon']}, latitude={indiv.home.coordinate['lat']}s")
                hh.append(indiv)
            households.append(set(hh))
            assigned += size

        return households

def is_care_home(home):
    return min([p.age for p in home]) >= MAXIMUM_WORKING_AGE and len(home) > 20


def assign_staff(care_homes, working_age_people, staff=5):
    carers = set()
    for home in care_homes:
        home_carers = set(random.sample(working_age_people, staff))
        home |= home_carers
        carers |= home_carers
    report_size(care_homes, 'care_homes')
    return carers


def report_size(care_homes, ch):
    logging.info(f"{len(care_homes)} {ch} of mean size {np.mean([len(x) for x in care_homes]):2.2f}")


def build_class_groups(people):
    classrooms = []
    for kids_age in range(MINIMUM_CLASS_AGE, MAXIMUM_CLASS_AGE+1):
        schoolkids = [p for p in people if p.age == kids_age]
        random.shuffle(schoolkids)
        classrooms += build_workplaces(schoolkids, classroom_size=30)
    logging.info(f"Only putting children >{MINIMUM_CLASS_AGE} years old into classrooms.")
    return classrooms




def build_households_home_list(total_h=50000):
    coords_types = home.get_coords(COORDINATES_CSV)
    types_counts = home.count_coords_for_types(coords_types)
    df_types_constraints_households = home.merge_building_types_constraints_to_accommodations(types_counts, TYPES_CONSTRAINTS_CSV)

    aver_num_households = (df_types_constraints_households['min_households'] + df_types_constraints_households['max_households']) / 2
    df_types_constraints_households['average_num_households'] = aver_num_households
    init_total_households = np.sum(df_types_constraints_households['number'] * aver_num_households)
    index_apartments = df_types_constraints_households['building_type']=='apartments'
    remaining_households_in_apartments = total_h - (init_total_households - df_types_constraints_households.loc[index_apartments, 'average_num_households'] * \
    df_types_constraints_households.loc[index_apartments, 'number'])
    df_types_constraints_households.loc[index_apartments, 'average_num_households'] = remaining_households_in_apartments / \
                                                                                        df_types_constraints_households.loc[index_apartments, 'number']
    df_types_constraints_households.drop('max_households', axis = 1, inplace=True)

    list_types_average_households = list(
        zip(df_types_constraints_households['building_type'], df_types_constraints_households['number'],
            df_types_constraints_households['average_num_households'] - df_types_constraints_households['min_households'],
            df_types_constraints_households['min_households']))
    list_num_households_per_building = home.allocate_households_to_each_building(total_h, list_types_average_households, coords_types)
    list_households_info = []
    for num_households_per_building in list_num_households_per_building:

        if int(num_households_per_building[3]) > 0:
            list_households_info += [num_households_per_building[:3]] * int(num_households_per_building[3])

    return list_households_info





def next_household_home(homes_list):

    next_home = random.choice(homes_list)
    homes_list.remove(next_home)
    return next_home

def next_household_ages(household_list):
    """
    :param: complete list of households
    :return: randomly select a type of household from a distribution suitable to City,
    and return the list of the ages of the people in that household
    """
    return random.choice(household_list)


def build_workplaces(people, classroom_size=-1):
    """
    :param people: lets for now let these be a list of N population.covid.PersonCovid() objects
    :return: a list of workplaces, where workplaces are a list of person objects.
    """
    n_individuals = len(people)
    assigned = 0
    workplaces = []
    while assigned < n_individuals:
        if classroom_size > 0:
            size = 30
        else:
            size = next_workplace_size()

        if assigned + size >= n_individuals:
            size = n_individuals - assigned

        assert size > 0

        hh = people[assigned: assigned + size]
        workplaces.append(set(hh))
        assigned += size

    return workplaces


def next_workplace_size():
    return random.choice(household_workplace.WORKPLACE_SIZE_REPRESENTATIVE_EXAMPLES)
