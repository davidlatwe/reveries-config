import os
import pyblish.api


class ExtractArnoldStandIn(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Arnold Stand-In"
    hosts = ["houdini"]
    families = [
        "reveries.standin",
    ]

    def process(self, instance):
        from reveries.houdini import lib

        ropnode = instance[0]

        files = list()

        if "frameOutputs" in instance.data:
            output = instance.data["frameOutputs"][0]

            for path in instance.data["frameOutputs"]:
                files.append(os.path.basename(path))

        else:
            output_parm = lib.get_output_parameter(ropnode)
            output = output_parm.eval()

        staging_dir, filename = os.path.split(output)
        repr_root = instance.data["reprRoot"]

        instance.data["repr.Ass._stage"] = staging_dir
        instance.data["repr.Ass._hardlinks"] = files or [filename]
        instance.data["repr.Ass.entryFileName"] = filename
        instance.data["repr.Ass.reprRoot"] = repr_root

        instance.data["repr.Ass._delayRun"] = {
            "func": self.render,
            "args": [ropnode],
        }

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
