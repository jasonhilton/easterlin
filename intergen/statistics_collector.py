"""
Module collecting statistics relating to a simulation

author: Jason Hilton

"""
from __future__ import division
from collections import Counter, defaultdict
from functools import partial
import os
import pandas as pd

from .population import Population
from .agent import Agent, Male, Female
from .labmarket import LabourMarket
from .population_statistics_helpers import *
from .labour_market_statistics_helpers import *

# confine event types to enum?
# name columns / series/ indicies ? 
# using partial as for bivariate module
# offload the lookup dictionaries to an adaptor class
# make more generic?

class VoidStatisticsCollector(object):
    """
    Void class in case we don't want to collect statistics.
    """
    def __init__(self):
        pass

    def record_stats(self, publisher):
        pass

    def record_event(self, agent, event_type, *args, **kwargs):
        pass

    def register_sim(self, sim):
        pass

    def process_stats(self):
        pass


class StatisticCollectorException(Exception):
    def __init__(self, message):
        super(StatisticCollectionException, self).__init__(message)


class StatisticsCollector(object):
    
    def __init__(self, stats_to_capture):
        """
        Set up statistics collector to record certain characteristics
        """
        # very rubbish code below.
        # push to function using setattr? 
        # generalise for any type of stats? 
        self.stats_to_capture = stats_to_capture
        setup_keys = ["events", "stocks", "labour"]
        attribute_names = ["events_to_capture",
                           "stocks_to_capture",
                           "lab_stats_to_capture"]
        setup_functions = [self._set_up_event_counters,
                           self._set_up_stock_dicts,
                           self._set_up_lab_dicts]

        for att, key, func in zip(attribute_names, setup_keys, setup_functions):
            self._setup_counters(att, key, func)


        # try:
        #     self.events_to_capture = stats_to_capture["events"]
        #     self._set_up_event_counters(self.events_to_capture)
        # except KeyError:
        #     self.events_to_capture = []



        # self.stocks_to_capture = stats_to_capture["stocks"]
        # self.lab_stats_to_capture = stats_to_capture["labour"]
        
        # self._set_up_stock_dicts(self.stocks_to_capture)
        # self._set_up_lab_dicts(self.lab_stats_to_capture)

    def _setup_counters(self, attribute_name, dict_key, setup_function):
        try:
            setattr(self, attribute_name, self.stats_to_capture[dict_key])
            setup_function(getattr(self, attribute_name))
        except KeyError:
            setattr(self, attribute_name, [])

    def record_stats(self, publisher, date):
        """
        Called by part of the simulation to record relevant statistics about
        that object.
        The calling object must be passed as an argument

        Parameters
        ----------
        publisher:
            A domain-model object which requests some elements of its state be
            recorded.

        Raises
        ------
        StatisticCollectorException:
            Raised if the collector is asked to record an event before a simulation
            is registered.

        """
        #try:
            # this is probably a bit flakey
        if isinstance(publisher, Agent):
            self.record_event(publisher, date)
        elif isinstance(publisher, Population):
            self.record_pop_stats(publisher, date)
        elif isinstance(publisher, LabourMarket):
            self.record_lab_stats(publisher, date)
        #except AttributeError:
        #    raise StatisticCollectorException("No simulation registered")

    def record_lab_stats(self, labour_market, date):
        """
        Record labour market information
        """
        # check not already recorded for this timestep
        for lab_stat in self.lab_stats_to_capture:
            if date not in self.lab_dict[lab_stat]:
                try:
                    self.lab_dict[lab_stat][date] = labour_stocks_dispatch[lab_stat](labour_market)
                except ZeroDivisionError:
                    self.lab_dict[lab_stat][date] = pd.np.NaN

    def record_pop_stats(self, population, date):
        """
        Parameters
        ----------
            population: an object of class Population
        """
        for stock in self.stocks_to_capture:
            if date not in self.stocks_dict[stock]:
                try:
                    self.stocks_dict[stock][date] = stock_dispatch_dict[stock](population)
                except ZeroDivisionError:
                    self.stocks_dict[stock][date] = pd.np.NAN

    def record_event(self, agent, event_type, date):
        """
        Record an event - to be called by an agent upon experiencing an event

        Parameters:
        -----------
        agent: Agent
            The agent experiencing the event
        event_type: hashable
            A string specifying the type of event
        """
        if event_type in self.events_to_capture:
            self.event_dict[event_type][date][agent.age_years] += 1

    def _set_up_event_counters(self, events_to_capture):
        """
        Set up the relevant counters for the statistics we wish to collect.

        Parameters
        ----------
        events_to_capture: iterable
            some iterable containing the names of the events we would like to
            capture. These names are used to create a dictionary keying counters for
            those events
        """
        # self.population_count = {}
        # self.population_age_count = defaultdict(Counter)
        self.event_dict = {}

        for event in events_to_capture:
            self.event_dict[event] = defaultdict(Counter)

    def _set_up_stock_dicts(self, stocks_to_capture):
        """
        Setup dictionaries for the stocks we wish to capture every timestep
        """
        self.stocks_dict = {}
        for stock in stocks_to_capture:
            self.stocks_dict[stock] = defaultdict(int)

    def _set_up_lab_dicts(self, lab_stats_to_capture):
        """
        Setup dictionaries for the stocks we wish to capture every timestep
        """
        self.lab_dict = {}
        for lab in lab_stats_to_capture:
            self.lab_dict[lab] = defaultdict(int)

    def convert_event_counters_to_dataframe(self, event_types):
        """
        Once the simulation is finished, convert all event counters to pandas dataframes
        for ease of analysis.
        """
        self.event_df_dict = {}

        for event in event_types:
            self.event_df_dict[event] = convert_age_counters_to_df(self.event_dict[event])

    def convert_stocks_to_pandas(self, stock_types):
        """
        Convert the stocks collected to pandas DataFrames
        Finds the correct function based on the stock type.
        Results held in a dictionary as an attribute of the instance.
        """
        self.stock_df_dict = {}
        for stock in stock_types:
            func_to_use = stock_pandas_dispatch[stock]
            self.stock_df_dict[stock] = func_to_use(self.stocks_dict[stock])

        # self.population_size = pd.Series(data=self.population_count.values(),
        #                                  index=self.population_count.keys())

        # self.population_by_age = convert_age_counters_to_df(self.population_age_count)

    def convert_lab_stats_to_pandas(self, lab_stat_types):
        """
        Convert the lab_stats collected to pandas DataFrames
        Finds the correct function based on the statistic typetype.
        Results held in a dictionary as an attribute of the instance.
        """
        self.lab_df_dict = {}
        for lab_stat in lab_stat_types:
            func_to_use = lab_pandas_dispatch[lab_stat]
            self.lab_df_dict[lab_stat] = func_to_use(self.lab_dict[lab_stat])

    def process_stats(self):
        """
        process statistics into a usable form
        """
        self.convert_stocks_to_pandas(self.stocks_to_capture)
        self.convert_event_counters_to_dataframe(self.events_to_capture)
        self.convert_lab_stats_to_pandas(self.lab_stats_to_capture)

    def save_out_all_stats(self, outpath, suffix):

        for result_dict in [self.stock_df_dict, self.lab_df_dict, self.event_df_dict]:
            self.save_out_result_dict(result_dict, outpath, suffix)

    def save_out_result_dict(self, result_dict, outpath, suffix):
        #  TODO does this need to be instance method? 
        for name, df_like in result_dict.items():
            out_file = os.path.join(outpath, name + "_" + suffix + ".csv")
            df_like.to_csv(out_file)

    def pad_event_counters(self, date):
        """
        if no events happen, in a given year, it's more convenient for analysis
        to record zero in the given year. 
        """
        ages = range(18, 50)
        for event in self.event_dict.keys():
            for age in ages:
                self.event_dict[event][date][age] += 0


