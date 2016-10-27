"""

"""
from __future__ import division
import logging
from collections import Counter

# do this by composition. i.e. pick one of these functions to be the interface
# for agent.
import random as rnd

from .agent import calculate_age_years
from math import exp, log
import numpy as np
from scipy.stats import norm

# from abc import abstractmethod

logger = logging.getLogger("intergen")


class BaseFertility(object):
    __slots__=["params", "agent", "date_of_last_birth", "parity"]
    def __init__(self, params, agent):
        self.params = params
        self.agent = agent
        self.date_of_last_birth = None
        self.parity = 0

    def reproductive_behaviour(self):
        """
        To be implemented by child classes
        Provides circumstances under which to call give birth method
        """

    def give_birth(self, pop):
        """
        """
        child = pop.agent_factory.make_new_born()
        self.parity += 1
        self.agent.children.append(child)
        pop.add_child(child)
        child.mother = self.agent
        self.date_of_last_birth = self.agent.timestepper.date
        logger.debug("event:birth,date:{},agent:{},"
                     "parity:{},child:{},female:{}"
                     "".format(self.agent.timestepper.date,
                               self.agent.ident,
                               self.parity,
                               child.ident,
                               child.isfemale))

        self.agent.notify_statistics_collector("birth")
        if self.parity == 1:
            self.agent.notify_statistics_collector("first_birth")
        if child.isfemale:
            pop.female_birth_ts[child.DOB.year] += 1
        else:
            pop.male_birth_ts[child.DOB.year] += 1 


class EasterlinFertility(BaseFertility):
    __slots__ = ["sub_fert", "fecundity"]
    def __init__(self, params, agent):
        self.params = params
        self.agent = agent
        self.date_of_last_birth = None
        self.parity = 0
        self.sub_fert = subsequent_fertility(params["further_fertility_a"],
                                             params["further_fertility_b"],
                                             params["further_fertility_mu"])
        self.fecundity = get_fecundity_func(params["fecundity_a"],
                                            params["fecundity_b"],
                                            params["fecundity_c"],
                                            params["fecundity_mu"])

    def reproductive_behaviour(self, pop):
        """
    
        """
        birth_flag = False
        if not self.agent.have_partner():
            return
        if self.parity == 0:
            birth_flag = self.check_family_formation(pop)
        else:
            birth_flag = self.check_subsequent_births(pop)
        fec = self.fecundity(self.agent.age_years)
        if birth_flag and rnd.random() < fec:
            self.give_birth(pop)

    def give_birth(self, pop):
        """
        """
        super(EasterlinFertility, self).give_birth(pop)

        child = self.agent.children[-1]
        if self.params["inheritance"] and self.agent.partner:
            k = self.params["inheritance_corr"]
            m = (self.agent.skill + self.agent.partner.skill) / 2.0
            child.skill = norm.cdf(np.random.normal(k * norm.ppf(m), 1 - k ** 2))
            #child.skill = (self.agent.skill + self.agent.partner.skill) / 2.0

        # if child.isfemale():
        #     EasterlinFertility.birth_ts[child.DOB.year] += 1

    def check_family_formation(self, pop):
        """
        """
        wage = self.agent.partner.employment.get_wage(pop)
        threshold = self.wage_threshold()
        logging.debug("checking family formation: wage = {:2f},"
                      "threshold = {:2f}".format(wage, threshold))

        # if self.agent.timestepper.time_since_start().days / 365.0 < 4:
        #     if rnd.random() > 0.3:
        #         # attempt to correct for heaping of births in first year.
        #         return False
        if wage > threshold * (1 - self.params["aspiration_offset"]):
            return True

    def wage_threshold(self):
        """
        the amount this agent's household must earn before she decides to start
        a family
        """
        weight = self.params["female_weight_in_threshold"]
        return (self.agent.aspiration * weight +
                self.agent.partner.aspiration * (1 - weight))

    def check_subsequent_births(self, pop):
        """
        For women who have already started a family
        examined based on current state whether  further children are desired
        / scheduled
        """
        time_since_last_birth = calculate_age_years(self.date_of_last_birth,
                                                    self.agent.timestepper.date)
        if time_since_last_birth < 1:
            return False
        mult = (self.agent.timestepper.get_timestep_days() /
                self.params["year_length"])
        prob_of_birth = (self.sub_fert(time_since_last_birth) *
                         (mult / self.parity))
        if rnd.random() < prob_of_birth and self.check_family_formation(pop):
            return True
        else:
            return False


