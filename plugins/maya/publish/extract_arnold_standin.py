
import os
import json
import contextlib

import pyblish.api
import avalon.api
from reveries.plugins import PackageExtractor
from reveries.maya import capsule
from reveries import lib

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

    def extract_Ass(self, packager):
        from reveries.maya import arnold

        # Ensure option created
        arnold.utils.create_options()

        packager.skip_stage()
        package_path = packager.create_package()

        cache_file = packager.file_name("ass")
        cache_path = os.path.join(package_path, cache_file)

        self.log.info("Extracting standin..")

        texture = self.data.get("textureInstance")
        if texture is not None:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())
        else:
            file_node_attrs = dict()

        data = {
            "fileNodeAttrs": file_node_attrs,
            "member": self.member,
            "cachePath": cache_path,
        }
        data_path = os.path.join(package_path, ".remoteData.json")

        if lib.to_remote():
            self.data["remoteDataPath"] = data_path
            with open(data_path, "w") as fp:
                json.dump(data, fp, indent=4)

            return

        elif lib.in_remote():
            self.log.info("Stand-In exported via per-frame script.")

        else:
            self.export_ass(data,
                            self.data["startFrame"],
                            self.data["endFrame"],
                            self.data["byFrameStep"])

        entry_file = next(f for f in os.listdir(package_path)
                          if f.endswith(".ass"))

        use_sequence = self.data["startFrame"] != self.data["endFrame"]
        packager.add_data({"entryFileName": entry_file,
                           "useSequence": use_sequence})
        if use_sequence:
            packager.add_data({"startFrame": self.data["startFrame"],
                               "endFrame": self.data["endFrame"]})

    @staticmethod
    def export_ass(data, start, end, step):

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
            capsule.attribute_states(data["fileNodeAttrs"].keys(), lock=False),
            # Change to published path
            capsule.attribute_values(data["fileNodeAttrs"]),
            # Disable Auto TX update and enable to use existing TX
            capsule.attribute_values(arnold_tx_settings),
        ):
            cmds.select(data["member"], replace=True)
            asses = cmds.arnoldExportAss(filename=data["cachePath"],
                                         selected=True,
                                         startFrame=start,
                                         endFrame=end,
                                         frameStep=step,
                                         expandProcedurals=True,
                                         boundingBox=True,
                                         # Mask:
                                         #      Shapes,
                                         #      Shaders,
                                         #      Override Nodes,
                                         #      Operators,
                                         #
                                         # (NOTE): If Color Manager included,
                                         #         may raise error if rendering
                                         #         in Houdini or other DCC.
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