def convert_dict_to_series(time_dict):
    """ Converts a dictionary of single values with time as keys to a pandas series """
    return pd.Series(time_dict)


def convert_dict_of_lists_to_df(time_dict):
    """ Convert list of dicts to a data frame"""
    return pd.DataFrame(time_dict)


def convert_dict_of_distributions_to_df(time_dict):
    wide_df = pd.DataFrame.from_dict(time_dict, orient="index")
    wide_df.index.name = "sim_time"
    wide_df = wide_df.reset_index()
    long_df = pd.melt(wide_df, id_vars="sim_time")
    long_df = long_df.set_index("sim_time")
    long_df = long_df.filter(["value"]).dropna().sort_index()
    return long_df


def convert_age_counters_to_df(dict_of_counters):
    """
    This allows us to convert counts classified by two dimensions to a pandas dataframe
    Currently this is used for counters over age, sat in a dictionary keyed by time

    Parameters
    ----------
    dict_of_counters: defaultdict(Counter)
        A dictionary of counters with time as the key
        and a counter over age of event for each value.

    Returns
    -------
    pandas.DataFrame
        A pandas dataframe of the values of the counters
        with time and age as indexes
    """
    event_df = pd.concat([pd.DataFrame.from_dict(counter, orient="index")
                          for counter in dict_of_counters.values()],
                         axis=1)

    event_df.columns = dict_of_counters.keys()

    return(event_df.T.sort_index())


