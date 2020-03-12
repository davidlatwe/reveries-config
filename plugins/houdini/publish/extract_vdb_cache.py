import os

import pyblish.api
from reveries.houdini.plugins import HoudiniRenderExtractor


class ExtractVDBCache(HoudiniRenderExtractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
    ]

    representations = [
        "VDB",
    ]

    def extract_VDB(self, packager):
        from reveries.houdini import lib

        ropnode = self.member[0]

        if "frameOutputs" in self.data:
            output = self.data["frameOutputs"][0]
        else:
            output_parm = lib.get_output_parameter(ropnode)
            output = output_parm.eval()

        staging_dir = os.path.dirname(output)
        file_name = os.path.basename(output)

        # Set custom staging dir
        self.data["stagingDir"] = staging_dir

        packager.add_data({
            "entryFileName": file_name,
            "reprRoot": self.data["reprRoot"],
        })
        if self.data.get("startFrame"):
            packager.add_data({
                "startFrame": self.data["startFrame"],
                "endFrame": self.data["endFrame"],
                "step": self.data["step"],
            })

        pkg_dir = packager.create_package(with_representation=False)
        self.log.info("Writing VDB '%s' to '%s'" % (file_name, pkg_dir))
        self.render(ropnode)
