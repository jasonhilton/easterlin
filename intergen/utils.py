import os
import yaml
from math import exp

import numpy as np

DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(DIR, "config")
DEFAULT_STATS_FILE = os.path.join(CONFIG_DIR, "defaultStats.yaml")
MINIM_STATS_FILE = os.path.join(CONFIG_DIR, "minimStats.yaml")
DEFAULT_PARAMS_FILE = os.path.join(CONFIG_DIR, "defaultParams.yaml")
DEFAULT_PARAM_RANGE_FILE = os.path.join(CONFIG_DIR, "param_ranges.yaml")
RESULTS_PATH = os.path.abspath(os.path.join(DIR, "..", "results"))


def load_yaml(yaml_file):
    """
    load in a yaml file as a dictionary
    """
    f = open(yaml_file)
    out_dict = yaml.load(f)
    f.close()
    return out_dict


def get_default_params():
    return load_yaml(DEFAULT_PARAMS_FILE)


def get_changed_params(changed_pars):
    """
    Given a dictionary specifying a subset of parameters, returns a dictionary
    specifying all parameters, using default values for parameters not specified
    by the arg.
    """
    params = get_default_params()
    for key, item in changed_pars.items():
        params[key] = item
    return params


def get_default_param_ranges():
    return load_yaml(DEFAULT_PARAM_RANGE_FILE)


def get_default_stats():
    return load_yaml(DEFAULT_STATS_FILE)


def subset_ranges(params_to_vary):
    """
    For a subset of parameters for which we wish to conduct experiments
    get the default ranges from file as a dictionary.
    """
    default_ranges = get_default_param_ranges()
    param_ranges = {}
    for param in params_to_vary:
        param_ranges[param] = default_ranges[param]
    return param_ranges


def calculate_age_years(DOB, today):
    """
    Takes the absolute difference between the years, and subtracts one if the
    date of birth comes later in the year than the current date.
    """
    # This works because tuple comparison is lexicographic by element.
    return (today.year - DOB.year -
            ((today.month, today.day) < (DOB.month, DOB.day)))


def gompertz_mortality_fact(a, b, l, start):
    """
    construct gompertz mortality function
    to determine probability of dying at any given age
    """
    def gompertz(age):
        """
        return probability of dying at age x during a year
        """
        if age < start:
            return 0.0
        return l + a * exp( b * (age - start))
    return gompertz


def get_productivity_function(params):
    alpha = params["wage_alpha"]
    beta = params["wage_beta"]
    gamma = params["wage_gamma"]
    delta = params["wage_delta"]
    nu = params["wage_nu"]
    if params["prod_type"] == "experience":
        def prod_func(market, experience, *args, **kwargs):
            experience_years = experience.days // params["year_length"]
            prod = np.exp(gamma * experience_years -
                          delta * experience_years ** 2)
            return prod
        return prod_func
    elif params["prod_type"] == "exper-skill":
        def prod_func(market, experience, skill, *args, **kwargs):
            experience_years = experience.days // params["year_length"]
            prod = skill * np.exp(gamma * experience_years -
                          delta * experience_years ** 2)
            return prod
        return prod_func
    elif params["prod_type"] == "difficulty":
        def prod_func(market, experience, skill, difficulty):
            experience_years = experience.days // params["year_length"]
            prod = (difficulty ** beta *   # technology contribution
                    # productivity contribution
                    exp((alpha * skill - difficulty) +
                        # experience contribution
                        skill + gamma * experience_years -
                        delta * experience_years**2))
            return prod
        return prod_func
    elif params["prod_type"] == "logistic":
        def prod_func(market, experience, skill, difficulty):
            """
            Logistic productivity function - implies productivity asymptotes as
            difference between skill and diffculty increases.
            """
            experience_years = experience.days // params["year_length"]
            prod = (  # experience contribution
                    np.exp(gamma * experience_years -
                           delta * experience_years ** 2) *
                    # technology contribution
                    (difficulty ** beta /
                     # productivity contribution
                     (1 + np.exp(- alpha * (skill - difficulty))) ** nu))
            return max(prod, 0.02)
        return prod_func
    else:
        raise NotImplemented("Don't recognise parameter prod_type== {}\n"
                             "prod_type must be one of: \n"
                             "experience \n exper-skill \n difficulty\n "
                             "logistic".format(params["prod_type"]))
