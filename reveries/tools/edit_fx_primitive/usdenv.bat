@echo off
echo off

call S:\_RD\BAT\miniconda_py37\src\avalon_env.bat
:: call E:\pipeline\USD\avalon_usd\usd_avalon_maya2.bat

call activate avalon

set USDFILEPATH=%1

set PATH=Q:\Resource\USD\lib;Q:\Resource\USD\bin;%PATH%
set PATH=T:\third-party\python27\;T:\third-party\python27\Scripts\;%PATH%

set PYTHONPATH=Q:\Resource\USD\lib\python\;%PYTHONPATH%

set SHOT_NAME=%2
:: set SHOT_NAME=SEQ01_SEQ01_Sh0200

set TEMP_DIR=%3
:: set TEMP_DIR=Q:\199909_AvalonPlay\Avalon\Shot\SEQ01_SEQ01_Sh0200\work\FX\fx_prim.usda

set AVALON_PROJECT=%4
set AVALON_PROJECTS=%5

set CONFIG_ROOT=%6
set PYTHONPATH=%CONFIG_ROOT%;%PYTHONPATH%

python %USDFILEPATH% shot_name=%SHOT_NAME% tmp_dir=%TEMP_DIR%
