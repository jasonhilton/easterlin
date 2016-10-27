from __future__ import division
import random as rnd
from itertools import count
import datetime

from intergen.agent import Male, Female
import numpy as np

# Should have some facility for producing different types of agent
# particularly using composition to pass fertility instances


class AgentFactory(object):
    def __init__(self, params, timestepper, statistics_collector):
        """
        Create an agent factory to generate a population of agents.
        Provides both members of the initial population and subsequent births
        """
        self.params = params
        self.id_state = count()
        self.timestepper = timestepper
        self.stats = statistics_collector

        self.cum_start_dist = self.startup_age_cum_dist()

    def make_initial_agent(self):
        """
        Produce a member of the initial population
        """
        attributes = self.create_initial_attributes()
        return self.make_agent(attributes)

    def make_new_born(self):
        """
        Produce a new born agent
        """
        attributes = self.create_new_born_attributes()
        return self.make_agent(attributes)

    def make_agent(self, attributes):
        sex_rng = rnd.Random()
        if sex_rng.random() < self.params["prop_male_at_birth"]:
            agent = Male(self.params, attributes, self.timestepper, self.stats)
        else:
            agent = Female(self.params, attributes,
                           self.timestepper, self.stats)
        return agent

    def startup_age_prob(self, age):
        # Parameterise?
        base = 1 - 0.0005 * age - 0.0002 * age ** 2
        peak = self.params["starting_hump_peak"]
        mult = self.params["starting_hump_mult"]
        hump = mult * np.exp(-0.002 * (age - peak) ** 2)
        return base + hump

    def startup_age_cum_dist(self):
        age = np.arange(80)
        probs = self.startup_age_prob(age)
        cumprobs = np.cumsum(probs)
        normcumprobs = cumprobs / cumprobs[-1]
        return normcumprobs

    def draw_age_distribution(self):
        """
        Return a draw from the inital age distribution in days
        """
        # year = rnd.randint(0, 75)
        # day = rnd.randint(0, 365)
        # return datetime.timedelta(days=max(1, (year * 365) + day))
        year = draw_from_age_dist(self.cum_start_dist)
        day = rnd.randint(0, 365)
        return datetime.timedelta(days=max(1, (year * 365) + day))

    def draw_experience(self, age):
        """
        randomly draw agent experience, dependent on age
        only relevant for starting population
        """
        # potentially in the long run could make experience dependent on skill
        # to reflect differential time in education

        # using 365 for year length is slightly off, but onlly slightly
        # means we overstate working life by c. 4 days
        working_life = max(datetime.timedelta(0),
                           age - datetime.timedelta(days=16 * 365))
        experience = working_life.days * rnd.uniform(0.5, 1)  # parameterise ?
        return int(experience)

    def draw_skill(self):
        """
        Distribution of skills in the population;
        A normal distribution is used.
        """
        return min(max(0.01, rnd.normalvariate(0.5, 0.2)), 1)
        # return 0.5

    def initialise_fertility(self):
        """
        Create instance of fertility class to allow modular fertility elements
        """

    def create_initial_attributes(self):
        """
        create dictionary of agent attributes to passed into agent's init
        function
        """
        attributes = {}
        # attributes["fertility"] = self.initialise_fertility()
        attributes["age"] = self.draw_age_distribution()
        attributes["experience"] = datetime.timedelta(
            self.draw_experience(attributes["age"]))
        attributes["skill"] = self.draw_skill()
        attributes["DOB"] = self.timestepper.start_date - attributes["age"]
        attributes["aspiration"] = self.get_intial_aspiration()
        attributes["ident"] = next(self.id_state)
        return attributes

    def create_new_born_attributes(self):
        attributes = {}
        attributes["age"] = self.get_new_born_age(
            self.timestepper.get_timestep_length())
        attributes["experience"] = datetime.timedelta(0)
        attributes["ident"] = next(self.id_state)
        attributes["DOB"] = self.timestepper.date + attributes["age"]
        attributes["aspiration"] = self.params["default_aspiration"]
        attributes["skill"] = self.draw_skill()
        return attributes

    def get_new_born_age(self, timestep_length):
        inc = 1 + int(rnd.random() * timestep_length.days)
        return datetime.timedelta(days=inc)

    def get_intial_aspiration(self):
        """
        """
        # return max(self.params["default_aspiration"],
        #            rnd.random() * self.params["initial_aspiration_max"])
        return rnd.uniform(self.params["default_aspiration"],
                           self.params["initial_aspiration_max"])


    def initialise_mortality(self):
        """
        create a mortality module.
        This could in fact just pass a reference to the same mortality object
        for everyone, which could be composed to just sit within the above.
        """
        pass


def draw_from_age_dist(cum_dist):
    rnum = rnd.random()
    for i in range(len(cum_dist)):
        if rnum < cum_dist[i]:
            return i
    else:
        return "error"