def subsequent_fertility(a, b, mu):
    # Note, timestep size and age dependence is handled in the calling function.
    def sub(duration):
        return a * exp(-b*(duration - mu)**2)
    return sub


class SimpleFertility(BaseFertility):
    working_ages = np.arange(15, 70)

    def __init__(self, params, agent):
        self.params = params
        self.agent = agent
        self.date_of_last_birth = None
        self.parity = 0


    def reproductive_behaviour(self, pop):
        # make fertility depend on weighted cohort size
        #
        """
        Check for births based on simple macro-formulation of Easterlin Effect
        """
        feedback_coef = self.calc_feedback(pop)
        base_fertility = self.base_fertility()
        # prob_birth = base_fertility * (1 + feedback_coef * 
        #                                self.params["feedback_mult"])
        prob_birth = base_fertility * np.exp(feedback_coef * 
                                        self.params["feedback_mult"])
        rn = rnd.random()
        if rn < prob_birth:
            self.give_birth(pop)

    def calc_feedback(self, pop):
        """
        Calculate the feedback coefficient on fertility,
        as determined by relative cohort size.
        Use gaussian weights centred on agent's age
        to determine contribution of each age group to cohort.
        """

        # relative to average birth cohort size of adults over the period. 
        relative_sizes = pop.get_relative_cohort_sizes("Female")
        # determins the 'variance' of the gaussian kernel
        cohort_width = self.params["cohort_width"]
        var = (cohort_width / 2) ** 2

        birth_years = self.agent.timestepper.date.year - self.working_ages
        weights = np.exp(- (1 / var) * (birth_years - self.agent.DOB.year)**2)

        # we want feedback coefficients that are negative for big cohorts
        # but positive for larger cohorts.
        feedback = (1/sum(weights)) * relative_sizes.dot(weights)
        return feedback

    def give_birth(self, pop):
        """
        Give birth, adding to yearly count in class variable
        """
        super(SimpleFertility, self).give_birth(pop)
        child = self.agent.children[-1]

        if child.isfemale:
            pop.female_birth_ts[child.DOB.year] += 1
        else:
            pop.male_birth_ts[child.DOB.year] += 1 

    def base_fertility(self):
        """
        """
        mult = (self.agent.timestepper.get_timestep_days() /
                self.params["year_length"])
        a = self.params["base_fertility_a"]
        b = self.params["base_fertility_b"]
        c = self.params["base_fertility_c"]
        return hadwiger_fertility(self.agent.age_years, a, b, c) * mult

    def check_family_formation(self, pop):
        """
        Under this fertility regime, everyone with a partner may form a familiy
        """
        # This is need for population setup. It is not required for actually
        # determining family formation. Note that checks for partners are
        # carried out by the calling function.
        return True


class MarriedFertility(SimpleFertility):
    def __init__(self, params, agent):
        super(MarriedFertility, self).__init__(params, agent)

    def reproductive_behaviour(self, pop):
        if self.agent.have_partner():
            super(MarriedFertility, self).reproductive_behaviour(pop)


class PartnerFertility(SimpleFertility):
    def __init__(self, params, agent):
        super(PartnerFertility, self).__init__(params, agent)

    def reproductive_behaviour(self, pop):
        if self.agent.have_partner():
            super(PartnerFertility, self).reproductive_behaviour(pop)

    def calc_feedback(self, pop):
        """
        Calculate the feedback coefficient on fertility,
        as determined by relative cohort size.
        Use gaussian weights centred on agent's age to determine
        contribution of each age group to cohort.
        """
        # relative to average birth cohort size of adults over the period.
        relative_sizes = pop.get_relative_cohort_sizes("Male")
        # determins the 'variance' of the gaussian kernel
        cohort_width = self.params["cohort_width"]
        var = (cohort_width / 2)**2
        ages = np.arange(15, 70)
        birth_years = self.agent.timestepper.date.year - ages
        weights = np.exp(- (1 / var) *
                         (birth_years - self.agent.partner.DOB.year)**2)

        # we want feedback coefficients that are negative for big cohorts
        # but positive for larger cohorts.
        feedback = np.sum(relative_sizes * weights) / sum(weights)
        return feedback


