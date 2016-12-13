# README #

This repository provides the simulation code for the Easterlin effect model in the Jason Hilton's PhD thesis.
The `run_sim.py` script allows the running of the simulation from the command line.


The `lhs_script.py` and the `lhs_script_from_csv.py` python scripts allow the creation of relevant input files for a generated Latin Hypercube Sample, or from a .csv file given on the command line.

The `intergen.pbs` file provides for running multiple simulation via iridis using pbsdsh.

To run a set of simulations defined by rows in a csv file, you would first run 
`python lhs_script_from_csv.py design.csv range.csv`

This instructs creates inputs parameter dictionaries based on the rows of the design.csv file, scaled up or down based on the range.csv file.

Then, the intergen.pbs file can be submitted to iridis via qsub. This script will call the run_sim.py python script repeatedly, running the simulation repeatedly for each input parameter file created in the previous step. The results are saved in dated folders in the "results" folder.

The simulation can also be run interactively via the simulation class.