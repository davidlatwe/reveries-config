
import os
import pyblish.api
import reveries.base

from maya import cmds
from avalon import maya


class ExtractRig(reveries.base.BaseExtractor):
    """Extract rig as mayaBinary"""

    label = "Extract Rig (mayaBinary)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    representations = [
        reveries.base.repr_obj("mayaBinary", "mb")
    ]

    def dispatch(self):
        self.extract()

    def extract_mayaBinary(self, representation):
        # Define extract output file path
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            cmds.select(self.member, noExpand=True)
            cmds.file(out_path,
                      force=True,
                      typ=representation,
                      exportSelected=True,
                      preserveReferences=False,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        self.stage_files(representation)

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=out_path)
        )
