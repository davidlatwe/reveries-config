import os

import pyblish.api
from reveries.plugins import PackageExtractor


class ExtractAlembic(PackageExtractor):

    order = pyblish.api.ExtractorOrder
    label = "Extract Alembic"
    hosts = ["houdini"]
    families = [
        "reveries.pointcache",
        "reveries.camera",
    ]

    representations = [
        "Alembic",
    ]

    def extract_Alembic(self):

        import hou

        ropnode = self.member[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir

        file_name = os.path.basename(output)

        # We run the render
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        staging_dir))
        try:
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

        if "files" not in self.data:
            self.data["files"] = []

        self.data["files"].append(file_name)
