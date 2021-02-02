
import sys
import os
import shutil
import subprocess
import pyblish.api
from reveries import plugins


def open(filepath):
    """Open file with system default executable"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))


class SelectInvalidNodes(plugins.HoudiniSelectInvalidInstanceAction):

    label = "Select ROP Node"
    symptom = "node"


class OpenStagingDirs(plugins.RepairInstanceAction):

    label = "Open Folder"
    symptom = "by_open"


class CleanUpStagingDirs(plugins.RepairInstanceAction):

    label = "Delete Files"
    symptom = "by_remove"


class ValidateCleanStage(pyblish.api.InstancePlugin):
    """Ensure empty staging dir"""

    order = pyblish.api.ValidatorOrder + 0.11
    label = "Clean Stage Dir"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
        "reveries.pointcache",
        "reveries.standin",
        "reveries.rsproxy",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalidNodes,
        OpenStagingDirs,
        pyblish.api.Category("Quick Fix"),
        CleanUpStagingDirs,
    ]

    def process(self, instance):
        ropnode = instance[0]
        staging_dir = self.get_staging_dir(ropnode)
        if os.path.isdir(staging_dir) and os.listdir(staging_dir):
            raise Exception("Staging dir not empty, please clean up.")

    @classmethod
    def get_staging_dir(cls, ropnode):
        from reveries.houdini import lib
        output_parm = lib.get_output_parameter(ropnode)
        output = output_parm.eval()

        return os.path.dirname(output)

    @classmethod
    def get_invalid_node(cls, instance):
        invalid = list()
        ropnode = instance[0]
        staging_dir = cls.get_staging_dir(ropnode)
        if os.path.isdir(staging_dir) and os.listdir(staging_dir):
            invalid.append(ropnode)

        return invalid

    @classmethod
    def fix_invalid_by_open(cls, instance):
        ropnode = instance[0]
        staging_dir = cls.get_staging_dir(ropnode)
        if os.path.isdir(staging_dir) and os.listdir(staging_dir):
            open(staging_dir)

    @classmethod
    def fix_invalid_by_remove(cls, instance):
        ropnode = instance[0]
        staging_dir = cls.get_staging_dir(ropnode)
        if os.path.isdir(staging_dir):
            shutil.rmtree(staging_dir)
