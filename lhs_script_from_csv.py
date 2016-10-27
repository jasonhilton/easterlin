from __future__ import division

from datetime import datetime
import os
import random as rnd
import argparse
import pandas as pd
from collections import defaultdict

import click

from intergen.experiment import Experiment, Parameters
from intergen.utils import get_default_params, get_default_param_ranges, get_default_stats

#REPETITIONS = 1

RESULTS_DIR = "./results"

REPETITIONS = 5

parser = argparse.ArgumentParser(description="Setup an experiment from given csv file")

parser.add_argument("design_path", help="path to the csv file containing the design")
parser.add_argument("range_path", help="path to the csv file containing the range")

#for i in range(4):
#        REPETITIONS[rnd.randint(0, 399)] = 6


def setup_HPC_experiment(design_path, range_path, repetitions):
    """
    Create the parameter files and results folders necessary to run simulation
    on a cluster
    """
    design = pd.read_csv(design_path)
    param_ranges = pd.read_csv(range_path)
    params_to_vary = convert_pd_to_dict(param_ranges)
    parameters = Parameters(get_default_params(), params_to_vary)

    exp = Experiment.create_from_table(design, repetitions, parameters)
    exp.add_validation_points(parameters, 50)
    date = datetime.now()
    rundate = (str(date.year) + "-" + "%02d" % date.month + "-" +
               "%02d" % date.day + "_" + "%02d" % date.hour + "." +
               "%02d" % date.minute)
    results_dir = os.path.join(RESULTS_DIR, rundate)
    os.mkdir(results_dir)
    exp.write_design_to_csv(results_dir)
    parameters.write_range_to_csv(results_dir)
    try:
        os.mkdir("./inputs")
    except OSError:
        pass
    exp.write_params_yamls("./inputs")


def convert_pd_to_dict(range_pd):
    param_ranges = defaultdict(dict)
    for param in range_pd:
        col = range_pd[param]
        param_ranges[param]["lower"] = col[0]
        param_ranges[param]["upper"] = col[1]
    return param_ranges

if __name__ == "__main__":
    arg = parser.parse_args()
    setup_HPC_experiment(arg.design_path, arg.range_path, REPETITIONS)
