import os

import pyblish.api
from reveries.houdini.plugins import HoudiniRenderExtractor


class ExtractAlembic(HoudiniRenderExtractor):

    order = pyblish.api.ExtractorOrder + 0.1
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
        from reveries.houdini import lib

        ropnode = self.member[0]

        # Get the filename from the filename parameter
        output_parm = lib.get_output_parameter(ropnode)
        output = output_parm.eval()
        staging_dir = os.path.dirname(output)
        file_name = os.path.basename(output)

        # Set custom staging dir
        self.data["stagingDir"] = staging_dir

        packager.add_data({
            "entryFileName": file_name,
        })
        self.inject_cache_root(packager)
        pkg_dir = packager.create_package(with_representation=False)

        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode)

    def extract_AlembicSeq(self, packager):
        ropnode = self.member[0]

        # Get the first frame filename from pre-collected data
        output = self.data["frameOutputs"][0]
        staging_dir = os.path.dirname(output)
        file_name = os.path.basename(output)

        # Set custom staging dir
        self.data["stagingDir"] = staging_dir

        packager.add_data({
            "entryFileName": file_name,
            "startFrame": self.data["startFrame"],
            "endFrame": self.data["endFrame"],
            "step": self.data["step"],
        })
        self.inject_cache_root(packager)
        pkg_dir = packager.create_package(with_representation=False)

        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode)

    def inject_cache_root(self, packager):
        if self.data["family"] == "reveries.pointcache":
            packager.add_data({
                "reprRoot": self.data["reprRoot"],
            })
