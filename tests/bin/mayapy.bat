@echo off

if not defined MAYA_VERSION (set MAYA_VERSION=2018)
set __ver__=%MAYA_VERSION:~0,4%
set __app__="Mayapy %__ver__%"
set __exe__="C:\Program Files\Autodesk\Maya%__ver__%\bin\mayapy.exe"
if not exist %__exe__% goto :missing_app

call %__exe__% %*

goto :eof

:missing_app
    echo ERROR: %__app__% not found at %__exe__%
    exit /B 1
