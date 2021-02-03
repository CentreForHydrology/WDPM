@echo off
"gdaldem.exe" color-relief %1 colormap_black.txt -OF png %~p1%~n1".png"
del %~p1%~n1".png.aux.xml"
