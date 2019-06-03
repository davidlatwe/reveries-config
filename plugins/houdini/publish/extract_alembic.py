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
        "AlembicSeq",
    ]

    def extract(self):

        if "frameOutputs" in self.data:
            self.extract_AlembicSeq()
        else:
            self.extract_Alembic()

    def extract_Alembic(self):
        ropnode = self.member[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        staging_dir))
        self.render(ropnode)

        self.add_data({
            "entryFileName": file_name,
        })

    def extract_AlembicSeq(self):
        ropnode = self.member[0]

        # Get the first frame filename from pre-collected data
        output = self.data["frameOutputs"][0]
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        staging_dir))
        self.render(ropnode)

        self.add_data({
            "entryFileName": file_name,
            "startFrame": self.data["startFrame"],
            "endFrame": self.data["endFrame"],
            "step": self.data["step"],
        })

    def render(self, ropnode):
        import hou

        try:
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))
