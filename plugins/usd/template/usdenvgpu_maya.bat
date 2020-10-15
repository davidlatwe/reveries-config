@echo off
echo off

::set USDFILEPATH=%1
set MAYA_MODULE_PATH=Q:\Resource\maya-usd_2020\install\RelWithDebInfo;%MAYA_MODULE_PATH%

::echo ##  usd file path is

set USD_FILE=%2
set USD_FILE="Q:\199909_AvalonPlay\Avalon\Shot\SEQ01_SEQ01_Sh0100\work\layout\houdini\scenes\pyblish\envDefault\env_prim.usda"


"C:\Program Files\Autodesk\Maya2020\bin\mayapy.exe" "F:\usd\test\usd_avalon\reveries-config\plugins\usd\houdini\publish\extract_env_prim.py" usd_path=%USD_FILE%