
import os
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import repr_obj, BaseExtractor


class ExtractRig(BaseExtractor):
    """Extract as Maya Ascii"""

    label = "Extract MayaShare (mayaAscii)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.mayaShare"]

    representations = [
        repr_obj("mayaAscii", "ma")
    ]

    def dispatch(self):
        self.extract()

    def extract_mayaAscii(self, representation):
        # Define extract output file path
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            cmds.select(self.member)
            cmds.file(out_path,
                      force=True,
                      typ=representation,
                      exportSelected=True,
                      preserveReferences=True,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        self.stage_files(representation)

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=out_path)
        )
