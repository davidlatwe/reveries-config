import os

import pyblish.api


class ExtractVDBCache(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract VDB Cache"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
    ]

    def process(self, instance):
        ropnode = instance[0]

        files = list()

        if "frameOutputs" in instance.data:
            output = instance.data["frameOutputs"][0]

            start = instance.data["startFrame"]
            end = instance.data["endFrame"]
            step = instance.data["step"]

            instance.data["repr.VDB.startFrame"] = start
            instance.data["repr.VDB.endFrame"] = end
            instance.data["repr.VDB.step"] = step

            for path in instance.data["frameOutputs"]:
                files.append(os.path.basename(path))

        else:
            output = ropnode.evalParm("sopoutput")

        staging_dir, filename = os.path.split(output)
        repr_root = instance.data["reprRoot"]

        instance.data["repr.VDB._stage"] = staging_dir
        instance.data["repr.VDB._hardlinks"] = files or [filename]
        instance.data["repr.VDB.entryFileName"] = filename
        instance.data["repr.VDB.reprRoot"] = repr_root

        instance.data["repr.VDB._delayRun"] = {
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
