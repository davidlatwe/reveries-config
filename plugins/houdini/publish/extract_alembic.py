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
            extract_type = ["Alembic"]
        else:
            extract_type = ["AlembicSeq"]

        self._active_representations = extract_type
        super(ExtractAlembic, self).extract()

    def extract_Alembic(self):
        ropnode = self.member[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        repr_dir = self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        repr_dir))
        self.render(ropnode, repr_dir)

        self.add_data({
            "entryFileName": file_name,
        })
        self.inject_cache_root()

    def extract_AlembicSeq(self):
        ropnode = self.member[0]

        # Get the first frame filename from pre-collected data
        output = self.data["frameOutputs"][0]
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        repr_dir = self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        repr_dir))
        self.render(ropnode, repr_dir)

        self.add_data({
            "entryFileName": file_name,
            "startFrame": self.data["startFrame"],
            "endFrame": self.data["endFrame"],
            "step": self.data["step"],
        })
        self.inject_cache_root()

    def inject_cache_root(self):
        if self.data["family"] == "reveries.pointcache":
            self.add_data({
                "reprRoot": self.data["reprRoot"],
            })

    def render(self, ropnode, output_dir):
        import hou

        raw_path = ropnode.parm("filename").rawValue()
        raw_file = os.path.basename(raw_path)
        try:
            ropnode.render(output_file=output_dir + "/" + raw_file)
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))
