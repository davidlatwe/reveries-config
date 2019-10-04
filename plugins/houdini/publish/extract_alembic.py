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
        if len(self.data.get("frameOutputs", [])) <= 1:
            self.data["extractType"] = "Alembic"
        else:
            self.data["extractType"] = "AlembicSeq"

        super(ExtractAlembic, self).extract()

    def extract_Alembic(self, packager):
        ropnode = self.member[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        pkg_dir = packager.create_package(with_representation=False)

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode, pkg_dir)

        packager.add_data({
            "entryFileName": file_name,
        })
        self.inject_cache_root(packager)

    def extract_AlembicSeq(self, packager):
        ropnode = self.member[0]

        # Get the first frame filename from pre-collected data
        output = self.data["frameOutputs"][0]
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        pkg_dir = packager.create_package(with_representation=False)

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode, pkg_dir)

        packager.add_data({
            "entryFileName": file_name,
            "startFrame": self.data["startFrame"],
            "endFrame": self.data["endFrame"],
            "step": self.data["step"],
        })
        self.inject_cache_root(packager)

    def inject_cache_root(self, packager):
        if self.data["family"] == "reveries.pointcache":
            packager.add_data({
                "reprRoot": self.data["reprRoot"],
            })

    def render(self, ropnode, output_dir):
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