class SoftEasterlinFertility(EasterlinFertility):
    # Define a probabilistic relationship for fertility and relative incomes,
    # where ratio between own income and aspiration probabilistically effects
    # childbirth
    def __init__(self, params, agent):
        super(SoftEasterlinFertility, self).__init__(params, agent)

    def reproductive_behaviour(self, pop):
        if not self.agent.have_partner() or not self.agent.partner.employment.have_job():
            return

        feedback_coef = self.calc_feedback(pop)
        base_fertility = self.base_fertility()
        prob_birth = base_fertility * (1 + feedback_coef *
                                       self.params["feedback_mult"])

        logging.debug("feedback_coef = {:3f},"
                      " prob_birth = {:3f}".format(feedback_coef, prob_birth))
        rn = rnd.random()

        if rn < prob_birth:
            self.give_birth(pop)

    def calc_feedback(self, pop):
        asp = self.wage_threshold()
        offset = self.params["aspiration_offset"]
        income = self.agent.partner.employment.get_wage(pop)

        logging.debug("calculating feedback - aspiration : {:3f},"
                      " income : {:3f}".format(asp, income))
        # return  ((income + offset) / asp) - 1
        return log((income + offset) / asp)

    def base_fertility(self):
        """
        """
        # could be dependent on parity
        mult = (self.agent.timestepper.get_timestep_days() /
                self.params["year_length"])
        a = self.params["base_fertility_a"]
        b = self.params["base_fertility_b"]
        c = self.params["base_fertility_c"]
        return hadwiger_fertility(self.agent.age_years, a, b, c) * mult

    def check_family_formation(self, pop):
        return True


class ChildCostFertility(EasterlinFertility):
    # Assume disposable income is effected by presence of children
    # Each child costs money to keep. Desire for another depends on how reduced
    # income compares to parent.
    def __init__(self, params, agent):
        super(ChildCostFertility, self).__init__(params, agent)
        raise NotImplementedError


class ParityEasterlinFertility(EasterlinFertility):
    """
    Let partity > 0 births also be affect by relative cohort size. 
    """
    __slots__ = ()

    def __init__(self, params, agent):
        super(ParityEasterlinFertility, self).__init__(params, agent)

    def check_subsequent_births(self, pop):
        """
        For women who have already started a family
        examined based on current state whether  further children are desired
        / scheduled
        """
        time_since_last_birth = calculate_age_years(self.date_of_last_birth,
                                                    self.agent.timestepper.date)
        #print("time since last birth = {}".format(time_since_last_birth))
        #print("age = {}".format(self.agent.age_years))
        if time_since_last_birth < 1:
            return False
        feedback_mult = self.params["parity_feedback_mult"]
        feedback_coef = 1 + self.calc_feedback(pop) * feedback_mult
        #print("feedback_coef = {}, parity ={}".format(feedback_coef, self.parity))
        mult = (self.agent.timestepper.get_timestep_days() /
                self.params["year_length"]) * feedback_coef
        prob_of_birth = (self.sub_fert(time_since_last_birth) *
                         (mult / self.parity))
        #print("prob_of_birth = {}".format(prob_of_birth))
        #if rnd.random() < prob_of_birth and self.check_family_formation(pop):
        if rnd.random() < prob_of_birth:
        #    print("birth")
            return True
        else:
        #    print("no_birth")
            return False

    def calc_feedback(self, pop):
        asp = self.wage_threshold()
        par_offset = self.params["parity_offset"]
        income = self.agent.partner.employment.get_wage(pop)
        asp_offset = self.params["aspiration_offset"]

        logging.debug("calculating feedback - aspiration : {:3f},"
                      " income : {:3f}".format(asp, income))
        # return  ((income + offset) / asp) - 1
        # print("income ={}, asp = {} ".format(income, asp))
        #return log((income + asp_offset) / asp) - par_offset * self.parity
        return ((income * (1 - par_offset * self.parity)) /
                asp * (1 - asp_offset))


