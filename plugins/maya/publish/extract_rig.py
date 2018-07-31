
import os
import pyblish.api

from maya import cmds
from avalon import maya
from reveries import pipeline


class ExtractRig(pyblish.api.InstancePlugin):
    """Extract rig as Maya Ascii"""

    label = "Extract Rig (Maya Binary)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    def process(self, instance):
        # Define extract output file path
        dirname = pipeline.temp_dir()
        filename = "{0}.mb".format(instance.name)
        path = os.path.join(dirname, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            cmds.select(instance, noExpand=True)
            cmds.file(path,
                      force=True,
                      typ="mayaBinary",
                      exportSelected=True,
                      preserveReferences=False,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)
        instance.data["stagingDir"] = dirname

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
