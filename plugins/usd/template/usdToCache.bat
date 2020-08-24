@echo off
echo off

set MAYA_MODULE_PATH=Q:\Resource\maya-usd_2020\install\RelWithDebInfo;%MAYA_MODULE_PATH%

set PY_FILE=%1
:: set PY_FILE="F:\usd\test\usd_avalon\reveries-config\plugins\usd\houdini\publish\extract_setdress_prim.py"

set USD_FILE=%2
:: set USD_FILE="Q:\199909_AvalonPlay\Avalon\Shot\SEQ01_SEQ01_Sh0100\work\layout\houdini\scenes\pyblish\envDefault\env_prim.usda"

"C:\Program Files\Autodesk\Maya2020\bin\mayapy.exe" %PY_FILE% usd_path=%USD_FILE%
