from __future__ import division
import random as rnd
from math import exp

import logging
import numpy as np


logger = logging.getLogger("intergen")

class Job(object):
    """
    Class representing a job object
    """
    def __init__(self, labour_market, params):
        """
        New job object, with a specific difficulty level
        """
        self.occupant = None
        self.market = labour_market  # instance of labour market class.
        self.params = params
        self.difficulty = rnd.random() * self.market.difficulty_bound()
        self.applicants = []
        if params["experience_floor"]:
            self.experience_floor = (max(0, rnd.uniform(-15, params["exp_max"]) *
             self.params["year_length"]))
        self.working_ages = np.arange(15, 70)

    def make_redundant(self):
        """
        Remove job given that it is no longer required
        """
        if self.occupant:
            self.occupant.job = None
            self.occupant = None
        else:
            self.market.vacancies.remove(self)
        self.market.joblist.remove(self)

    def retire(self):
        """
        Agent occupying this job has retired or resigned
        Make the job open to new applicants
        """
        self.occupant.job = None
        self.occupant = None
        self.market.vacancies.append(self)

    def update_wage(self, pop):
        if not self.occupant:
            return
        else:
            self.occupant.wage = self.calc_wage(self.occupant, pop)

    def calc_wage(self, employee, pop):
        prod = self.get_prod(employee)
        mult = self.get_multiplier(employee)
        wage = prod * mult
        return wage
        #return max(wage, pop.benefit_level * (1 + rnd.random() * 0.05))

    # def get_multiplier(self, employee, pop):
    def get_multiplier(self, employee):
        # cohort_sizes = pop.get_relative_cohort_sizes("Male")
        # feedback = self.calc_feedback(employee, cohort_sizes)
        feedback = self.get_feedback(employee)
        mult = np.exp(feedback * self.params["wage_feedback_mult"])
        return mult

    def get_feedback(self, employee):
        feedback = self.market.get_feedback(employee.agent.age_years)
        return feedback

    # def calc_feedback(self, employee, relative_sizes):
    #     """
    #     Calculate the feedback coefficient on fertility, as determined by
    #     relative cohort size.
    #     Use gaussian weights centred on agent's age to determine contribution
    #     of each age group to cohort.
    #     """
    #     # determines the 'variance' of the gaussian kernel
    #     cohort_width = self.params["cohort_width"]
    #     var = (cohort_width / 2) ** 2

    #     birth_years = self.market.timestepper.date.year - self.working_ages
    #     weights = np.exp(- (1 / var) *
    #                      (birth_years - employee.agent.DOB.year) ** 2)

    #     # we want feedback coefficients that are negative for big cohorts
    #     # but positive for larger cohorts.
    #     feedback = (1 / np.sum(weights)) * relative_sizes.dot(weights)
    #     if feedback == np.inf:
    #         print("weights = {}, year_diff = {}, dob = {}"
    #               "".format(weights, birth_years - employee.agent.DOB.year,
    #                         employee.agent.DOB.year))
    #         raise ValueError("Wages must not be infinity")

    #     logger.debug("event:feedback,date:{},agent:{},age:{},feedback:{},skill:{},"
    #                  "experience:{}".format(self.market.timestepper.date,
    #                                         employee.agent.ident,
    #                                         employee.agent.age_years,
    #                                         feedback,
    #                                         employee.agent.skill,
    #                                         employee.agent.experience))
    #     return feedback

    def get_prod(self, employee):
        """
        calculate the wage of a prospective or current employee
        """
        prod = self.market.prod_function(employee.agent.experience,
                                         employee.agent.skill,
                                         self.difficulty)
        mult = self.market.growth_mult
        add = self.market.additive_growth
        return prod * mult + add

    def offer_job(self, pop):
        """
        assess applicant and offer to employ someone
        """
        assert not self.occupant
        if self.params["experience_floor"]:
            self.applicants = [app for app in self.applicants if
                               app.agent.experience.days >= self.experience_floor]
        if not self.applicants:
            return False
        result = self._pick_winner(pop, self.applicants)
        try:
            # if the was a suitable candidate then we should get out 
            # an index and a wage
            ind, wage = result
        except TypeError:
            # if this doesnt work then the below should
            self.applicants = []
            return False
        winner = self.applicants[ind]
        offer = {"job": self, "wage": wage}
        winner.offers.append(offer)
        self.applicants = []
        return True

    def _pick_winner(self, pop, apps):
        # tidy up - this is ugly and repetitive.
        wages = [self.calc_wage(app, pop) for app in apps]
        if self.params["app_criteria"] == "wage":
            wage = max(wages)
            if wage < 0:
                return False
            ind = wages.index(wage)
            return ind, wage
        elif self.params["app_criteria"] == "prod":
            prods = [self.get_prod(app) for app in apps]
            prod = max(prods)
            if prod < 0:
                return False
            ind = prods.index(prod)
            wage = wages[ind]
            return ind, wage
        elif self.params["app_criteria"] == "profit":
            profs = [self.get_prod(app) - wage
                     for app, wage in zip(apps, wages)]
            prof = max(profs)
            ind = profs.index(prof)
            return ind, wages[ind]
        else:
            raise NotImplemented("dont recognise app_criteria")

    def fill_job(self, applicant):
        """
        Applicant has accepted a job offer
        Remove self from vacancies list
        """
        assert applicant.agent.age_years > 14
        self.occupant = applicant
        self.market.vacancies.remove(self)

    def occupied(self):
        """
        check if there's some one in the job
        """
        if self.occupant:
            return True
        else:
            return False