from __future__ import division
import random as rnd
import logging


from numpy.random import poisson


logger = logging.getLogger("intergen")


class Employment(object):
    __slots__ = ["agent", "params", "wage", "job", "offers"]

    def __init__(self, agent, params):
        self.agent = agent
        self.params = params
        self.wage = 0
        self.job = None
        self.offers = []

    # setup functions -------------------------------------------------

    def job_setup_activity(self, market):
        if self.participate_in_market():
            self.apply_for_jobs(market)

    # timestep functions ----------------------------------------------

    def activity(self, sim):
        if self.participate_in_market():
            self.apply_for_jobs(sim.get_labour_market())

    def assess_offers(self, pop):
        """
        Examine offers seen. Choose the best one
        """
        if not self.offers:
            return
        self.offers.sort(key=lambda x: x["wage"])
        winner, wage = self.offers[-1]["job"], self.offers[-1]["wage"]
        if self.job:
            # if self.job.calc_wage(self, pop) > wage:
            if self.wage(self, pop) > wage:
                # don't take any job..
                self.offers = []
                return
            else:
                self.job.retire()
        self.job = winner
        self.wage = wage
        winner.fill_job(self)
        self.offers = []
        logger.debug("event:started_job,date:{},agent:{},wage:{},skill:{},"
                     "aspiration:{}".format(self.agent.timestepper.date,
                                            self.agent.ident,
                                            wage,
                                            self.agent.skill,
                                            self.agent.aspiration))

    def get_wage(self, pop):
        """
        Find the amount of earnings. Substitute a benefit if you're unemployed.
        """
        if self.job:
            return self.wage
        else:
            self.wage = pop.benefit_level
            return self.wage

    def eligible_for_market(self):
        """
        determine whether agent is able to get a job
        """
        # For simplicity, and representing to some extent the employment
        # realities, women do not work.
        if self.agent.age_years > 16 and \
                self.agent.age_years < self.params["retirement_age"] and not \
                self.agent.isfemale:
            return True
        else:
            return False

    def participate_in_market(self):
        """
        function determining whether agents attempts to find a job
        """
        # at present this is the same as eligibility
        # but this needn't be the case
        # can we make it so added to some sort of jobseeker dict?
        if self.eligible_for_market() and not self.have_job():
            return True

    def determine_job_application_numbers(self):
        # should be somewhat similar to a frailty model
        # timestep_length is slighly wrong here for short months and leap years
        # but this is not a massive problem
        mult = self.agent.timestepper.get_timestep_days() /\
                        self.params["year_length"]
        if self.job:
            return poisson(self.params["job_apps_employed"] * mult)
        else:
            return poisson(self.params["job_apps_unemployed"] * mult)

    def apply_for_jobs(self, market):
        """
        send out a number of applications to vacant jobs
        these vary depending on current employment status
        """
        #  mult = self.pop.sim.timestep_length / self.params["year_length"]
        # should use functions here to interact with labour market?

        applications = self.determine_job_application_numbers()
        targets = []
        n_vac = len(market.vacancies)
        

        if self.params["experience_floor"]:
            # or maybe iterate through a random shuffleb
            # untill reached the one needed.
            # a stopping problem!
            indicies = rnd.sample(range(n_vac), n_vac)
            for i in indicies:
                if self._check_eligible(market.vacancies[i]):
                    targets.append(i)
                if len(targets) >= applications:
                    break

            # this is a bottle neck...
            # eligible = [vac for vac in market.vacancies
            #     if vac.experience_floor <= self.agent.experience.days and
            #     (self.agent.experience.days - vac.experience_floor < 365 * 4
            #     or vac.experience_floor > 365 * (self.params["exp_max"] - 4))]
            #       # don't apply if your massively over-qualified
                        # unless its a top-end job 
        else:
            targets = rnd.sample(range(n_vac), min(n_vac, applications))
            #targets = indicies[:applications]

        #    eligible = market.vacancies
        #if len(eligible) == 0:
        #    return

        # TODO investigate iterating through and 'rolling dice'
        # until number chose == applications
        # might be mmore efficient than 'choice'
        # plus can used filter as iterator
        # UPDATE: replaced horribly inefficient np.choice
        # with decent and scalable rnd.sample 
        # c ~ 100x faster for 100k list
        
        for target in targets:
            market.vacancies[target].applicants.append(self)

    def _check_eligible(self, vac):
        if not self.params["experience_floor"]:
            return True
        else:
            condition1 = vac.experience_floor <= self.agent.experience.days
            condition2 = (self.agent.experience.days - vac.experience_floor < 365 * 4
                          or vac.experience_floor > 365 * (self.params["exp_max"] - 4))
            return condition1 and condition2


    def have_job(self):
        return self.job is not None


class InactiveEmployment(Employment):
    # Not Used
    def __init__(self, agent, params):
        self.agent = agent
        self.params = params
        self.wage = None
        self.job = None

    def job_setup_activity(self, market):
        pass

    def apply_for_jobs(self, market):
        pass

    def eligible_for_market(self):
        return False
