
import os
import contextlib
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import PackageExtractor
from reveries.maya import capsule


class ExtractRig(PackageExtractor):
    """Extract rig as mayaBinary"""

    label = "Extract Rig (mayaBinary)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def extract_mayaBinary(self):
        # Define extract output file path
        entry_file = self.file_name("mb")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)

        # Perform extraction
        self.log.info("Performing extraction..")
        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(self.member),
            maya.maintained_selection(),
        ):
            cmds.select(self.member, noExpand=True)

            with capsule.undo_chunk_when_no_undo():
                # Remove loaded subset's namespace before exporting
                for namespace in self.context.data["loadedNamespace"]:
                    if not cmds.namespace(exists=namespace):
                        continue
                    cmds.namespace(removeNamespace=namespace,
                                   mergeNamespaceWithRoot=True)

                cmds.file(entry_path,
                          force=True,
                          typ="mayaBinary",
                          exportSelected=True,
                          preserveReferences=False,
                          channels=True,
                          constraints=True,
                          expressions=True,
                          constructionHistory=True)

        self.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )
