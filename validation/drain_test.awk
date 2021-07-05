#!/usr/bin/awk -f 
# Tests results of WDPM drain module
# (c) Kevin Shook, 2021
# Distributed under GPL version 3.0

function abs(x){
   if (x > 0)
   return x;
   return x * -1;
}
BEGIN {
total_volume=0;
cell_count=0;
water_count=0;
patch_depth=0;

}
{
# First, get header info
if (NR<=6) {
 if ($1 == "NCOLS")
  ncol = $2;

 if ($1 == "NROWS")
  nrow = $2;

 if ($1 == "CELLSIZE")
  cellsize = $2;

 if ($1 == "NODATA_VALUE")
  nodata = $2;
  
} else {
  for(i=1;i<=NF;i++){
    # get total volume of water and cells not masked
    if ($i >= 0){
      total_volume = total_volume + ($i * cellsize * cellsize);
      cellcount++;


    # get total volume of water in patch
    if((i >= patch_left) && (i <= patch_right) && (NR >= patch_top) && (NR <= patch_bottom)) {
       patch_depth += $i;
     }
    # get outlet depth
    if((i >= drain_col) && (NR >= drain_row)) {
       drain_depth = $i;
     }
    } 
  }
 }
}
END {

vol_error=abs(total_volume - specified_drain_vol) / specified_drain_vol;
patch_depth_error=abs(patch_depth - specified_patch_depth) / specified_patch_depth;

print("");
print("Drain module test");
print("=================");
if (vol_error <= vol_tolerance)
  print("Final water volume error = ", vol_error*100, "%: water volume test passed");
else
  print("Final water volume error = ", vol_error*100, "%: water volume test failed");

if (patch_depth_error <= vol_tolerance)
  print("Patch depth error = ", patch_depth_error*100, "%: water patch depth test passed");
else
  print("Patch depth error = ", patch_depth_error*100, "%: water patch depth test failed");

if (drain_depth <= 0.1)
  print("Drain depth = ", drain_depth, "mm: drain depth test passed");
else
  print("Drain depth = ", drain_depth, "mm: drain depth test failed");
}
