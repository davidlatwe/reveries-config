
import pyblish.api
from maya import cmds
from avalon import maya
from reveries import utils


class ExtractMayaShare(pyblish.api.InstancePlugin):
    """Extract as Maya Ascii"""

    label = "Extract MayaShare (ma)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.mayashare"]

    def process(self, instance):

        staging_dir = utils.stage_dir()
        filename = "%s.ma" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        instance.data["repr.mayaAscii._stage"] = staging_dir
        instance.data["repr.mayaAscii._files"] = [filename]
        instance.data["repr.mayaAscii.entryFileName"] = filename

        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            # Set flag `noExpand` to True for sharing containers,
            # which will be ignored if the selection expanded since
            # they are objectSets.
            cmds.select(instance, noExpand=True)
            cmds.file(outpath,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=True,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      shader=True,
                      constructionHistory=True)
