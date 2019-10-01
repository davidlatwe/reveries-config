
import os
import contextlib

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
        from reveries.maya import arnold

        # Ensure option created
        arnold.utils.create_options()

        package_path = self.create_package()
        cache_file = self.file_name("ass")
        cache_path = os.path.join(package_path, cache_file)

        self.log.info("Extracting shaders..")

        texture = self.data.get("textureInstance")
        if texture is not None:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())
        else:
            file_node_attrs = dict()

        arnold_tx_settings = {
            "defaultArnoldRenderOptions.autotx": False,
            "defaultArnoldRenderOptions.use_existing_tiled_textures": True,
        }

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_refresh(),
            capsule.evaluation("off"),
            capsule.maintained_selection(),
            capsule.ref_edit_unlock(),
            # (NOTE) Ensure attribute unlock
            capsule.attribute_states(file_node_attrs.keys(), lock=False),
            # Change to published path
            capsule.attribute_values(file_node_attrs),
            # Disable Auto TX update and enable to use existing TX
            capsule.attribute_values(arnold_tx_settings),
        ):
            cmds.select(self.member, replace=True)
            asses = cmds.arnoldExportAss(filename=cache_path,
                                         selected=True,
                                         startFrame=self.data["startFrame"],
                                         endFrame=self.data["endFrame"],
                                         frameStep=self.data["byFrameStep"],
                                         expandProcedurals=True,
                                         boundingBox=True,
                                         # Mask:
                                         #      Shapes,
                                         #      Shaders,
                                         #      Override Nodes,
                                         #      Operators,
                                         #
                                         # mask=6200,  # With Color Manager
                                         #
                                         mask=4152)  # No Color Manager

            # Change to environment var embedded path
            root = avalon.api.registered_root().replace("\\", "/")
            project = avalon.api.Session["AVALON_PROJECT"]

            for ass in asses:
                lines = list()
                has_change = False
                with open(ass, "r") as assf:
                    for line in assf.readlines():
                        if line.startswith(" filename "):
                            line = line.replace(root, "[AVALON_PROJECTS]", 1)
                            line = line.replace(project, "[AVALON_PROJECT]", 1)
                            has_change = True
                        lines.append(line)

                if has_change:
                    with open(ass, "w") as assf:
                        assf.write("".join(lines))

        use_sequence = self.data["startFrame"] != self.data["endFrame"]
        entry_file = os.path.basename(asses[0])

        self.add_data({"entryFileName": entry_file,
                       "useSequence": use_sequence})
        if use_sequence:
            self.add_data({"startFrame": self.data["startFrame"],
                           "endFrame": self.data["endFrame"]})
