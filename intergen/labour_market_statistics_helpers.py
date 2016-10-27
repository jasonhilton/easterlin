"""

Set of functions to collect statistics from a LabourMarket instance.
Used by StatisticsCollector to collect relavent information

"""
from __future__ import division
import numpy as np

from .agent import Agent, Male, Female


# Helper functions for statistics collection ---------------------------------
# These could all be methods of labour market but leaving them here helps separate 
# model code from auxilliary code.


def get_vacancy_rate(labour_market):
    """
    Proportion of all jobs which are unoccupied
    """
    # vrate1 = sum(not job.occupied() for job in labour_market.joblist) / \
    #          len(labour_market.joblist)
    vrate2 = len(labour_market.vacancies) / float(len(labour_market.joblist))
    # assert vrate1 == vrate2
    return vrate2


def get_wage_distribution(labour_market):
    return [job.occupant.wage for job in labour_market.joblist
            if job.occupant]

def get_employed_skill_distribution(labour_market):
    return [job.occupant.agent.skill for job in labour_market.joblist
            if job.occupant]

def get_vacancy_difficulty_distribution(labour_market):
    return [vacancy.difficulty for vacancy in labour_market.vacancies]

def get_job_difficulty_distribution(labour_market):
    return [job.difficulty for job in labour_market.joblist
            if job.occupant]

def get_experience_distribution(labour_market):
    return [job.occupant.agent.experience.days / labour_market.params["year_length"]
            for job in labour_market.joblist if job.occupant]

def get_age_wage_distribution(labour_market):
    """
    returns list of tuples, with a workers age and wage
    """
    return [(job.occupant.agent.age_years, job.occupant.wage)
            for job in labour_market.joblist if job.occupant]

def get_average_youth_wage(labour_market):
    """
    
    """
    return np.mean([job.occupant.wage for job in labour_market.joblist 
                    if job.occupant and job.occupant.agent.age_years < 30])
    



labour_stocks_dispatch = {"vacancy_rate": get_vacancy_rate,
                          "wage": get_wage_distribution,
                          "employed_skill": get_employed_skill_distribution,
                          "vacancy_difficulty": get_vacancy_difficulty_distribution,
                          "job_difficulty": get_job_difficulty_distribution,
                          "experience": get_experience_distribution,
                          "wage_by_age": get_age_wage_distribution,  # list of tuples
                          "young_wage": get_average_youth_wage
                          }
