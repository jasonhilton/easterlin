"""
Class representing a single Simulation
contains methods for running simulation
"""

from __future__ import division
import logging
import datetime
import copy
import random as rnd
import numpy.random as nprnd

from .population import Population
from .agent_factory import AgentFactory
from .timestepper import TimeStepper
from .labmarket import LabourMarket
from .utils import get_productivity_function


class BaseSim(object):
    """
    For testing
    """

    def __init__(self):
        self.time = 0


class Simulation(BaseSim):
    """
    Class representing one simulation
    """

    def __init__(self, parameters, statistics_collector, seed=None):
        logging.info("Setting up simulation ... ")
        self.params = parameters
        self.timestepper = TimeStepper(parameters)
        agent_factory = AgentFactory(parameters, self.timestepper,
                                     statistics_collector)

        # setting random with None means system randomness is sought for seed
        rnd.seed(seed)
        # set numpy.random with a seed derived from random.
        nprnd.seed(rnd.randint(100, 100000))  # arbitrary

        # set start date
        self.start_date = datetime.datetime.strptime(parameters["start_date"],
                                                     "%Y-%m-%d").date()

        # initialise population
        self.pop = Population(parameters, self, agent_factory)

        # initialise labour market
        num_jobs = int(self.pop.get_lab_force_size() *
                       parameters["setup_job_lab_ratio"])
        LabourMarket.prod_function = get_productivity_function(parameters)
        self.labour_market = LabourMarket(parameters, num_jobs,
                                          self.timestepper)
        self.pop.setup_cohort_sizes()
        self.labour_market.update_feedbacks(self.pop.get_relative_cohort_sizes("Male"))
        self.setup_labour_market()
        self.pop.do_partnership_setup()
        # logging.info("Finished Setup")
        print("Finished Setup")

        self.stats = statistics_collector

    def setup_labour_market(self):
        """
        ensure that during the first time step some are employed
        """

        for _ in range(self.params["job_burnin_rounds"]):
            indexes = list(range(len(self.pop.poplist)))
            nprnd.shuffle(indexes)
            for i in indexes:
                self.pop.poplist[i].employment.job_setup_activity(self.labour_market)
            self.labour_market.send_offers(self.pop)
            self.pop.resolve_job_offers()

    def time_step(self):
        """
        step the simulation forward one time_step
        as defined in the parameter dictionary.
        """
        self.pop.update(self)
        self.labour_market.update_jobs(self.pop)
        self.pop.do_applications(self)
        self.labour_market.send_offers(self.pop)
        self.pop.resolve_job_offers()
        self.pop.resolve_marriage_market()
        self.labour_market.update_growth_coefs()
        self.pop.update_social_security()
        self.notify_stats_collector()

        # logging --------------------------------
        # TODO: logging frequency should depend on step size
        # or perhaps have seperate parameter.
        logging.info("date = {}".format(self.timestepper.date.isoformat()))
        logging.info("population size = {}".format(self.pop.pop_size))

        self.timestepper.step_forward()

    def notify_stats_collector(self):
        self.stats.pad_event_counters(self.timestepper.date)
        self.stats.record_stats(self.pop, self.timestepper.date)
        self.stats.record_stats(self.labour_market, self.timestepper.date)

    def run_sim(self, sim_length):
        """
        run a simulation for sim_length TIMESTEPS.
        note that these are not necessary co-terminous with
        years.
        """
        current_year = copy.deepcopy(self.timestepper.start_date.year)
        for step in range(sim_length):
            self.time_step()
            if ((self.timestepper.date.year > current_year) and
                    (self.timestepper.date.year % 10 == 0)):
                print (self.timestepper.date.year)
                current_year = self.timestepper.date.year

    def get_labour_market(self):
        return self.labour_market












