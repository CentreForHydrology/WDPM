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
- requirements.txt - file containing libraries required by WDPM.py 


**dem** - contains a sample digital elevation model (DEM) for use with the WDPM:

- basin5.asc - DEM of sub-basin 5 at Smith Creek in SW Saskatchewan.

**paper** - contains files for the paper 'WDPM: the Wetland DEM Ponding Model'

**manual** - contains the user manual **WDPMUserGuide_2.pdf** as well as the document Lyx file and images used


## Program requirements

The WDPM requires the use of other programs in order to work properly.
- Python 3 and the wxPython library are required to run the GUI, 
- OpenCl drivers are required to use parallel processing,
- gdaldem is required to create maps of water distribution.

Compilation of the WDPM and installation of the other required software are described in the manual **WDPMUserGuide_2.pdf**.


