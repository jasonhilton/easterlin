from __future__ import division
import random as rnd
from math import exp

import logging
import numpy as np

from .job import Job


logger = logging.getLogger("intergen")

# NB: at present the productivity function is added at runtime by the
# simulation class. This is a bit of hack and needs revising.


class LabourMarket(object):
    """
    class controling the labourmarket behaviour of the population
    maintain a number of jobs depending on the size of the population
    """

    def __init__(self, params, num_jobs, timestepper):
        self.params = params

        self.joblist = [Job(self, params) for _ in range(num_jobs)]
        # we want a list of vacant jobs, which initially is all of them
        self.vacancies = [job for job in self.joblist]

        self.new_vacancies = []

        self.job_count = []

        self.timestepper = timestepper
        self.growth_mult = 1.0
        self.additive_growth = 0.0

        self.feedback_coefs = []
        self.working_ages = np.arange(15, 70)

        # the below will work only if you ignore the first arg.
        # it is an object that happens to be a function,
        # rather than a method
        # so the first arg in self.prod_function(*args) WONT be the instance
        # (I think)
        # self.prod_function = get_productivity_function(params)

    def update_feedbacks(self, relative_sizes):

        working_birth_years = self.timestepper.date.year - self.working_ages
        
        feedbacks = [self._update_feedback_single(year, relative_sizes,
                     working_birth_years) for year in working_birth_years]
        # we want feedback coefficients that are negative for big cohorts
        # but positive for larger cohorts.
        self.feedback_coefs = feedbacks

    def _update_feedback_single(self, year, relative_sizes, working_birth_years):        
        cohort_width = self.params["cohort_width"]
        var = (cohort_width / 2) ** 2
        weights = np.exp(- (1 / var) *
                         (working_birth_years - year) ** 2)
        feedback = (1 / np.sum(weights)) * relative_sizes.dot(weights)
        return feedback


    def update_jobs(self, pop):
        """
        Change number of jobs in the market based upon the size of the
        population.
        """        
        con_demand = pop.derive_demand()
        lab_demand = self.labour_demand(con_demand)
        adjustment = lab_demand - len(self.joblist)        
        if adjustment <= -1:
            self.shed_jobs(abs(adjustment))
        # to keep population down, only add jobs below a certain amount.
        elif adjustment >= 1 and \
                    len(self.joblist) < self.params["job_upper_limit"]:
            self.add_jobs(adjustment)

        mult = (self.timestepper.get_timestep_days() /
                self.params["year_length"])
        churn = int(round(mult * self.params["churn"] * len(self.joblist)))
        if churn:
            self.shed_jobs(min(churn, len(self.joblist)))
            self.add_jobs(churn)

        self.update_feedbacks(pop.get_relative_cohort_sizes("Male"))
        for job in self.joblist:
            job.update_wage(pop)

        logging.info("time = {}, number of jobs = {}".format(self.timestepper.date,
                                                             len(self.joblist)))

    def update_growth_coefs(self):
        self.growth_mult *= exp(self.params["growth_rate"])
        self.additive_growth += self.params["linear_growth"]

    def consumption(self):
        """
        total consumption
        Here assumed to equal wages paid
        """
        return sum(self.get_wage_distribution())

    def labour_demand(self, con_demand):
        """
        Work out how many jobs are required given consumption
        """
        return int(con_demand / self.params["support_ratio"])

    def shed_jobs(self, adjustment):
        """
        remove jobs to adjust to changing size of the economy
        """
        # could use first in last out, lowest experience,
        # or some other criterion of choice here
        # or high wage, close to retirement

        [job.make_redundant() for job in
         rnd.sample(self.joblist, adjustment)]

    def add_jobs(self, adjustment):
        """
        add jobs to adjust to changing size of economy
        """
        new_jobs = [Job(self, self.params) for _ in range(adjustment)]
        self.joblist.extend(new_jobs)
        self.vacancies.extend(new_jobs)

    def expected_job_value(self):
        """
        Calculate what it is expected that a new job might produce
        Used to determine how many new jobs are required
        given the current state of demand
        """
        expected_difficulty = self.difficulty_bound()/2.0
        expected_skill = 0.5  # can we make this more sensible?
        expected_experience = 20
        expected_job_value = self.prod_function(expected_experience,
                                                expected_skill,
                                                expected_difficulty)
        return expected_job_value

    def difficulty_bound(self):
        """
        determine what the upper bound on job complexity might
        determined by Cahuc et al's exposition of matching and technology
        model.
        It may be that this is dependent on time,
        if we are interested in the effect of improving technology
        """
        alpha = self.params["wage_alpha"]
        beta = self.params["wage_beta"]
        return alpha * beta / (1 + beta)

    # DEPRECATED: now initialised at runtime dependent on aparameters 
    # def prod_function(self, difficulty, skill, experience):
    #     """
    #     determine the wage of job employee based on their skill and experience
    #     """
    #     alpha = self.params["wage_alpha"]
    #     beta = self.params["wage_beta"]
    #     gamma = self.params["wage_gamma"]
    #     delta = self.params["wage_delta"]
    #     experience_years = experience.days // self.params["year_length"]

    #     prod = (difficulty ** beta *   # technology contribution
    #             exp((alpha * skill - difficulty) +  # productivity contribution
    #                 skill + gamma * experience_years -
    #                 delta * experience_years**2))  # experience contribution
    #     return prod

    def send_offers(self, pop):
        """
        Process applications to each job, and send offers as appropriate
        """
        for job in self.vacancies:
            job.offer_job(pop)

    def process_new_vacancies(self):
        """
        simple function to avoid changing list while iterating
        """
        self.vacancies.extend(self.new_vacancies)
        self.new_vacancies = []

    def get_feedback(self, age_years):
        #return self.feedback_coefs[np.where(self.working_ages == age_years)[0][0]]
        return self.feedback_coefs[age_years - 15]



