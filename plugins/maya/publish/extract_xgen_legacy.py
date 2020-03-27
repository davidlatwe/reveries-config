
import os
import shutil
import pyblish.api
from reveries import utils
from reveries.maya import io, utils as maya_utils
from reveries.maya.xgen import legacy as xgen
from maya import cmds


class ExtractXGenLegacy(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract XGen Legacy"
    families = [
        "reveries.xgen.legacy",
    ]

    def process(self, instance):

        staging_dir = utils.stage_dir()

        files = list()
        xgen_files = list()
        descriptions_data = dict()

        for desc in instance.data["xgenDescriptions"]:
            palette = xgen.get_palette_by_description(desc)

            # Save UUID and bounding
            descriptions_data[desc] = {
                "id": maya_utils.get_id(desc),
                "bound": xgen.list_bound_geometry(desc),
            }

            # Stage maps
            map_stage = staging_dir + "/maps/%s" % palette
            if not os.path.isdir(map_stage):
                os.makedirs(map_stage)

            for src in xgen.maps_to_transfer(desc):
                if os.path.isfile(src):
                    ship = shutil.copy2
                elif os.path.isdir(src):
                    ship = shutil.copytree
                else:
                    continue
                try:
                    ship(src, map_stage)
                except OSError:
                    msg = "An unexpected error occurred."
                    self.log.critical(msg)
                    raise OSError(msg)

            for root, _, files in os.walk(map_stage):
                relative = os.path.relpath(root, staging_dir)
                relative = "" if relative == "." else (relative + "/")
                for file in files:
                    map_file = relative + file
                    files.append(map_file)

            # Export guides
            guides = xgen.list_guides(desc)
            if guides:
                guide_file = "guides/%s/%s.abc" % (palette, desc)
                guide_path = "%s/%s" % (staging_dir, guide_file)
                io.export_xgen_LGC_guides(guides, guide_path)

                files.append(guide_file)

            # Export grooming
            groom = xgen.get_groom(desc)
            if groom and cmds.objExists(groom):
                groom_dir = "groom/%s/%s" % (palette, desc)
                groom_path = "%s/%s" % (staging_dir, groom_dir)
                xgen.export_grooming(desc, groom, groom_path)

                # Walk groom_path and add into files
                for root, _, files in os.walk(groom_path):
                    relative = os.path.relpath(root, staging_dir)
                    relative = "" if relative == "." else (relative + "/")
                    for file in files:
                        groom_file = relative + file
                        files.append(groom_file)

        # Extract palette
        for palette in instance.data["xgenPalettes"]:
            xgen_file = palette + ".xgen"
            xgen_path = "%s/%s" % (staging_dir, xgen_file)
            io.export_xgen_LGC_palette(palette, xgen_path)

            xgen_files.append(xgen_file)
            files.append(xgen_file)

            # Culled
            xgd_file = "deltas/%s/%s_culled.xgd" % (palette, palette)
            xgd_path = "%s/%s" % (staging_dir, xgd_file)
            if xgen.save_culled_as_delta(palette, xgd_path):
                self.log.info("Culled primitives saved.")

                files.append(xgd_file)

        instance.data["repr.XGenLegacy._stage"] = staging_dir
        instance.data["repr.XGenLegacy._files"] = files
        instance.data["repr.XGenLegacy.entryFileName"] = None  # no entry file
        instance.data["repr.XGenLegacy.descriptionsData"] = descriptions_data
        instance.data["repr.XGenLegacy.palettes"] = xgen_files
        instance.data["repr.XGenLegacy.step"] = instance.data["step"]
