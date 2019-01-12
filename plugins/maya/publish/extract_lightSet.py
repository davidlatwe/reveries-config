
import os
import contextlib

import pyblish.api

from reveries.plugins import PackageExtractor


class ExtractLightSet(PackageExtractor):
    """Export lights for rendering"""

    label = "Extract LightSet"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.lightset"]

    representations = [
        "LightSet"
    ]

    def extract_LightSet(self):

        from maya import cmds
        from avalon import maya
        from reveries.maya import capsule

        entry_file = self.file_name("ma")
        package_path = self.create_package(entry_file)

        # Extract lights
        #
        entry_path = os.path.join(package_path, entry_file)

        self.log.info("Extracting lights..")

        with contextlib.nested(
            maya.maintained_selection(),
            capsule.undo_chunk(),
            capsule.no_refresh(),
        ):
            # From texture extractor
            file_node_path = self.context.data.get("fileNodePath")
            if file_node_path is not None:
                # Change texture path to published location
                for file_node in cmds.ls(self.member, type="file"):
                    attr_name = file_node + ".fileTextureName"
                    final_path = file_node_path[file_node]

                    # Set texture file path to publish location
                    cmds.setAttr(attr_name, final_path, type="string")

            # Select full shading network
            # If only select shadingGroups, and if there are any node
            # connected to Dag node (i.e. drivenKey), then the command
            # will not only export selected shadingGroups' shading network,
            # but also export other related DAG nodes (i.e. full hierarchy)
            cmds.select(self.member,
                        replace=True,
                        noExpand=True)

            cmds.file(entry_path,
                      options="v=0;",
                      type="mayaAscii",
                      force=True,
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False)
