#!/bin/bash
startingDir=$PWD
# remove spaces from path

# creates color map from water applied to DEM
infile=$1
outfile="${infile%.*}"
gdaldem color-relief $infile "$startingDir"/colormap_black.txt -OF png $outfile".png"
# delete superfluous xml file
rm $outfile".png.aux.xml"
