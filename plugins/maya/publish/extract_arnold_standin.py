
import os
import contextlib
from collections import OrderedDict

import pyblish.api
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

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
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
