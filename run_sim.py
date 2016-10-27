"""
This script is intended for use for single design points
It is designed with parallelisation through pbs scripts in mind.
The design_point_number parameters is important to ensure each python instance 
is associated with a particular design point.
"""
import logging
import os
import time
from datetime import timedelta

import click

from intergen.experiment import DesignPoint
from intergen.control import Control
from intergen.utils import load_yaml
from intergen.utils import DEFAULT_PARAMS_FILE
from intergen.utils import DEFAULT_STATS_FILE
from intergen.utils import MINIM_STATS_FILE

from parameter_settings import minimal_stats_to_collect

@click.command()
@click.option("--design-point-number", default=1,
              help="Identifier for the design point at which the simulation is to be run. "
                   "Used to help match inputs and outputs.")
@click.option("--param-file", default=DEFAULT_PARAMS_FILE,
              help="Path to the location of the parameters for the simulation "
                   "runs in question")
@click.option("--log-level", default="INFO",
              help="Level of logging required must be given as a string "
                   "corresponding to a default log level such as 'info' "
                   "or 'DEBUG'")
@click.option("--repetitions", type=int,
              help="Number of repetitions of the simulation")
@click.option("--out-dir", default="results",
              help="Path in which to create results files")
@click.option("--simulation-length", default=200,
              help="Number of simulation time-steps to perform")
@click.option("--stats-to-collect-file", default=MINIM_STATS_FILE,
              help="The name of the file detailing what statistics are "
                   "collected by the simulation. Should be in yaml format")
@click.option("--add-date-folder", default=False,
              help="Should the results be saved out into a datestamped folder? "
                   "If true, a datestamped folder will be created in the path "
                   "specified by --out-dir")
def run_simulations(design_point_number, param_file, log_level, repetitions,
                    out_dir, simulation_length, stats_to_collect_file,
                    add_date_folder):
    """
    Run a simulation, or repetitions of a simulation
    """
    numeric_log_level = getattr(logging, log_level.upper())
    # try:
    #     os.mkdir("logs")
    # except OSError:
    #     pass
    #  logging.basicConfig(filename=os.path.join("logs", "intergen_{0:03d}.log"
    #                                            "".format(design_point_number)),
    #                      filemode="w", level=numeric_log_level,
    #                      format='%(asctime)s %(name)-12s %(levelname)-8s |%(message)s')
    start = time.time()
    params = load_yaml(param_file)
    # stats_to_collect = load_yaml(stats_to_collect_file)
    stats_to_collect = minimal_stats_to_collect
    if not repetitions:
        try:
            repetitions = params["repetitions"]
        except KeyError:
            repetitions = 1
    try:
        seed = params["seed"]
    except KeyError:
        seed = None

    design_point = DesignPoint(params, repetitions, design_point_number, seed)
    cont = Control.single_point(simulation_length, stats_to_collect,
                                design_point)
    cont.run_single_simulation()
    cont.write_experiment_results(out_dir, add_date_folder=add_date_folder)
    end = time.time()
    ex_time = timedelta(seconds=end - start)
    print("simulation {} took {} with {} reps"
          "".format(design_point_number, ex_time, repetitions))

if __name__ == "__main__":
    run_simulations()
