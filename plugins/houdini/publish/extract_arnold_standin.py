import os

import pyblish.api
from reveries.plugins import PackageExtractor


class ExtractArnoldStandIn(PackageExtractor):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Arnold Stand-In"
    hosts = ["houdini"]
    families = [
        "reveries.standin",
    ]

    representations = [
        "Ass",
    ]

    def extract_Ass(self):

        import hou

        ropnode = self.member[0]

        if "frameOutputs" in self.data:
            output = self.data["frameOutputs"][0]
        else:
            output = ropnode.evalParm("ar_ass_file")

        staging_dir = os.path.dirname(output)
        self.data["stagingDir"] = staging_dir
        repr_dir = self.create_package()

        file_name = os.path.basename(output)
        self.log.info("Writing Ass '%s' to '%s'" % (file_name, repr_dir))

        raw_path = ropnode.parm("ar_ass_file").rawValue()
        raw_file = os.path.basename(raw_path)
        try:
            ropnode.render(output_file=repr_dir + "/" + raw_file)
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
