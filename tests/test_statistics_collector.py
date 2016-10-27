import sys

sys.path.append('..')

from intergen.statistics_collector import *
from intergen.agent import BaseAgent
from intergen.simulation import BaseSim
from intergen.population import BasePopulation


class TestStatisticsCollector(object):
    """
    test the statistic collector works as expected
    """

    # def setup_statistics_collector(cls):
    @classmethod
    def setup_class(cls):
        cls.sim = BaseSim()
        cls.statistics_collector = StatisticsCollector({"events": ["birth"], "stocks": ["population"]})
        cls.statistics_collector.register_sim(cls.sim)

    def test_record_births(self):
        self.statistics_collector.record_event(BaseAgent(0, 24*360), "birth")
        self.statistics_collector.record_event(BaseAgent(0, 28*360), "birth")

        self.statistics_collector.convert_event_counters_to_dataframe(["birth"])

        assert self.statistics_collector.event_df_dict["birth"].ix[0, 24] == 1

    def test_record_pop_stats(self):
        poplist = [BaseAgent(i, x) for i, x
                   in zip(range(100), range(0, 35000, 350))]
        base_population = BasePopulation(poplist)
        self.statistics_collector.record_pop_stats(base_population)
        self.statistics_collector.convert_stocks_to_pandas(["population"])
        # check for year 0
        assert self.statistics_collector.stock_df_dict["population"][0] == 100
