
import os
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import PackageExtractor


class ExtractMayaShare(PackageExtractor):
    """Extract as Maya Ascii"""

    label = "Extract MayaShare (mayaAscii)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.mayashare"]

    representations = [
        "mayaAscii",
    ]

    def extract_mayaAscii(self, instance):
        # Define extract output file path
        packager = instance.data["packager"]
        package_path = packager.create_package()

        entry_file = packager.file_name("ma")
        entry_path = os.path.join(package_path, entry_file)

        # Perform extraction
        self.log.info("Performing extraction..")
        with maya.maintained_selection():
            # Set flag `noExpand` to True for sharing containers,
            # which will be ignored if the selection expanded since
            # they are objectSets.
            cmds.select(instance, noExpand=True)
            cmds.file(entry_path,
                      force=True,
                      typ="mayaAscii",
                      exportSelected=True,
                      preserveReferences=True,
                      channels=True,
                      constraints=True,
                      expressions=True,
                      shader=True,
                      constructionHistory=True)

        packager.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=instance.data["subset"],
            path=entry_path)
        )
