"""
Module to allow the definition of simulation experiments, based on a specification of
default parameters, a set of variable parameters and ranges for these.

Different experimental designs are permitted.


"""
# TODO think about varying switches
# TODO use pandas everywhere to maintain explicit link between 
# columns and column names.
from __future__ import division
import os
import csv

import pyDOE
import yaml
import numpy as np
import itertools

import random as rnd

from .utils import get_changed_params


# TODO give an interface which returns the upper and lower boundaries for a given
# parameter.
class Parameters(object):
    """
    Defines parameters names, central/default values and sensible ranges
    """
    def __init__(self, default_params, variable_param_ranges=None):
        self.default_params = default_params
        try:
            self.varied = variable_param_ranges.keys()
            self.ranges = variable_param_ranges
        except AttributeError:
            # this implies we have only a single run
            # should all be considered varied, or none?
            # this could be more explicit somehow.
            self.varied = None
            self.ranges = None

    @classmethod
    def from_files(cls, default_param_file, variable_param_ranges_file):
        default_stream = open(default_param_file)
        default_params = yaml.load(default_stream)
        default_stream.close()

        ranges_stream = open(variable_param_ranges_file)
        varied_param_ranges = yaml.load(ranges_stream)
        ranges_stream.close()
        return cls(default_params, varied_param_ranges)

    def write_range_to_csv(self, out_dir):
        try:
            os.mkdir(os.path.join(out_dir, "params"))
        except OSError:
            pass
        try:
            with open(os.path.join(out_dir, "params", 'range.csv'), 'wb') as f:
                range_writer = csv.writer(f)
                range_writer.writerow(self.varied)
                range_writer.writerow([self.ranges[par]["lower"] for par in self.varied])
                range_writer.writerow([self.ranges[par]["upper"] for par in self.varied])
        except:
            # python 2/3 compatibility problem
            # both TypeError and _csv_error expected.
            with open(os.path.join(out_dir, "params", 'range.csv'), 'w') as f:
                range_writer = csv.writer(f)
                range_writer.writerow(list(self.varied))
                range_writer.writerow([self.ranges[par]["lower"] for par in self.varied])
                range_writer.writerow([self.ranges[par]["upper"] for par in self.varied])


class Experiment(object):
    """
    Generates experiments for a simulation model
    """
    def __init__(self, design_points, parameters, unit_design=None):
        """

        """
        # Todo maybe create different intialisations for each design type.
        self.parameters = parameters
        self.design_points = design_points

        self.unit_design = unit_design
        try:
            self.scaled_design = self.scale_design(unit_design, parameters)
        except AttributeError:
            pass
        self.Vdesign = None

    @classmethod
    def single_design_point(cls, param_dict, repetitions=1):
        """
        Create an experiment object with a single design point from a dictionary
        """
        # should check that all the relevant keys are present?
        design_points = [DesignPoint(param_dict, number=1, repetitions=1)]
        parameters = Parameters(param_dict)

        return cls(design_points, parameters)

    @classmethod
    def create_from_table(cls, design, repetitions, parameters):
        """
        Create an experiment from design specifed in a csv file. 

        Parameters
        ----------
        design: np.array
            array containing design

        repetitions: int or iterable of ints
            Gives the number of repetitions to be used at each point. Either an int,
            in which case the same number of repeats will be conducted at each point,
            or alternatively a iterable specifying repetitions for each point individually.
            In this case the iterable must be the same length as the number of rows in the design

        """

        scaled_design = cls.scale_design(design, parameters)
        design_points = cls.get_design_points(scaled_design, parameters, repetitions)
        return cls(design_points, parameters, design)


    @classmethod
    def create_lhs(cls, n_points, parameters, repetitions):
        """
        Create a latin Hypercube sample of the varied parameters.
        
        Parameters
        ----------
        n_points: int
            number of points to be included in the design.

        parameters: Parameter instance
            Class of type parameters detailing the parameters to be varied and the
            range of these parameters.

        repetitions: int or iterable of ints
            Gives the number of repetitions to be used at each point. Either an int,
            in which case the same number of repeats will be conducted at each point,
            or alternatively a iterable specifying repetitions for each point individually.
            In this case the iterable must be the same length as the number of points
            requested

        Returns
        -------
        Experiment instance with Latin Hypercube sample design points.
        """
        num_pars = len(parameters.varied)
        # first create a design in [0,1] space
        design = pyDOE.lhs(n=num_pars, samples=n_points, criterion="maximin")
        # now scale it up to lie in the correct range
        scaled_design = cls.scale_design(design, parameters)
        design_points = cls.get_design_points(scaled_design, parameters, repetitions)
        return cls(design_points, parameters, design)


    def add_validation_points(self, parameters, n_points):
        num_pars = len(parameters.varied)
        Vdesign = pyDOE.lhs(n=num_pars, samples=50)
        Vscaled_design = self.scale_design(Vdesign, parameters)
        self.Vdesign_points = self.get_design_points(Vscaled_design, parameters,
                                                     start_number=len(self))
        self.Vdesign = Vdesign




    @classmethod
    def get_design_points(cls, scaled_design, parameters, reps=1, start_number=0):
        """
        Convert an array like representation of the experimental design to
        a list of DesignPoints.
        Start number allows a second set of points to be given unique design points
        starting from where the first set started off, eg for validation.
        """
        design_points = []
        try:
            assert len(reps) == scaled_design.shape[0]
            reps = iter(reps)
        except TypeError:
            reps = itertools.repeat(reps)
        if hasattr(scaled_design, "columns"):
            row_dicts = scaled_design.to_dict("records")
            for number, row_dict in enumerate(row_dicts):
                params = parameters.default_params.copy()
                params.update(row_dict)
                seed = rnd.randint(1, 10000000)
                design_points.append(DesignPoint(params, repetitions=next(reps),
                                             number=number + start_number,
                                             seed=seed))
        for number, point in enumerate(scaled_design):
            params = cls.gen_dict_from_point(parameters, point)
            seed = rnd.randint(1, 10000000)
            design_points.append(DesignPoint(params, repetitions=next(reps),
                                             number=number+start_number,
                                             seed=seed))
        return design_points

    @staticmethod
    def scale_design(unit_design, parameters):
        """
        Take a design defined on [0,1] and scale so it is bounded by the ranges
        defined by parameters.ranges
        """
        scaled_design = unit_design.copy()

        if hasattr(unit_design, "columns"):
            # is a pandas array
            for parameter in parameters.varied:
                scaled_design[parameter] = scale_up(unit_design[parameter],
                                                parameters.ranges[parameter]["lower"],
                                                parameters.ranges[parameter]["upper"])
        else:
            for col, parameter in enumerate(parameters.varied):
                scaled_design[:, col] = scale_up(unit_design[:, col],
                                                 parameters.ranges[parameter]["lower"],
                                                 parameters.ranges[parameter]["upper"])
        return scaled_design

    @staticmethod
    def gen_dict_from_point(parameters, point):
        """
        Creates a copy of the default_params dictionary, and replaces the values of
        the varied_params with the values in the iterable point.
        """
        params = parameters.default_params.copy()
        for param, value in zip(parameters.varied, point):
            params[param] = value
        return params

    @classmethod
    def create_parameter_sweep(cls, n_points_per_param, parameters, reps=1):
        """
        Sweep through each of the varied parameters in turn
        keeping everything else constant at its mean point.
        """
        dims = len(parameters.varied)

        # first create a design in the unit space
        # start by varying just one parameter
        midpoint = 0.5
        varied_points = np.linspace(0, 1, n_points_per_param)
        initial_design = np.full(shape=(n_points_per_param, dims),
                                 fill_value=midpoint)

        initial_design[:, 0] = varied_points
        # repeat this design over all parameters by permuting columns and concatenating
        index_pattern = [0]
        index_pattern.extend([1] * (dims-1))
        design = np.concatenate([initial_design[:, perm] for perm in
                                list(set(itertools.permutations(index_pattern)))])
        # remove duplicates
        design = unique_rows(design)
        scaled_design = cls.scale_design(design, parameters)
        design_points = cls.get_design_points(scaled_design, parameters, reps)
        return cls(design_points, parameters, design)

    def __iter__(self):
        """
        return the next design point
        """
        # could this just be return iter(self.design_points) ? 
        index = 0
        while index < len(self):
            yield self.design_points[index]
            index += 1

    def __len__(self):
        """
        number of design points in the experiment
        """
        return len(self.design_points)

    def write_params_yamls(self, outdir):
        """
        Write out the design points as yaml files to be read by a command line
        script
        """
        for point in self.design_points:
            point.write_parameters_to_yaml(outdir)
        for point in self.Vdesign_points:
            point.write_parameters_to_yaml(outdir)

    def write_pbs_file(self, walltime, processors):
        """
        Write a pbs file ???
        """

    def write_design_to_csv(self, out_dir):
        """
        Write design and validation design to csv.
        """
        param_dir = os.path.join(out_dir, "params")
        try:
            os.mkdir(param_dir)
        except OSError:
            pass
        header = ",".join(self.parameters.varied)
        np.savetxt(os.path.join(param_dir, "design.csv"),
                   self.unit_design, delimiter=",", header=header)

        try:
            np.savetxt(os.path.join(param_dir, "Vdesign.csv"),
                       self.Vdesign, delimiter=",", header=header)
        except TypeError:
            pass



