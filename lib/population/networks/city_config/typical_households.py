import logging
import random
import numpy as np

from population.networks.city_config import city_cfg as cfg


def build_characteristic_households(total_h=50000):
    """
    :param: total_h - total number of example households to build *NOTE* this must be >10000 as CARE_HOME_RATE = 0.0004
    :return: a list of lists of ages
    :approach:
        - build a list for each category
        - each category should create a list of households w respect ot data
        - each household is a list of people with an age
    """
    logging.info(f"Building a set of {total_h} households from which to build a population")

    one = house(total_h * cfg.ONE_PERSON_RATE, cfg.OVER_25_WEIGHT, house_size=1)
    pair = house(round(total_h * cfg.TWO_PERSON_RATE), cfg.ADULT_WEIGHT, house_size=2)
    sen_pair = house(total_h * cfg.TWO_SENIOR_PERSON_RATE, cfg.SENIOR_WEIGHT, house_size=2)
    sen_triple = house(total_h * cfg.OTHER_SENIOR_PERSON_RATE, cfg.SENIOR_WEIGHT, house_size=3)
    par_w_d = poisson_house(total_h * cfg.PAREN_W_DEPENDENT_RATE, cfg.CHILD_WEIGHT,
                            cfg.AVERAGE_NUMBER_OF_CHILDREN,
                            case=1, weight_2=cfg.PARENT_WEIGHT)
    fam_w_d = poisson_house(total_h * cfg.FAMILY_W_DEPENDENT_RATE, cfg.CHILD_WEIGHT,
                            cfg.AVERAGE_NUMBER_OF_CHILDREN,
                            case=2, weight_2=cfg.PARENT_WEIGHT)
    par_w_non_d = poisson_house(total_h * cfg.PAREN_W_NON_DEPENDENT_RATE, cfg.ADULT_WEIGHT,
                                cfg.AVERAGE_NUMBER_OF_CHILDREN,
                                case=1, weight_2=cfg.GROWNUP_PARENT_WEIGHT)
    fam_w_non_d = poisson_house(total_h * cfg.FAMILY_W_NON_DEPENDENT_RATE, cfg.ADULT_WEIGHT,
                                cfg.AVERAGE_NUMBER_OF_CHILDREN,
                                case=2, weight_2=cfg.GROWNUP_PARENT_WEIGHT)
    students = poisson_house(total_h * cfg.STUDENT_HOUSEHOLD_RATE, cfg.STUDENT_WEIGHT, cfg.AVERAGE_STUDENT_HOME_SIZE)
    care_home = poisson_house(total_h * cfg.CARE_HOME_RATE, cfg.SENIOR_WEIGHT, cfg.AVERAGE_CARE_HOME_SIZE)
    other = house(total_h * cfg.OTHER_HOUSEHOLD_RATE, cfg.ADULT_WEIGHT, a=2, b=4)

    all_houses = one + pair + sen_pair + sen_triple + par_w_d + fam_w_d + par_w_non_d + fam_w_non_d + students + care_home + other
    return all_houses


def house(n, weights, house_size=None, a=0, b=0):
    """
    :param n: the number of houses to build [not just building 1 in this method]
    :param weights: these weights are used to determine the ages of the inhabitants
    :param house_size: if not None: we are building houses of this size
    :param a, b: if not None then these determine the min and max sizes from which to draw house size uniformly
    :return: a list of households, in turn each household is a list of ages
    """
    h = []

    for x in range(0, int(n)):
        if house_size is None:
            house_size = random.randint(a, b)
        inside_list = pick_age(house_size, weights)
        h += [inside_list]

    return h


def poisson_house(n, weight, lam, case=None, weight_2=None):
    """
    :param n: is number of households to create based on desired rate
    :param weight: these weights are used to determine the ages of the inhabitants
    :param lam: lam we want to use in the poisson. i.e. the average size of household
    :param case: if not None this determines the number of people to create and give an age, for households with kids, this case is usually the number of parents
    :param weight_2: if not None these are desired weights (age range) for case
    :return: a list of households, in turn each household is a list of people (with an age)
    """
    h = []
    pd = truncated_poisson(lam, int(n))  # creates poisson dist. based on lambda and n

    for x in range(0, int(n)):
        val_poisson = int(pd[x])
        inside_list = pick_age(val_poisson, weight)

        if case is not None:
            inside_list += pick_age(case, weight_2)

        h += [inside_list]

    return h


def pick_age(num_people, weights):
    """
    :param num_people: number of people in the household we want to give an age to
    :param weights: these weights are used to determine the ages of the inhabitants
    :return: a list of ages with ages based on the weights provided, k is count of person #
    """
    inside_list, n = [], 0
    while n < num_people:
        rand = random.randint(0, len(weights) - 1)
        age = age_randomizer(weights[rand])
        inside_list += [age]
        n += 1

    return inside_list


def truncated_poisson(lam, size):
    """
    :param lam: lam we want to use in the poisson. i.e. the average size of household
    :param size: number of households to create
    :return: a poisson dist. (as a list) truncated such that min is zero
    """
    poissons = np.zeros(size)
    while min(poissons) == 0:
        new_poissons = np.random.poisson(lam, size=size)
        poissons[poissons < 1] = new_poissons[poissons < 1]
    return poissons


def age_randomizer(x):
    """
    :param x: range of age based on weights.
    :return: a random age (int) in a fairly small range
    """
    x = int(x)
    if x < 20 or (25 < x < 85):
        return random.randint(x, x + 9)
    return random.randint(x, x + 4)
