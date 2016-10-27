"""

Set of functions to collect statistics from a population instance.
Used by StatisticsCollector to collect relavent information

"""
from __future__ import division
from collections import Counter

from .agent import Agent, Male, Female


# Helper functions for statistics collection ---------------------------------
# These could all be methods of population but leaving them here helps separate 
# model code from auxilliary code.

def population_size(population):
    """ Returns the size of the population object"""
    return len(population.poplist)


def prop_married_by_age(population, agent_type=Agent):
    """
    Determine what proportion of the population are married by age

    Parameters
    ----------
    population:Population
        instance of Population class. Expects attribute poplist, which must be a
    agent_type: inherits from Agent
        Class to restrict calculation to. e.g. Female.

    Returns
    -------
    list
        proportion of agents married for each age in years from 0 to 99.

    """
    ages = range(100)
    age_dist = get_age_distribution(population, agent_type=agent_type)
    married_age_dist = get_age_distribution(population, agent_type=agent_type,
                                            condition=lambda x: x.have_partner())
    get_prop = lambda x, y: x / y if y else 0  # avoid dividing by zero
    return [get_prop(married_age_dist[age], age_dist[age]) for age in ages]


def get_age_distribution(population, agent_type=Female,
                         condition=lambda x: True):
    """
    Gets the age distribution of agents of some specified subclass of
    the base Agent type (eg Male, Female), but only those meeting the
    condions described by the function in condition

    Parameters
    ----------
    poplist: iterable
        Contains individual agents as elements
    agent_type: inherits from Agent
        Class to restrict calculation to. e.g. Female.
    condition: callable
        Some condition by which agents are included in calculatin e.g age range

    Returns
    -------
    list
        proportion of agents married for each age in years from 0 to 99.

    """
    age_dist = Counter()
    for agent in population.poplist:
        if condition(agent) and isinstance(agent, agent_type):
            age_dist[agent.age_years] += 1
    return age_dist


def get_unemployment_rate(population, agent_type=Male):
    """
    divide total agents with job by total working age population
    """
    emp_count = sum(agent.employment.have_job() for agent in population.poplist)
    potential_workforce = sum(agent.employment.eligible_for_market() 
                              for agent in population.poplist
                              if isinstance(agent, agent_type))
    return 1 - emp_count / float(potential_workforce)


def get_unemp_skill_distribution(population):
    """
    get skill distribution of those unemployed male agents old enough to
    work
    exclude those who have retired
    """
    return [agent.skill for agent in population.poplist
            if agent.employment.eligible_for_market() 
            and not agent.employment.job and
            isinstance(agent, Male)]


def get_lab_force_size(population):
    # may depend on women work status
    return sum(agent.employment.eligible_for_market() for agent in
               population.poplist)


def get_youth_unemployment(population, agent_type=Male):
    return get_cohort_unemployment(population, 16, 30, agent_type)


def get_cohort_unemployment(population, lower, upper, agent_type):
    """
    Get unemployment for those aged between lower and upper
    """
    in_cohort = in_cohort_generator(lower, upper)
    emp_count = sum(agent.employment.have_job() for agent in population.poplist
                    if in_cohort(agent))
    potential_workforce = sum(agent.employment.eligible_for_market() for agent in
                              population.poplist if isinstance(agent, agent_type)
                              and in_cohort(agent))
    return 1 - emp_count / float(potential_workforce)


def get_labour_cohort_count(population, lower, upper, agent_type):
    """
    Get count of people between ages lower and upper, of agent_type
    """
    in_cohort = in_cohort_generator(lower, upper)
    potential_workforce = sum(agent.employment.eligible_for_market() for agent in
                              population.poplist if isinstance(agent, agent_type) and
                              in_cohort(agent))
    return potential_workforce

def get_cohort_count(population, lower, upper, agent_type):
    """
    Get count of people between ages lower and upper, of agent_type
    """
    in_cohort = in_cohort_generator(lower, upper)
    cohort_size = len([agent for agent in population.poplist
                       if isinstance(agent, agent_type) and in_cohort(agent)])
    return cohort_size


def in_cohort_generator(lower, upper):
    """
    Give function that determines whether an agent is in a cohort defined by
    the upper and lower ages
    """
    def in_cohort(agent):
        return agent.age_years > lower and agent.age_years < upper
    return in_cohort


def get_parity_distribution(population):
    """
    get a list of the parity of female adults
    """
    return [agent.fertility.parity for agent in population.poplist
            if isinstance(agent, Female) and agent.age_years > 16]


def age_at_first_birth_distribution(population):
    """
    Get list of ages at first birth of those (women, implicitly)
    with children
    """
    return [age_at_first_birth(agent) for agent in population.poplist
            if isinstance(agent, Female) and agent.children]


def skill_of_mothers_partners(population):
    females = [agent for agent in population.poplist if isinstance(agent, Female)]
    skill = [agent.partner.skill for agent in females
             if agent.children]
    return skill


def skill_of_mothers(population):
    females = [agent for agent in population.poplist if isinstance(agent, Female)]
    skill = [agent.skill for agent in females
             if agent.children]
    return skill


def age_at_first_birth(mother):
    return mother.age_years - mother.children[0].age_years


stock_dispatch_dict = {"population": population_size,
                       "population_by_age": get_age_distribution,
                       "unemployment": get_unemployment_rate,
                       "parity": get_parity_distribution,
                       "married_by_age": prop_married_by_age,
                       "umemployed_skill": get_unemp_skill_distribution,
                       "age_at_first_birth": age_at_first_birth_distribution,
                       "father_skill": skill_of_mothers_partners,
                       "labour_force_size": get_lab_force_size,
                       "youth_unemployment": get_youth_unemployment,
                       }
