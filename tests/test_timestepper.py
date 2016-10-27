import pytest
import datetime

import sys
sys.path.append('..')

from intergen.timestepper import TimeStepper


def get_timestepper(start_date, timestep):
    params = {}
    params["timestep"] = timestep
    params["start_date"] = start_date  
    params["year_length"] = 365
    return TimeStepper(params)


def test_monthtimestepper():
    timestepper = get_timestepper("2016-01-01", "month")
    assert timestepper.date.year == 2016
    assert timestepper.date.day == 1
    assert timestepper.get_timestep_length() == datetime.timedelta(days=31)

    timestepper.step_forward()
    assert timestepper.get_timestep_length() == datetime.timedelta(days=29)
    # check this is persistant
    assert timestepper.get_timestep_length() == datetime.timedelta(days=29)

    for _ in range(12):
        timestepper.step_forward()

    assert timestepper.date == datetime.datetime.strptime("2017-02-01", "%Y-%m-%d").date()
    assert timestepper.get_timestep_length() == datetime.timedelta(days=28)


def test_year_timestepper():
    timestepper = get_timestepper("2100-01-01", "year") # not a leap year
    assert timestepper.get_timestep_length().days == 365
    
    timestepper.step_forward()
    assert timestepper.date == datetime.datetime.strptime("2101-01-01", "%Y-%m-%d").date()
    assert timestepper.get_timestep_length().days == 365

    for _ in range(3):
        timestepper.step_forward()

    assert timestepper.date == datetime.datetime.strptime("2104-01-01", "%Y-%m-%d").date()
    assert timestepper.get_timestep_length() == datetime.timedelta(days=366)


def test_day_timestepper():
    timestepper = get_timestepper("2015-01-01", 7)
    timestepper.step_forward()
    assert timestepper.date.day == 8
    assert timestepper.date.month == 1


def test_invalid_timestepper():
    with pytest.raises(ValueError):
        get_timestepper("2016-0204", timestep="month")
    with pytest.raises(ValueError):
        get_timestepper("2016-02-04", timestep="blibble")
