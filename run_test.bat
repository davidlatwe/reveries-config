
rem start miniconda, activate conda evnironment "avalon"
call condaenv activate avalon

set AVALON_PROJECTS=\workspace

pytest --cov reveries -k test_utils -s

mayapy -m pytest --cov reveries -k test_maya
