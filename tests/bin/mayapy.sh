#!/bin/bash
pythonpath=$PYTHONPATH
/usr/bin/docker exec -e PYTHONPATH=${pythonpath//$CONFIG_ROOT/$DCC_WORKDIR} maya mayapy $1 "$2"