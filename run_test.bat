
rem start miniconda, activate conda evnironment "avalon"
rem call condaenv activate avalon

rem set AVALON_PROJECTS=\workspace

pytest --cov reveries -k test_utils -s

mayapy -m pytest --cov reveries -k test_maya
