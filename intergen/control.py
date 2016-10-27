"""
Module responsible for controling the execution of the simulation

    Seed? AND RNGs!
    Perhaps should be set in experiment
"""

import os
import logging
from datetime import datetime


import yaml

from .experiment import Experiment, DesignPoint
from .simulation import Simulation
from .statistics_collector import StatisticsCollector, VoidStatisticsCollector
logger = logging.getLogger("intergen")


class Control(object):
    def __init__(self, run_length, stats_to_collect, experiment):
        """
        Control the execution of a series of simulations

        Parameter
        ---------
        run_length: int
            Length of each simulation, defined in years
        stats_to_collect: iterable of strings
            A list of the statistics you wish to collect from ths Simulation
        experiment: Experiment
            An object of class exeriment, giving all the design points
            to be run. Act like an iterable of design points.
        """
        # For a single run, the special constructor is used and instead a 
        # experiment can be an instance of Experiment class.
        # a single design point is put in a list.

        self.experiment = experiment
        self.run_length = run_length

        self.stats_to_collect = stats_to_collect
        self.results = {}
        self.sims_run = False

    def conduct_experiment(self, experiment):
        """
        Sets off a number of simulations based on the contents of arg.
        """
        # should I pass here or use self
        # note inconsitency with write sim below.
        logging.info("Beginning simulation runs...")
        number_design_points = len(experiment)

        for design_point in experiment:
            self.results[design_point.number] = {}
            logging.info("Running at design_point {} of {}".format(
                             design_point.number, number_design_points))
            self.do_repetitions(design_point)
        self.sims_run = True


    def do_repetitions(self, design_point):
        for rep in range(design_point.repetitions):
            # some logging here so's time can be tracked.
            logging.info("Running repetition {} of {} "
                         "for design_point {}".format(rep + 1, # (0-indexed)
                                                      design_point.repetitions,
                                                      design_point.number))
            self.setup_simulation(design_point)
            self.run_simulation()
            self.process_stats()
            self.results[design_point.number][rep] = self.stats

    def setup_simulation(self, design_point):
        """
        setup a simulation for the specified design_point
        """
        if not self.stats_to_collect:
            self.stats = VoidStatisticsCollector()
        else:
            self.stats = StatisticsCollector(self.stats_to_collect)

        seed = design_point.next_seed()
        self.sim = Simulation(design_point.params, self.stats, seed)
        # self.stats.register_sim(self.sim)

    def run_simulation(self):
        # maybe there's a better way of doing this.
        if self.sim.params["timestep"] == "year":
            timesteps = self.run_length
        elif self.sim.params["timestep"] == "month":
            timesteps = self.run_length * 12
        else:
            timesteps = self.run_length * \
                        self.sim.params["year_length"] / \
                        self.sim.params["timestep"]
        self.sim.run_sim(timesteps)

    def process_stats(self):
        # Very thin...
        self.stats.process_stats()

    def write_experiment_results(self, results_dir, add_date_folder=True):
        """
        Write our all experiment results to csv files, 1 per repetition.
        """

        if not self.sims_run:
            raise SimNotRunException("Can't write out results"
                                     " as simulations have not been run")

        if add_date_folder:
            date = datetime.now()
            rundate = (str(date.year) + "-" + "%02d" % date.month + "-" +
                       "%02d" % date.day + "_" + "%02d" % date.hour + "." +
                       "%02d" % date.minute)
            results_dir = os.path.join(results_dir, rundate)

            os.mkdir(results_dir)

        for design_point in self.experiment:
            self.write_design_point_results(design_point, results_dir)

    def write_design_point_results(self, design_point, experiment_results_dir):
        """
        Write out results to dated folder.
        """
        for rep, stats in self.results[design_point.number].items():
            suffix = "{point:03d}_{run:03d}".format(point=design_point.number,
                                                    run=rep)
            stats.save_out_all_stats(experiment_results_dir, suffix)

        design_point.write_parameters_to_yaml(experiment_results_dir)

        # fff = open(os.path.join(experiment_results_dir, "params" + "_" +
        #                         "{0:03d}".format(design_point.number) + ".yaml"),
        #            mode="x")
        # yaml.dump(design_point.number, fff)

    @classmethod
    def single_point(cls, run_length, stats_to_collect, design_point):
        """
        Setup simulation for runs at a single design point.
        Parameters
        ----------
        run_length: int
            Length in timesteps that the simulation should run for.
        stats_to_collect: dict
            Nested dictionaries determining the types
        design_point: DesignPoint
            Instance of DesignPoint class. Give info about parameters,
            number of repetitions etc.
        """
        return cls(run_length, stats_to_collect, [design_point])

    @classmethod
    def from_param_dict(cls, run_length, stats_to_collect, params):
        """
        Setup simulation for a single run based on parameter dictionary
        """
        design_point = DesignPoint(params)
        return cls(run_length, stats_to_collect, [design_point])

    def run_single_simulation(self):
        logging.info("Running simulation at one design point")
        design_point = self.experiment[0]
        self.results[design_point.number] = {}
        self.do_repetitions(design_point)
        self.sims_run = True


class SimNotRunException(Exception):
    def __init__(self, message):
        super(SimNotRunException, self).__init__(message)







#if __name__ == "__main__":
