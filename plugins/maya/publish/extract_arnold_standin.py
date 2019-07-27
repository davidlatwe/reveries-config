
import os
import contextlib
from collections import OrderedDict

import pyblish.api
from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya import capsule

from maya import cmds


def to_tx(path):
    return os.path.splitext(path)[0] + ".tx"


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

        file_node_attrs = OrderedDict()
        for node in self.data["fileNodes"]:
            attr = node + ".fileTextureName"
            path = cmds.getAttr(attr, expandEnvironmentVariables=True)
            file_node_attrs[attr] = to_tx(path)

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
