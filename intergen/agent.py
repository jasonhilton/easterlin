"""
This module defines class representing agents in demographic simulation
These agents have methods describing how they make decisions about fertility,
as well as those relating to their mortality and nuptiality
and their social network behaviour
"""
from __future__ import division
import random as rnd
from math import exp
import logging
import datetime


from .utils import calculate_age_years, gompertz_mortality_fact
from .fertility import get_fertility
from .employment import Employment


logger = logging.getLogger("intergen")


class Agent(object):
    """
    Genderless agent class
    contains methods and attributes shared by male and female agents
    """
    __slots__ = ["params", "stats", "timestepper", "partner", "mother",
                 "age_years", "DOB", "age", "marriage_market",
                 "age_at_marriage", "employment", "in_marriage_market",
                 "gp_start", "gompertz", "experience", "skill", "aspiration",
                 "ident","imprinted"]

    def __init__(self, params, attributes, timestepper, stats):

        """
        Initialise agent using params and attributes
        """
        self.params = params
        self.stats = stats

        #for key, value in attributes.items():
        #    self.__setattr__(key, value)
        self.age = attributes["age"]
        self.DOB = attributes["DOB"]
        self.ident = attributes["ident"]
        self.aspiration = attributes["aspiration"]
        self.experience = attributes["experience"]
        self.skill = attributes["skill"]


        self.timestepper = timestepper

        self.age_years = calculate_age_years(self.DOB, timestepper.date)

        self.partner = None
        self.mother = None

        self.imprinted = False

        self.marriage_market = None
        self.age_at_marriage = None
        self.in_marriage_market = False

        self.employment = Employment(self, params)

        # could we include these as static variables that are changed
        # by 'simulation'
        # maybe we would want to include heterogeneity.
        a = self.params["gompertz_a"]
        b = self.params["gompertz_b"]
        l = self.params["gompertz_l"]
        self.gp_start = self.params["gompertz_start"]
        self.gompertz = gompertz_mortality_fact(a, b, l,
                                                self.gp_start)

        logger.debug("event:initialisation,date:{},agent:{},age:{},experience:{}".format(
                                timestepper.date,self.ident, self.age_years, self.experience))

    

    # timestep functions ----------------------------------------------

    def step_activity(self, sim):
        """
        main method for doing stuff that an agent does every year
        to be extended by child methods
        """
        self.age_on(sim.pop)

    def age_on(self, pop):
        """
        increase agent age
        """
        timestep_length = self.timestepper.get_timestep_length()
        self.age += timestep_length
        self.age_years = calculate_age_years(self.DOB, self.timestepper.date)


        if self.age_years >= self.params["imprinting_time"] and not self.imprinted:
            self.aspiration = self.determine_aspiration(pop)

        if self.employment.job:
            self.experience += timestep_length

        if self.age_years >= self.params["retirement_age"] and self.employment.have_job():
            self.employment.job.retire()

        if self.age_years > 16 and not self.have_partner():
            self.find_partner(pop)

    def get_marriage_market(self, pop):
        pass

    # labour market functions ------------------------------------------

    def determine_aspiration(self, pop):
        """
        determine a threshold for satisfaction with life
        """
        if self.age_years > self.params["imprinting_time"] and self.aspiration:
            return self.aspiration
        try:
            aspiration = self.mother.partner.employment.get_wage(pop)
            self.imprinted = True
            logger.debug("event:aspiration_imprinted,date:{},agent:{},aspiration:{}"
                          "".format(self.timestepper.date,
                                    self.ident,
                                    aspiration))
        except AttributeError:
            aspiration = self.params["social_security_level"]
            self.imprinted = True
            logger.debug("event:aspiration_imputed,date:{},agent:{},"
                          "aspiration:{}".format(self.timestepper.date, 
                                            self.ident,
                                            aspiration))
        return aspiration

    def demand_contribution(self):
        """
        Assumption based contribution to demand, plays a part in determining
        the number of jobs required in economy
        """
        # TODO in future could use income to determine demand.
        if self.age_years < 16:
            return 0.5
        elif self.age_years < 25:
            return 0.8
        elif self.age_years > 65:
            return 0.8
        else:
            return 1.0

    # nuptiality functions ----------------------------------------------

    def have_partner(self):
        return self.partner is not None


    def find_partner(self, pop):
        """
        find a partner
        """
        if self.in_marriage_market:
            return
        a = self.params["partnering_a"]
        alpha = self.params["partnering_alpha"]
        mu = self.params["partnering_mu"]
        # avoid using the keyword lambda
        lambda_p = self.params["partnering_lambda"]
        # correct for timestep length
        mult = self.timestepper.get_timestep_days() / self.params["year_length"]
        if rnd.random() < mult * a * exp(-alpha * (self.age_years - mu) -
                                         exp(- lambda_p * (self.age_years - mu))):
            self.marriage_market = self.get_marriage_market(pop)
            self.marriage_market.append(self)
            self.in_marriage_market = True

    # network functions --------------------------------------
    def define_network(self):
        """
        define network partners
        """
        pass

    # mortality ------------------------------------------
    def check_survival(self):
        """
        Check to see if I survive the timestep
        Return self so that I can be removed from various lists
        """
        if self.age_years <= self.gp_start:
            return
        mort_rn = rnd.random()
        mult = self.timestepper.get_timestep_length().days / self.params["year_length"]
        if mort_rn < self.gompertz(self.age_years) * mult:
            return self

    def die(self, pop):
        """
        remove agent from simulation
        keep this method in agent in order to remove family pointers
        """
        pop.poplist.remove(self)
        pop.pop_size -= 1
        logger.debug("event:death,date:{},agent:{},age:{}".format(self.timestepper.date,
                                                           self.ident,
                                                           self.age_years))
        if self.employment.have_job():
            self.employment.job.retire()


