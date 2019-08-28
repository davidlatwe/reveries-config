
import os
import contextlib
from collections import OrderedDict

import pyblish.api
import avalon.api
from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya import capsule

from maya import cmds


class ExtractArnoldStandIn(PackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Arnold Stand-In"
    families = [
        "reveries.standin"
    ]

    representations = [
        "Ass",
    ]

    @skip_stage
    def extract_Ass(self):
        # Ensure mtoa loaded
        cmds.loadPlugin("mtoa", quiet=True)

        package_path = self.create_package()
        cache_file = self.file_name("ass")
        cache_path = os.path.join(package_path, cache_file)

        root = avalon.api.registered_root()
        project = avalon.api.Session["AVALON_PORJECT"]

        file_node_attrs = OrderedDict()
        for node in self.data["fileNodes"]:
            # Embedding env var into file path
            attr = node + ".fileTextureName"
            path = cmds.getAttr(attr, expandEnvironmentVariables=True)
            if path.startswith(root):
                path = path.replace(root, "[AVALON_PROJECTS]", 1)
            if project in path:
                path = path.replace(project, "[AVALON_PROJECT]", 1)
            file_node_attrs[attr] = path

            # Preserve color space
            attr = node + ".colorSpace"
            color_space = cmds.getAttr(attr)
            file_node_attrs[attr] = color_space

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
            capsule.ref_edit_unlock(),
            # (NOTE) Force color space unlocked
            #        Previously we used to lock color space in case
            #        forgot to check it after changing file path.
            capsule.attribute_states(file_node_attrs.keys(), lock=False),
            # Change to .tx path
            capsule.attribute_values(file_node_attrs),
        ):
            cmds.select(self.member, replace=True)
            asses = cmds.arnoldExportAss(filename=cache_path,
                                         selected=True,
                                         startFrame=self.data["startFrame"],
                                         endFrame=self.data["endFrame"],
                                         frameStep=self.data["byFrameStep"],
                                         shadowLinks=1,
                                         lightLinks=1,
                                         expandProcedurals=True,
                                         mask=24)

        use_sequence = self.data["startFrame"] != self.data["endFrame"]
        entry_file = os.path.basename(asses[0])

        self.add_data({"entryFileName": entry_file,
                       "useSequence": use_sequence})
        if use_sequence:
            self.add_data({"startFrame": self.data["startFrame"],
                           "endFrame": self.data["endFrame"]})
