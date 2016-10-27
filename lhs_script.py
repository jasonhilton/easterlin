from __future__ import division

from datetime import datetime
import os
import random as rnd

import click

from intergen.experiment import Experiment, Parameters
from intergen.utils import get_default_params, get_default_param_ranges, get_default_stats
from intergen.utils import subset_ranges

#REPETITIONS = 1

RESULTS_DIR = "./results"
# PARAMS_TO_VAR = ["support_ratio", "churn", "imprinting_time",
#                  "social_security_level", "job_apps_unemployed", "wage_gamma"]

# PARAMS_TO_VAR = ["linear_growth", "wage_feedback_mult", "wage_alpha",
#                  "wage_gamma", "wage_delta", "growth_rate", "support_ratio",
#                  "parity_offset", "parity_feedback_mult", "aspiration_offset",
#                  "inheritance_corr", "prob_mult", "prob_asymptote"]


PARAMS_TO_VAR = ["wage_feedback_mult", "growth_rate", "support_ratio",
                 "parity_offset", "aspiration_offset_max", "desire2",
                 "inheritance_corr"]


N_POINTS = 400
REPETITIONS = [5] * N_POINTS


#for i in range(4):
#        REPETITIONS[rnd.randint(0, 399)] = 6


def setup_HPC_experiment(n_points, repetitions, params_to_vary):
    """
    Create the parameter files and results folders necessary to run simulation
    on a cluster
    """

    params_to_vary = subset_ranges(params_to_vary)
    parameters = Parameters(get_default_params(), params_to_vary)
    exp = Experiment.create_lhs(n_points, parameters, repetitions)
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


if __name__ == "__main__":
    setup_HPC_experiment(N_POINTS, REPETITIONS, PARAMS_TO_VAR)