def convert_dict_of_bivariate_dists(dict_of_list_of_tuples, col_names=None):
    """
    Convert a data where for each time step we collect data we have two values
    for every agent
    """
    list_of_dfs = [pd.DataFrame(timestep_data)
                   for timestep_data in dict_of_list_of_tuples.values()]
    return_df = pd.concat(list_of_dfs, axis=0, keys=dict_of_list_of_tuples.keys())
    if col_names:
        return_df.columns = col_names
    return return_df


stock_pandas_dispatch = {"population": convert_dict_to_series,
                         "population_by_age": convert_dict_of_lists_to_df,
                         "unemployment": convert_dict_to_series,
                         "parity": convert_dict_of_distributions_to_df,
                         "married_by_age": convert_dict_of_lists_to_df,
                         "umemployed_skill": convert_dict_of_distributions_to_df,
                         "age_at_first_birth": convert_dict_of_distributions_to_df,
                         "father_skill": convert_dict_of_distributions_to_df,  # this is an empirical dist?!
                         "labour_force_size": convert_dict_to_series,
                         "youth_unemployment": convert_dict_to_series
                         }

lab_pandas_dispatch = {"vacancy_rate": convert_dict_to_series,
                       "young_wage": convert_dict_to_series,
                       "wage": convert_dict_of_distributions_to_df,
                       "employed_skill": convert_dict_of_distributions_to_df,
                       "vacancy_difficulty": convert_dict_of_distributions_to_df,
                       "job_difficulty": convert_dict_of_distributions_to_df,
                       "experience": convert_dict_of_distributions_to_df,
                       "wage_by_age": partial(convert_dict_of_bivariate_dists, col_names=["age", "wage"])
                       }


#  How to change this.
# What about classing certain output as time series,
# time series of distributions
# or time series of bivariate distributions

# also some summary measures might be usefull
# ie. average parity
# average wage
# average skill / variance in skill
# average experience / var
# mean age
# mean age at first birth


stocks_univariate_timeseries = ["population",
                                "unemployment",
                                "labour_force_size",
                                "youth_unemployment"]


lab_uni_timeseries    =        ["vacancy_rate", "young_wage"]


def get_mean_age(series):
    return series.multiply(series.index).divide(series.sum()).sum()


def get_mean_pop_age(stats):
    pop_df = stats.stock_df_dict["population_by_age"]
    return pop_df.apply(get_mean_age)


def get_mean_age_birth(stats):
    birth_df = stats.event_df_dict["birth"].T
    return birth_df.apply(get_mean_age)


def get_timeseries_df(stats, stocks, lab_stats, others, freq):
    """
    Helper functions to weld together stats that can be represented as a single time
    series into one data frame with a period index
    """
    result_df = pd.concat([stats.stock_df_dict[key] for key in stocks], axis=1)
    result_df.columns = stocks
    result_df["birth"] = stats.event_df_dict["birth"].sum(axis=1)
    if "first_birth" in stats.event_df_dict:
        result_df["first_birth"] = stats.event_df_dict["first_birth"].sum(axis=1)
    for stat in lab_stats:
        result_df[stat] = stats.lab_df_dict[stat]
    for name, funct in others.items():
        result_df[name] = funct(stats)
    result_df.index = pd.PeriodIndex(result_df.index, freq=freq)
    return result_df


other = {"mean_pop_age": get_mean_pop_age,
         "mean_age_birth": get_mean_age_birth}