class Male(Agent):
    """
    subclass of agent corresponding to male agents
    """
    __slots__=()
    def __init__(self, params, attributes, timestepper, stats):
        Agent.__init__(self, params, attributes, timestepper, stats)


    def step_activity(self, sim):
        super(Male, self).step_activity(sim)
        if self.params["log_wages"] and self.employment.have_job():
            wage = self.employment.get_wage(sim.pop)
            logger.debug("event:wage,date:{},agent:{},age:{},wage:{},skill:{},"
                     "experience:{}".format(self.timestepper.date,
                                            self.ident,
                                            self.age_years,
                                            wage,
                                            self.skill,
                                            self.experience))

    @property
    def isfemale(self):
        return False

    def get_marriage_market(self, pop):
        """
        Return the correct marriage_market for men
        """
        # should this function go elsewhere
        # ie should it be function of sim/pop
        return pop.marriage_market_males




class Female(Agent):
    """
    subclass of agent corresponding to female agents
    """
    __slots__ = ["fertility", "children"]
    def __init__(self, params, attributes, timestepper, stats):
        Agent.__init__(self, params, attributes, timestepper, stats)

        self.fertility = get_fertility(params, self)
        self.children = []


    @property
    def isfemale(self):
        return True

    def step_activity(self, sim):
        super(Female, self).step_activity(sim)
        if self.age_years > 15 and self.age_years < 49:
            self.fertility.reproductive_behaviour(sim.pop)


    def notify_statistics_collector(self, type_of_event):
        self.stats.record_event(self, type_of_event, self.timestepper.date)

    

    # economic functions ------------------------------------------------

    
    def eligible_for_market(self):
        """
        Placeholder untill more complicated function defined
        """
        return False

    def participate_in_market(self):
        """
        Decide whether to attempt to find a job
        To be extended
        """
        return False

    def apply_for_jobs(self):
        """
        make some applications for vacant jobs.
        """
        # TODO: Women's propensity to work
        pass

    def get_marriage_market(self, pop):
        """
        Return the correct marriage_market for women
        """
        return pop.marriage_market_females


def gompertz_mortality_fact(a, b, l, start):
    """
    construct gompertz mortality function
    to determine probability of dying at any given age
    """
    def gompertz(age):
        """
        return probability of dying at age x
        """
        # TODO This should also change dependent on the size of timestep
        return l + a*exp(b*(age-start))
    return gompertz
