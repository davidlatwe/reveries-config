
import os
import json
import pyblish.api
from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya import io, utils
from reveries.maya.xgen import legacy as xgen


class ExtractXGenLegacy(PackageExtractor):
    """
    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract XGen Legacy"
    families = [
        "reveries.xgen.legacy",
    ]

    representations = [
        "XGenLegacy",
    ]

    @skip_stage
    def extract_XGenLegacy(self):

        package_dir = self.create_package()

        xgen_files = list()
        description_ids = dict()
        bound_map = dict()

        for desc in self.data["xgenDescriptions"]:
            # Save bounding

            desc_id = utils.get_id(desc)
            description_ids[desc] = desc_id
            bound_map[desc_id] = [utils.get_id(geo) for geo in
                                  xgen.list_bound_geometry(desc)]

            # Transfer maps
            maps = xgen.maps_to_transfer(desc)
            palette = xgen.get_palette_by_description(desc)
            data_paths = xgen.current_data_paths(palette, expand=True)

            for src in maps:
                for root in data_paths:
                    if src.startswith(root):
                        # At least one root will be matched, since all
                        # map path has been validated that must exists
                        # under ${DESC} dir.
                        tail = src[len(root):]
                        break
                else:
                    self.log.critical("Searched data path:")
                    for root in data_paths:
                        self.log.critical(root)
                    raise Exception("Could not find root path for %s , "
                                    "this is a bug." % src)

                dst = os.path.join(package_dir, "maps", palette, tail)
                self.add_file(src, dst)

            # Export guides
            guides = xgen.list_guides(desc)
            if guides:
                guide_file = os.path.join(package_dir,
                                          "guides",
                                          palette,
                                          desc + ".abc")
                io.export_xgen_LGC_guides(guides, guide_file)

        # Extract palette
        for palette in self.data["xgenPalettes"]:
            xgen_file = palette + ".xgen"
            xgen_path = os.path.join(package_dir, xgen_file)
            io.export_xgen_LGC_palette(palette, xgen_path)
            xgen_files.append(xgen_file)

            # Culled
            xgd_file = palette + "_culled.xgd"
            xgd_path = os.path.join(package_dir, "deltas", palette, xgd_file)
            if xgen.save_culled_as_delta(palette, xgd_path):
                self.log.info("Culled primitives saved.")

        # Extract bounding map
        link_file = self.file_name("json")
        link_path = os.path.join(package_dir, link_file)

        with open(link_path, "w") as fp:
            json.dump(bound_map, fp, ensure_ascii=False)

        self.add_data({
            "entryFileName": None,  # Yes, no entry file for XGen Legacy.
            "linkFname": link_file,
            "descriptionIds": description_ids,
            "palettes": xgen_files,
        })
