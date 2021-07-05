#!/bin/bash
# BASH script to vaidate WDPM
# (c) Kevin Shook, 2021
# Distributed under GPL version 3.0

# This script runs WDPM version 2.0, testing the add, drain and subtract modules. 

# The script runs each module in turn. After running each module, the output water state file
# is tested to ensure that the results are as they should be. 
# Note that tolerences are used in the comparison of the floating point output from
# WDPM with the specified values.

# Most of the parameters are marked 'do not change'. Altering these parameters will cause the program
# output to be changed to values that are not expected.

# Set up file names and locations - can be changed if required
WDPMloc="../src/"
demloc="../dem/"
awk_script_loc="./"
logfile="WDPM_validation.txt"

# Volume testing tolerance - can be changed 
vol_tolerance=0.0001                # 0.01% of applied volume

# The following variables set the WDPM runs - do NOT change them
outputloc=$(pwd)
run_type=1                          # parallel
parallel_type=0                     # CPU
runoff_frac=1.0                     # 100% runof
zero_thresh=0.005                   # mm
iter_limit=0                        # no limit
add_depth=10                        # depth (mm) to be added 
subtract_depth=10                   # depth (mm) to be removed 

# Set up variables for awk scripts - do NOT change them

# Set water patch location parameters
patch_top=268
patch_left=59
patch_bottom=269
patch_right=61

# set add parameters
awk_add_test="add_test.awk"
add_patch_depth=0.420810            # total depth of water in patch (m)
add_elev_tol=1.0                    # tolerance for adding water (mm)

# set drain parameters
awk_drain_test="drain_test.awk"
specified_drain_vol=97577.54        # volume after draining (m3)
drain_col=468                       # column of outlet
drain_row=333                       # row of outlet
drain_patch_depth=0.420810          # total depth of water in patch (m)
drain_elev_tol=0.1                  # drainage elevation tolerance (mm)
drain_vol_tol=1.0                   # drainage volume tolerance (m3)

# set subtract module parameters
awk_subtract_test="subtract_test.awk"
specified_subtract_vol=86762.40     # volume after subtracting (m3)
subtract_patch_depth=0.360810       # total depth of water in patch (m)

# test Add module
current_dir=$(pwd)                  # record current directory
cd $WDPMloc                         # change to directory with WDPM executable
echo "Run WDPM add module"
echo "==================="
./WDPMCL add $demloc"basin5.asc" NULL $outputloc"/"$add_depth"_0_undrained.asc" NULL $add_depth $runoff_frac $add_elev_tol $run_type $parallel_type $zero_thresh $iter_limit | tee $outputloc"/"$add_depth"_0_undrained.txt"
cd $current_dir                     # change back to original directory

# run awk script to test output
awk -f $awk_add_test -v add_depth=$add_depth -v vol_tolerance=$vol_tolerance -v patch_top=$patch_top -v patch_bottom=$patch_bottom -v patch_left=$patch_left -v patch_right=$patch_right -v specified_patch_depth=$add_patch_depth $outputloc"/"$add_depth"_0_undrained.asc" | tee $logfile

# test Drain module
cd $WDPMloc                         # change to directory with WDPM executable
echo
echo "Run WDPM drain module"
echo "====================="
./WDPMCL drain $demloc"basin5.asc" $outputloc"/"$add_depth"_0_undrained.asc" $outputloc"/"$add_depth"_0_drained.asc" NULL $drain_elev_tol $drain_vol_tol $run_type $parallel_type $zero_thresh $iter_limit | tee $outputloc"/"$add_depth"_0_drained.txt"
cd $current_dir                     # change back to original directory

# run awk script to test output
awk -f $awk_drain_test -v specified_drain_vol=$specified_drain_vol -v drain_row=$drain_row -v drain_col=$drain_col -v vol_tolerance=$vol_tolerance -v patch_top=$patch_top -v patch_bottom=$patch_bottom -v patch_left=$patch_left -v patch_right=$patch_right -v specified_patch_depth=$drain_patch_depth $outputloc"/"$add_depth"_0_drained.asc" | tee -a $logfile

# test Subtract module
cd $WDPMloc                         # change to directory with WDPM executable
echo
echo "Run WDPM subtract module"
echo "==================="
./WDPMCL subtract $demloc"basin5.asc" $outputloc"/"$add_depth"_0_drained.asc" $outputloc"/"$add_depth"_"$subtract_depth"_drained.asc" NULL $subtract_depth $runoff_frac $subtract_elev_tol $run_type $parallel_type $zero_thresh $iter_limit | tee $outputloc"/"$add_depth"_"$subtract_depth"_drained.txt"
cd $current_dir             # change back to original directory

# run awk script to test output
awk -f $awk_subtract_test -v specified_subtract_vol=$specified_subtract_vol= -v vol_tolerance=$vol_tolerance -v patch_top=$patch_top -v patch_bottom=$patch_bottom -v patch_left=$patch_left -v patch_right=$patch_right -v specified_patch_depth=$subtract_patch_depth $outputloc"/"$add_depth"_"$subtract_depth"_drained.asc" | tee -a $logfile



