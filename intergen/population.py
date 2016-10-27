"""
Class representing populations of agents
"""
from __future__ import division
import random as rnd
from math import exp
from collections import Counter

import logging

import numpy.random as nprnd
import numpy as np

from .agent import Male, Female

from .utils import gompertz_mortality_fact

class BasePopulation(object):
    """
    Base Population class for testing

    """
    def __init__(self, poplist):
        self.poplist = poplist
        self.pop_size = len(poplist)


class Population(BasePopulation):
    """
    population of agents
    """
    def __init__(self, params, sim, agent_factory):
        """
        Class holding individual agents
        """
        self.params = params
        self.sim = sim
        self.agent_factory = agent_factory

        self.marriage_market_males = []
        self.marriage_market_females = []

        self.initial_pop_size = params["pop_size"]
        self.pop_size = self.initial_pop_size

        self.poplist = [agent_factory.make_initial_agent()
                        for _ in range(self.initial_pop_size)]

        self.relative_cohort_size_m = None
        self.relative_cohort_size_f = None

        self.benefit_level = self.params["social_security_level"]
    #  setup functions --------------------------------------------

    def setup_cohort_sizes(self):
        """
        creat timeseries of past births and calculate initial relative cohort sizes
        """
        # Need record of past births - construct this from current population
        # and mortality.
        #if self.params["fertility_type"] in {"simple", "married", "partner"}:
            # Do child classes definitely inherit changes in parent class atts?
        self.female_birth_ts = self.construct_birth_ts(Female)
        self.male_birth_ts = self.construct_birth_ts(Male)
        year = self.poplist[1].timestepper.date.year
        self.relative_cohort_size_m = self.calc_relative_cohort_sizes(year, "Male")
        self.relative_cohort_size_f = self.calc_relative_cohort_sizes(year, "Female")


    def do_partnership_setup(self):
        """
        setup initial population so that most women have partner,
        and women have a roughly sensible distribution of children
        chosen from the distribution in the sample
        """
        males = [agent for agent in self.poplist
                 if partnerable(agent) and isinstance(agent, Male)]
        females = [agent for agent in self.poplist
                   if partnerable(agent) and isinstance(agent, Female)]
        children = [agent for agent in self.poplist if not partnerable(agent)]

        for female in females:
            if rnd.random() < self.setup_marriage_dist(female.age_years) \
                        and males:
                p_i = self.pick_partner(female, males)
                self.partner_agents(males[p_i], female)
                del males[p_i]

        logging.debug("Completed partnering...")

        # TODO: Should this go somewhere else? In fertility?
        self.assign_children(children,
                             [female for female in females
                              if female.partner and female.age_years < 55])

    def construct_birth_ts(self, sex):
        """
        Aims to construct an approximation to the historical birth time series
        at startup, by inflating current agents by inverse of survivorship.
        """
        birth_ts = Counter()
        gomp = self.get_gompertz()
        ages = np.arange(100)
        inflators = 1/np.cumprod([1-gomp(age) for age in ages])
        for agent in self.poplist:
            if isinstance(agent, sex):
                birth_ts[agent.DOB.year] += 1 * inflators[agent.age_years]
        return birth_ts

    def get_gompertz(self):
        a = self.params["gompertz_a"]
        b = self.params["gompertz_b"]
        l = self.params["gompertz_l"]
        gp_start = self.params["gompertz_start"]
        return gompertz_mortality_fact(a, b, l, gp_start)

    def setup_marriage_dist(self, age):
        """
        Use cloglog function to describe cumulative distribution of agents
        married by age at setup.
        """
        a = self.params["setup_marriage_age_a"]
        b = self.params["setup_marriage_age_b"]
        mid = self.params["setup_marriage_age_mid"]
        return 1 - exp(- exp(a + b * (age - mid)))

    def assign_children(self, children, females):
        """
        Assign children to mother for setup.
        difficult, as need to respect possible age and parity distributions
        """
        logging.debug("Assigning {} children"
                      "to {} mothers".format(len(children), len(females)))
        childno = 1
        prospective_mothers = [ma for ma in females
                               if ma.fertility.check_family_formation(self)]
        for child in children:
            check_not_forever = 0
            while not child.mother and check_not_forever < 20:
                self.pick_mother(child, prospective_mothers)
                check_not_forever += 1

            logging.debug("Assigning child {} of {} children".format(childno,
                                                               len(children)))
            if check_not_forever == 20:
                logging.debug("Child {} not assigned ".format(childno))
            childno += 1

    def pick_mother(self, child, females):
        """
        assign a child to a mother based weighting function matching_children
        """
        try:
            num_choices = min(len(females), 10)
            prospective_mothers = rnd.sample(females, num_choices)
        except ValueError:
            return
        logging.debug("choosing from {}"
                      " prospective_mothers".format(len(prospective_mothers)))
        weights = [self.matching_children(child, prosp_mo) for prosp_mo
                   in prospective_mothers]
        if not sum(weights) > 0:
            logging.debug("No suitable mothers")
            return
        probs = [weight / sum(weights) for weight in weights]
        mother = nprnd.choice(prospective_mothers, 1, p=probs)[0]
        mother.fertility.parity += 1
        if not mother.children:
            mother.fertility.date_of_last_birth = child.DOB
        else:
            most_recent_other_birth = max([other_child.DOB for other_child in mother.children])
            mother.fertility.date_of_last_birth = max(most_recent_other_birth, child.DOB)
        #logging.debug("mother-child match, partners_wage {}".format(mother.partner.employment.get_wage()))
        mother.children.append(child)
        child.mother = mother

    def matching_children(self, child, female):
        """
        give probablity weight of female being mother to child in the initial
        population. arbitrary.
        """
        age_at_birth = female.age_years - child.age_years
        logging.debug("Prospective mother's age at birth"
                      " = {}".format(age_at_birth))

        if age_at_birth < 17 or age_at_birth > 45:
            weight = 0
        elif female.fertility.parity > 5:
            weight = 0
        elif not female.fertility.check_family_formation(self):
            weight = 0
        elif age_at_birth > 22 and age_at_birth < 32:
            weight = 1
        else:
            weight = 0.2
        if female.fertility.parity > 1:
            weight = weight / female.fertility.parity
        return weight

    # timestep functions -----------------------------------------------

    def update(self, sim):
        """
        update all agents as part of a timestep
        includes anything defined in the step activity method (e.g. fertility)
        And additionally mortality
        """
        # could just shuffle the poplist directly. might be slightly quicker.
        # range in python 3 is an iterator
        indexes = list(range(len(self.poplist)))
        nprnd.shuffle(indexes)
        for i in indexes:
            self.poplist[i].step_activity(sim)

        deaths = [self.check_survival_pop(i) for i in indexes]
        for death in deaths:
            if death:
                death.die(self)
        year = sim.timestepper.date.year
        self.relative_cohort_size_m = self.calc_relative_cohort_sizes(year, "Male")
        self.relative_cohort_size_f = self.calc_relative_cohort_sizes(year, "Female")
        # if self.params["fertility_type"] == "simple_fertility":
        #     # possiblity to restrict to males, the employed etc
        #     self.female_age_dist = get_age_distribution(self)

    # economic functions ------------------------------------------------

    def do_applications(self, sim):
        for agent in self.poplist:
            agent.employment.activity(sim)

    def update_social_security(self):
        
        wages = [agent.employment.wage for agent in self.poplist 
                 if agent.employment.have_job()]
        try:
            min_wage = min(wages)
        except ValueError:
            if not wages:
                min_wage = 0
            else:
                raise ValueError("Noticed somethings not right while trying to"
                                  "uprate benefit level.")
        self.benefit_level = max(self.benefit_level, min_wage)
        #mult = exp(self.params["growth_rate"])
        #addit  = self.params["linear_growth"]
        #self.benefit_level *= mult
        #self.benefit_level += addit * 0.8

    def check_survival_pop(self, index):
        """
        check if the agent referred to by index survives the time period
        """
        return self.poplist[index].check_survival()

    def derive_demand(self):
        """
        sum the demand contribution of all agents
        """
        return sum(agent.demand_contribution() for agent in self.poplist)

    def skill_distribution(self):
        """
        Distribution of skills in the population;
        A normal distribution is used.
        """
        return min(max(0.01, rnd.normalvariate(0.5, 0.2)), 1)

    def get_lab_force_size(self):
        # may depend on women work status
        return sum(agent.employment.eligible_for_market() for agent in
                   self.poplist)

    def resolve_job_offers(self):
        """
        Each agent examines their offers, and takes a job if relevant
        """
        for agent in self.poplist:
            agent.employment.assess_offers(self)

    # demographic functions ---------------------------------------------

    def add_child(self, child):
        """
        Add a new-born to the list of agent
        """
        self.poplist.append(child)
        self.pop_size += 1

    def pick_partner(self, female, malelist):
        """
        pick the most suitable partner for female from malelist,
        by social distance criteria
        return index of position of partner in malelist
        """
        no_indexes = min(len(malelist), 5)
        indexes = rnd.sample(range(len(malelist)), no_indexes)
        suitabilities = [{"value": self.matching_mate(female, malelist[index]),
                          "index": index} for index in indexes]
        # the lowest 'distance'
        suitabilities.sort(key=lambda x: x["value"])
        partner_i = suitabilities[0]["index"]
        return partner_i

    def resolve_marriage_market(self):
        """
        For those scheduled to become married, record age of marriage
        """
        # should include threshold ? - but probabilistic stuff is taken care of
        # by the hazard for marriage
        still_in_market = []
        for female in self.marriage_market_females:
            # fifo queuing for females
            if self.marriage_market_males:
                p_i = self.pick_partner(female, self.marriage_market_males)
                self.partner_agents(female, self.marriage_market_males[p_i])
                del self.marriage_market_males[p_i]
            else:
                still_in_market.append(female)
        self.marriage_market_females[:] = still_in_market

    def matching_mate(self, female, male):
        age_diff = abs(male.age_years - female.age_years -
                       self.params["partner_age_diff"])
        skill_diff = abs(male.skill - female.skill)
        # 50 determines the relative weighting between skill and age
        # but doesn't effect age-based choices (atm)
        return skill_diff + (age_diff ** 2) / 50

    def partner_agents(self, male, female):
        """
        Ensure we can identify the relationship between male and female
        """
        # TODO move this to agent level.
        female.partner = male
        male.partner = female
        female.age_at_marriage = female.age_years
        male.age_at_marriage = male.age_years

    def calc_relative_cohort_sizes(self, year, sex):
        """
        Calculate the relative sizes of all birth cohorts currently of working 
        age. Note that the size at birth is used, not the current size. 
        """
        ages = np.arange(15, 70)
        birth_years = year - ages
        if sex == "Female":
            counts = np.array([self.female_birth_ts[year] for year
                               in birth_years])
        elif sex =="Male":
            counts = np.array([self.male_birth_ts[year] for year
                               in birth_years])
        else:
            raise ValueError("sex must be 'Male' or 'Female'")
        relative_size = counts / np.mean(counts)
        # relative_size[birth_years < self.agent.timestepper.start_date.year] = 1
        return 1 - relative_size

    def get_relative_cohort_sizes(self, sex):
        if sex == "Female":
            return self.relative_cohort_size_f
        elif sex =="Male":
            return self.relative_cohort_size_m
        else:
            raise ValueError("sex must be 'Male' or 'Female'")


def age_at_first_birth(mother):
    return mother.age_years - mother.children[0].age_years


def partnerable(agent):
    """
    examine if the agent is able to form a partnership
    """
    return agent.age_years > 16 and not agent.partner
