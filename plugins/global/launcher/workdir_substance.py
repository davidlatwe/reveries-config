
import os
import sys
import subprocess

from avalon import api


def open(filepath):
    """Open file with system default executable"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


class WorkDirSubstance(api.Application):

    name = "substance"
    label = "Substance"
    icon = "crosshairs"
    color = "#E24024"
    order = 6

    config = {
        "application_dir": "substance",
        "default_dirs": [
            "wip",
            "export",
            "import",
            "maps",
        ]
    }

    def launch(self, environment):
        return open(environment["AVALON_WORKDIR"])
