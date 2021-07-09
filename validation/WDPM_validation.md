## WDPM validations scripts

These scripts are provided to validate the output of WDPM by testing
values in the water state files output by the program's modules against pre-defined
values. The validation tests are not intended to be a substitute for unit testing,
but they do provide some confirmation that the program is running correctly. Note
that the scripts require WDPM to have been built, as is documented in the manual 
![WDPMUserGuide_2.pdf](https://github.com/CentreForHydrology/WDPM/blob/master/manual/WDPMUserGuide_2.pdf).

The scripts are written in Bash and awk. They have been tested on Linux and MacOS
and should work with other POSIX-compliant operating systems, but they
may require some modifications to run under Windows.

The main script is `validate_WDPM.sh` and can be run from the command
line  like any other Bash script. This script runs WDPM using the
add, subtract, and drain modules.  Following each of the WDPM runs, the
appropriate awk script (`add_test.awk`, `drain_test.awk`, or
`subtract_test.awk`) is run to test the program output.

The WDPM modules and the testing scripts are described below. 

###Add
The Add module adds 10 mm of water to the initially empty DEM. This
is the only module where conservation of mass can be assessed without
using a specified value. The volume of water that _should_ be present after
the model run is the depth of water multiplied by the number of cells that
are not masked (i.e., those that have elevations > 0).

In addition, the total depth of water in a very small depression (2
rows x 3 columns) is also computed and compared against a previously
established value.


###Drain
The Drain module allows water added in the previous run to exit from
the lowest point in the DEM. The total volume remaining after the run
is compared with a specified value. The depth of water in the
previously specified water depression is also tested. Note that this
value should _not_ have been altered by the drain module because this
depression is not part of the stream network. The third test checks
that the depth of water at the outlet is zero.

###Subtract
The Subtract module removes 10 mm of water from the drained water. The
remaining volume of water is compared against a specified value. The
depth of water remaining in the depression is also checked against a
specified value. Because the depression consists of 6 elements, the
depth of water remaining after this step should be 0.06 m smaller than
after the Add and Drain modules.

The awk scripts write their output to the file `WDPM_validation.txt`.


