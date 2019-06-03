import os

import pyblish.api
from reveries.plugins import PackageExtractor


class ExtractVDBCache(PackageExtractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
    ]

    representations = [
        "vdb",
    ]

    def extract_vdb(self):

        import hou

        ropnode = self.member[0]

        if "frameOutputs" in self.data:
            output = self.data["frameOutputs"][0]
        else:
            output = ropnode.evalParm("sopoutput")

        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing VDB '%s' to '%s'" % (file_name, staging_dir))

        try:
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

        self.add_data({
            "entryFileName": file_name,
        })

        if self.data.get("startFrame"):
            self.add_data({
                "startFrame": self.data["startFrame"],
                "endFrame": self.data["endFrame"],
                "step": self.data["step"],
            })
