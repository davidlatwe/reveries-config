
import os
import json
import pyblish.api
from reveries.plugins import PackageExtractor, skip_stage
from reveries.maya import io
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
        bound_map = dict()

        for desc in self.data["xgenDescriptions"]:
            # Save bounding
            bound_map[desc] = xgen.list_bound_geometry(desc)

            # Transfer maps
            maps = xgen.maps_to_transfer(desc)
            palette = xgen.get_palette_by_description(desc)
            data_path = xgen.current_data_path(palette, expand=True)

            for src in maps:
                tail = src[len(data_path):]
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

        # Extract bounding map
        link_file = self.file_name("json")
        link_path = os.path.join(package_dir, link_file)

        with open(link_path, "w") as fp:
            json.dump(bound_map, fp, ensure_ascii=False)

        self.add_data({
            "entryFileName": link_file,
            "palettes": xgen_files,
        })
