
import os
import contextlib

import pyblish.api
import avalon.api
from reveries import plugins
from reveries.maya import capsule

from maya import cmds, mel


class ExtractArnoldStandIn(plugins.PackageExtractor):
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

        packager.skip_stage()
        package_path = packager.create_package()

        cache_file = packager.file_name("ass")
        cache_path = os.path.join(package_path, cache_file)

        start = self.data["startFrame"]
        end = self.data["endFrame"]

        entry_file = packager.file_name(suffix=".%04d" % start,
                                        extension="ass")

        use_sequence = start != end
        if use_sequence:
            packager.add_data({"startFrame": start, "endFrame": end})
        packager.add_data({"entryFileName": entry_file,
                           "useSequence": use_sequence})

        self.log.info("Extracting standin..")

        nodes = self.member

        try:
            texture = next(chd for chd in self.data.get("childInstances", [])
                           if chd.data["family"] == "reveries.texture")
        except StopIteration:
            file_node_attrs = dict()
        else:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())

        self.export_ass(file_node_attrs,
                        nodes,
                        cache_path,
                        has_yeti=self.data.get("hasYeti", False),
                        start=self.data["startFrame"],
                        end=self.data["endFrame"],
                        step=self.data["byFrameStep"])

    def export_ass(self,
                   file_node_attrs,
                   nodes,
                   cache_path,
                   has_yeti,
                   start,
                   end,
                   step):
        from reveries.maya import arnold

        # Ensure option created
        arnold.utils.create_options()

        arnold_tx_settings = {
            "defaultArnoldRenderOptions.autotx": False,
            "defaultArnoldRenderOptions.use_existing_tiled_textures": True,
        }

        # Yeti
        if has_yeti:
            # In Deadline, this is a script job instead of rendering job, so
            # the `pgYetiPreRender` Pre-Render MEL will not be triggered.
            # We need to call it by ourselve, or Yeti will complain about
            # cache temp dir not exist.
            mel.eval("pgYetiPreRender;")

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
            cmds.select(nodes, replace=True)
            asses = cmds.arnoldExportAss(filename=cache_path,
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
                                         # mask=4152,  # No Color Manager
                                         mask=6200)  # With Color Manager

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

                # Remove color manager
                # (NOTE): If Color Manager included,
                #         may raise error if rendering
                #         in Houdini or other DCC.
                try:
                    s = lines.index("color_manager_syncolor\n")
                except ValueError:
                    # No color manager found
                    pass
                else:
                    e = lines.index("}\n", s) + 1
                    lines = lines[:s] + lines[e:]
                    has_change = True

                # Re-write
                if has_change:
                    with open(ass, "w") as assf:
                        assf.write("".join(lines))
