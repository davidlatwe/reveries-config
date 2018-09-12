#!/bin/bash
/usr/bin/docker exec -e PYTHONPATH=$PYTHONPATH maya mayapy $1 "$2"