
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
        package_path = self.create_package()

        # Extract lights
        #
        entry_path = os.path.join(package_path, entry_file)

        self.log.info("Extracting lights..")

        # From texture extractor
        file_node_attrs = self.context.data.get("fileNodeAttrs", dict())

        with contextlib.nested(
            maya.maintained_selection(),
            capsule.attribute_values(file_node_attrs),
            capsule.no_refresh(),
        ):
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

        self.add_data({
            "entryFileName": entry_file,
        })
