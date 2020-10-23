@echo off
echo off

set USDFILEPATH=%1
set PATH=Q:\Resource\USD\lib;Q:\Resource\USD\bin;%PATH%
set PATH=T:\third-party\python27\;T:\third-party\python27\Scripts\;%PATH%

set PYTHONPATH=Q:\Resource\USD\lib\python\;%PYTHONPATH%

echo ##  usd file path is %USDFILEPATH%

"Q:\Resource\USD\bin\usdview" %USDFILEPATH%