
import os
import json
import pyblish.api
from reveries.plugins import PackageExtractor
from reveries.maya import io, lib, utils, capsule


class ExtractXGenInteractive(PackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Interactive Groom"
    families = [
        "reveries.xgen.interactive",
    ]

    representations = [
        "XGenInteractive",
    ]

    def extract_XGenInteractive(self):
        from maya import cmds

        entry_file = self.file_name("json")
        package_dir = self.create_package()
        entry_path = os.path.join(package_dir, entry_file)

        bound_map = dict()
        clay_shader = "initialShadingGroup"
        descriptions = self.data["igsDescriptions"]
        with capsule.assign_shader(descriptions, shadingEngine=clay_shader):

            for description in descriptions:

                # Get bounded meshes
                bound_map[description] = list()
                for mesh in lib.list_bound_meshes([description]):
                    transform = cmds.listRelatives(mesh, parent=True)
                    id = utils.get_id(transform)
                    bound_map[description].append(id)

                # Export preset
                # (NOTE) Saving as ext `.ma` instead of `.xgip` is because
                #        I'd like to use reference to load it later.
                #        Referencing file that was not `.ma`, `.mb` or other
                #        normal ext will crash Maya on file saving.
                out_path = os.path.join(package_dir, description + ".ma")
                io.export_xgen_IGS_preset(description, out_path)

        # Parse preset bounding map
        with open(entry_path, "w") as fp:
            json.dump(bound_map, fp, ensure_ascii=False)

        self.add_data({
            "entryFileName": entry_file,
        })
