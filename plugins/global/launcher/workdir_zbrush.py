
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


class WorkDirZBrush(api.Application):

    name = "zbrush"
    label = "ZBrush"
    icon = "circle"
    color = "#C8AAA6"
    order = 5

    config = {
        "application_dir": "zbrush",
        "default_dirs": [
            "wip",
            "export",
            "import",
            "maps",
        ]
    }

    def launch(self, environment):
        return open(environment["AVALON_WORKDIR"])
