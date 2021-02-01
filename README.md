# WDPM
The Wetland DEM Ponding Model (WDPM) was developed at the Centre for Hydrology at the University of Saskatchewan to model the spatial distribution of water in depressions in the Canadian Prairies.  

The program is described in 

Shook, K., J. W. Pomeroy, C. Spence, and L. Boychuk (2013), Storage dynamics simulations in prairie wetland hydrology models: evaluation and parameterization, Hydrol. Process., 27(13), 1875–1889, doi:10.1002/hyp.9867. 

Please cite all uses of the program.

Several presentations on using WDPM are available at https://research-groups.usask.ca/hydrology/modelling/wdpm.php.

## Folders and files

**src** - contains program source code files:

- WDPMCL.c - WDPM main line. Can be executed from the command line or from the GUI
- runoff.cl - OpenCL kernel which does the water smoothing
- WDPM.py - GUI for running the program. Written in Python 3.
- CMakeLists.txt - configuration file for building the program using cmake.
- cmap_black.sh - shell script for converting model output to an image on Linux or MacOS 
- cmap.bat - shell script for converting model output to an image on Windows  

**OpenCL_install** - contains scripts for installing OpenCL drivers

**dem** - contains a sample digital elevation model (DEM) for use with the WDPM:

- basin5.asc - DEM of sub-basin 5 at Smith Creek in SW Saskatchewan.

**paper** - contains files for the paper 'WDPM: the Wetland DEM Ponding Model'

**manual** - contains the user manual .pdf file as well as the document Lyx file and images used