class ProbEasterlinFertility(ParityEasterlinFertility):
    """
    Let partity > 0 births also be affect by relative cohort size. 
    """
    __slots__ = ()

    def __init__(self, params, agent):
        super(ProbEasterlinFertility, self).__init__(params, agent)

    def check_family_formation(self, pop):
        """
        """
        wage = self.agent.partner.employment.get_wage(pop)
        threshold = self.wage_threshold()
        logging.debug("checking family formation: wage = {:2f},"
                      "threshold = {:2f}".format(wage, threshold))

        # if self.agent.timestepper.time_since_start().days / 365.0 < 4:
        #     if rnd.random() > 0.3:
        #         # attempt to correct for heaping of births in first year.
        #         return False
        rand = rnd.random()
         
        # ranges 
        mult = self.params["prob_mult"]
        eta = mult * log(wage / (threshold * (1 - self.params["aspiration_offset"])))
        criteria = self.params["prob_asymptote"] * np.exp(eta) / (1 + np.exp(eta))
        # if self.agent.timestepper.date.year == 2000 and rnd.random() < 0.2:
        #     print("aspiration = {}, wage={}, criteria={}"
        #           "age = {}, parity = {}".format(threshold, wage,criteria, 
        #                                          self.agent.age_years, self.parity))
        if rand < criteria:
            return True


class HeteroEasterlinFertility(EasterlinFertility):
    __slots__ = ["desired_fam_size", "aspiration_offset"]

    def __init__(self, params, agent):
        super(HeteroEasterlinFertility, self).__init__(params,agent)
        self.desired_fam_size = get_desired_family_size(params)
        #self.aspiration_offset = rnd.normalvariate(self.params["aspiration_offset"],
        #                                    self.params["aspiration_var"])
        self.aspiration_offset = rnd.uniform(0, self.params["aspiration_offset_max"])


    def check_family_formation(self, pop):
        """
        """
        wage = self.agent.partner.employment.get_wage(pop)
        threshold = self.wage_threshold()
        logging.debug("checking family formation: wage = {:2f},"
                      "threshold = {:2f}".format(wage, threshold))

        # if self.agent.timestepper.time_since_start().days / 365.0 < 4:
        #     if rnd.random() > 0.3:
        #         # attempt to correct for heaping of births in first year.
        #         return False
        if wage > threshold * (1 - self.aspiration_offset):
            return True

    def check_subsequent_births(self, pop):
        """
        For women who have already started a family
        examined based on current state whether  further children are desired
        / scheduled
        """
        time_since_last_birth = calculate_age_years(self.date_of_last_birth,
                                                    self.agent.timestepper.date)

        
        asp = self.wage_threshold()
        par_offset = self.params["parity_offset"]
        income = self.agent.partner.employment.get_wage(pop)

        if time_since_last_birth < 1:
            return False
        if  (((income * (1 - par_offset * self.parity)) > 
               asp * (1 - self.aspiration_offset)) and
            (self.parity < self.desired_fam_size)):
            return True
        else:
            return False




def get_desired_family_size(params):
    rn = rnd.random()
    # proportion desiring no more than two children
    prop2 = params["desire2"]
    prop3 = prop2 + (1 - 0.05 - prop2) / 2
    if rn < 0.02:
        return 0
    elif rn < 0.1:
        return 1
    elif rn < prop2:
        return 2
    elif rn < prop3:
        return 3
    elif rn < 0.95:
        return 4
    elif rn < 0.98:
        return 5
    else:
        return 6



def get_fecundity_func(a, b, c, mu):
    """
    Get multiplier that reduces fertility probability according to age
    """
    def fecundity(x):
        return (a - b * (x - mu) - c * (x - mu) ** 2)
    return fecundity


def hadwiger_fertility(x, a, b, c):
    """
    Hadwiger fertility function for base fertility level.
    """
    part1 = a * (b / c) * (c / x)**(3 / 2)
    part2 = exp(-(b**2) * ((c / x) + (x / c) - 2))
    return part1 * part2


def get_fertility(params, agent):
    """
    Construct the fertility object specified by the contents of parameter
    dictionary
    """
    if params["fertility_type"] == "easterlin":
        return EasterlinFertility(params, agent)
    elif params["fertility_type"] == "simple":
        return SimpleFertility(params, agent)
    elif params["fertility_type"] == "married":
        return MarriedFertility(params, agent)
    elif params["fertility_type"] == "partner":
        return PartnerFertility(params, agent)
    elif params["fertility_type"] == "soft_easterlin":
        return SoftEasterlinFertility(params, agent)
    elif params["fertility_type"] == "parity_easterlin":
        return ParityEasterlinFertility(params, agent)
    elif params["fertility_type"] == "prob_easterlin":
        return ProbEasterlinFertility(params, agent)
    elif params["fertility_type"] == "hetero":
        return HeteroEasterlinFertility(params, agent)
    else:
        return NotImplementedError("Unrecognised fertility_type parameter:"
                                   " {}".format(params["fertility_type"]))