class DesignPoint(object):
    """
    Represents a single design point in an experiment.
    This design point may have multiple repetitions.
    It also has a unique number distinguishing it from other points.
    """
    def __init__(self, params, repetitions=1, number=1, seed=None):

        self.params = params
        self.repetitions = repetitions
        self.number = number
        self.seed = seed
        try:
            self.seed_it = iter(seed)
        except TypeError:
            self.seed_it = itertools.repeat(seed)

    def next_seed(self):
        """
        Get seed for this run.
        Note that this is different for each repetition.
        And it may be that no seed is given
        """
        return next(self.seed_it)

    def varied_params_points(self):
        """
        """
        # allow for returning only the varied parameters
        # could pass parameters object ? 
        raise NotImplementedError

    def scaled_points(self):
        """
        """
        # return points in [0,1] space
        # could pass parameters object ? 
        raise NotImplementedError

    def csv_repr(self):
        """
        """
        raise NotImplementedError

    def write_parameters_to_yaml(self, directory):
        """
        Write out the parameters for this design point to yaml format
        This is mostly useful for parallelisation, as it means each design point 
        has a separate input file and can be run independently.

        The number of repetitions at this design point is added to the dictionary
        in order that this information is preserved.
        """
        filename = "params" + "_" + "{0:03d}".format(self.number) + ".yaml"
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
        param_stream = open(file_path, mode="w")
        param_out = self.params.copy()
        param_out["repetitions"] = self.repetitions
        param_out["seed"] = self.seed
        yaml.dump(param_out, param_stream, default_flow_style=False)


def scale_up(points, lower, upper):
    """
    Scales point vector from design space [0,1] to parameter space [lower,upper]
    """
    width = upper-lower
    scaled = points * width + lower
    return scaled


def scale_down(points, lower, upper):
    """
    Scales point vector from parameter space [lower,upper] to design space [0,1]
    """
    width = upper-lower
    unit = (points - lower) / width
    return unit


def unique_rows(a):
    """
    Given a 2d numpy array return only the unique rows.
    Based on Stackoverflow answer here:    
    http://stackoverflow.com/questions/8560440/
    removing-duplicate-columns-and-rows-from-a-numpy-2d-array
    """
    # sort the array rows lexically
    order = np.lexsort(a.T)
    a_ordered = a[order]
    # get the difference  between each row and it's predecessor
    diff = np.diff(a_ordered, axis=0)
    # produce a boolean array the same length as the rows
    ui = np.ones(len(a_ordered), 'bool')
    # place a false in the array if the row was the same as predecessor
    # ie if all are zero
    # note the first item is kept automatically.
    ui[1:] = (diff != 0).any(axis=1) 
    return a[sorted(order[ui])]
