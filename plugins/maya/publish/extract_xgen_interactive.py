
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

        package_dir = self.create_package()

        preset_files = list()
        bound_map = dict()
        clay_shader = "initialShadingGroup"
        descriptions = self.data["igsDescriptions"]
        with capsule.assign_shader(descriptions, shadingEngine=clay_shader):

            for description in descriptions:

                desc_id = utils.get_id(description)

                # Get bounded meshes
                bound_map[desc_id] = list()
                for mesh in lib.list_bound_meshes(description):
                    transform = cmds.listRelatives(mesh, parent=True)
                    id = utils.get_id(transform[0])
                    bound_map[desc_id].append(id)

                # This is short name
                desc_transform = cmds.listRelatives(description,
                                                    parent=True)[0]

                # Export preset
                # (NOTE) Saving as ext `.ma` instead of `.xgip` is because
                #        I'd like to use reference to load it later.
                #        Referencing file that was not `.ma`, `.mb` or other
                #        normal ext will crash Maya on file saving.
                relative = os.path.join("descriptions", desc_transform + ".ma")
                out_path = os.path.join(package_dir, relative)
                if not os.path.isdir(os.path.dirname(out_path)):
                    os.makedirs(os.path.dirname(out_path))

                io.export_xgen_IGS_preset(description, out_path)

                preset_files.append((relative, desc_transform))

        # Wrap preset files to one mayaAscii file
        entry_file = self.file_name("ma")
        entry_path = os.path.join(package_dir, entry_file)

        io.wrap_xgen_IGS_preset(entry_path, preset_files)

        # Parse preset bounding map
        link_file = self.file_name("json")
        link_path = os.path.join(package_dir, link_file)

        with open(link_path, "w") as fp:
            json.dump(bound_map, fp, ensure_ascii=False)

        self.add_data({
            "linkFname": link_file,
            "entryFileName": entry_file,
        })
