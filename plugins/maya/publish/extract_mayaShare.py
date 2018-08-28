
import os
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import PackageExtractor


class ExtractRig(PackageExtractor):
    """Extract as Maya Ascii"""

    label = "Extract MayaShare (mayaAscii)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.mayaShare"]

    representations = [
        "mayaAscii",
    ]

    def dispatch(self):
        self.extract()

    def extract_mayaAscii(self):
        # Define extract output file path
        entry_file = self.file_name("ma")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            cmds.select(self.member)
            cmds.file(entry_path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=True,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      constructionHistory=True)

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )
