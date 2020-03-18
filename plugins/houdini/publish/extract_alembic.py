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

    def extract(self, instance):
        if len(instance.data.get("frameOutputs", [])) <= 1:
            instance.data["extractType"] = "Alembic"
        else:
            instance.data["extractType"] = "AlembicSeq"

        super(ExtractAlembic, self).extract(instance)

    def extract_Alembic(self, instance):
        packager = instance.data["packager"]
        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        pkg_dir = packager.create_package(with_representation=False)

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode, pkg_dir)

        packager.add_data({
            "entryFileName": file_name,
        })
        self.inject_cache_root(instance, packager)

    def extract_AlembicSeq(self, instance):
        packager = instance.data["packager"]
        ropnode = instance[0]

        # Get the first frame filename from pre-collected data
        output = instance.data["frameOutputs"][0]
        # Set custom staging dir
        staging_dir = os.path.dirname(output)
        instance.data["stagingDir"] = staging_dir
        pkg_dir = packager.create_package(with_representation=False)

        file_name = os.path.basename(output)
        self.log.info("Writing alembic '%s' to '%s'" % (file_name,
                                                        pkg_dir))
        self.render(ropnode, pkg_dir)

        packager.add_data({
            "entryFileName": file_name,
            "startFrame": instance.data["startFrame"],
            "endFrame": instance.data["endFrame"],
            "step": instance.data["step"],
        })
        self.inject_cache_root(instance, packager)

    def inject_cache_root(self, instance, packager):
        if instance.data["family"] == "reveries.pointcache":
            packager.add_data({
                "reprRoot": instance.data["reprRoot"],
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
