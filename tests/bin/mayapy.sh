#!/bin/bash
/usr/bin/docker exec -e PYTHONPATH=${$PYTHONPATH//$CONFIG_ROOT/$DCC_WORKDIR} maya mayapy $1 "$2"