import datetime
import logging
import copy
import calendar as cal


class TimeStepper(object):
    """
    Timesteppers keep track of the date in a simulation.
    Methods are provided to get the current date, find the current timestep length,
    and to step forward to the next time step.
    Monthly and yearly timesteps are catered for, as well as steps of any integer number of days
    """
    def __init__(self, params):

        self.step_type = params["timestep"]
        self.year_length = params["year_length"]
        try:
            self.start_date = datetime.datetime.strptime(params["start_date"],
                                                         "%Y-%m-%d").date()
        except ValueError:
            msg = "Invalid start date given: please use YYYY-mm-dd format"
            logging.error(msg)
            raise ValueError(msg)

        if self.start_date.day > 28 and self.step_type == "month":
            logging.warning("Starting the simulation near the end of a month"
                            "results in monthly timesteps running out of sync")
        self.date = copy.deepcopy(self.start_date)
        self._determine_step_length_function()
        self.timestep_length = self.step_length_function()

    def step_forward(self):
        """
        Increment date and update timestep length
        """
        self.increment_date()
        self.update_timestep_length()

    def increment_date(self):
        """
        Increase current date by one timestep_length
        """
        self.date += self.timestep_length

    def update_timestep_length(self):
        """
        Update the length for the next timestep
        """
        self.timestep_length = self.step_length_function()

    def get_date(self):
        """
        Return the current date
        """
        return self.date

    def get_timestep_length(self):
        """
        Return the current timestep_length as a datetime object
        """
        return self.timestep_length

    def get_timestep_days(self):
        """
        Return the number of days in the current timestep 
        """
        return self.timestep_length.days

    def _determine_step_length_function(self):
        """
        Based on the type of step specified, choose the correct function to increment the date
        Valid types are "year"
        """
        if self.step_type == "year":
            self.step_length_function = self._year_timestep
        elif self.step_type == "month":
            self.step_length_function = self._month_timestep
        elif isinstance(self.step_type, int):
            # not very pythonic?
            logging.info("Assume timestep given in days\n"
                         "Timestep = {} days".format(self.step_type))
            self.timestep_length = datetime.timedelta(days=self.step_type)
            self.step_length_function = self._days_timestep
        else:
            raise ValueError("Invalid step type. Step must be years, months,"
                             " or an integer number of days")

    def _month_timestep(self):
        """
        Calculate and update the correct month length for the current date and increment
        the date by this amount
        """
        days = cal.monthrange(self.date.year, self.date.month)[1]
        return datetime.timedelta(days=days)

    def _year_timestep(self):
        """
        Update the current year length and increment the date byt this amount.
        Accounts for leap years
        """
        if cal.isleap(self.date.year):
            return datetime.timedelta(days=366)
        else:
            return datetime.timedelta(days=365)

    def _days_timestep(self):
        """
        Increment the date by one timestep
        """
        return self.timestep_length

    def time_since_start(self):
        return (self.date - self.start_date)

    def get_year_length(self):
        return self._year_timestep()



# DEPRECATED -----------------------------------------------------------
# these were used initially but having access to date and timestep length
# means class is preferable

def get_month_length_generator(start_date):
    """
    Produce a generator that yields the number of days in the next month

    Parameters
    ----------
    start_date: datetime.date instance
        The date to start generating dates from

    Yields
    ------
    A timedelta object giving the number of days in the current month
    """
    date = copy.deepcopy(start_date)
    while True:
        days = cal.monthrange(date.year, date.month)[1]
        days_delta = datetime.timedelta(days=days)
        date += days_delta
        yield days_delta


def get_year_length_generator(start_date):
    """
    Produce a generator that yields the number of days in the current year

    Parameters
    ----------
    start_date: datetime.date instance
        The date to start generating dates from

    Yields
    ------
    A timedelta object giving the number of days in the year
    """
    date = copy.deepcopy(start_date)
    while True:
        if cal.isleap(date.year):
            days_delta = datetime.timedelta(days=366)
        else:
            days_delta = datetime.timedelta(days=365)
        date += days_delta
        yield days_delta
