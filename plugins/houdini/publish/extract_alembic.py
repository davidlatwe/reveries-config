import os
import pyblish.api


class ExtractAlembic(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder
    label = "Extract Alembic"
    hosts = ["houdini"]
    families = [
        "reveries.pointcache",
        "reveries.camera",
    ]

    def process(self, instance):
        if len(instance.data.get("frameOutputs", [])) <= 1:
            self.export_abc(instance)
        else:
            self.export_abc_seq(instance)

    def export_abc(self, instance):
        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("filename")
        # Set custom staging dir
        staging_dir, filename = os.path.split(output)
        repr_root = instance.data["reprRoot"]

        instance.data["repr.Alembic._stage"] = staging_dir
        instance.data["repr.Alembic._hardlinks"] = [filename]
        instance.data["repr.Alembic.entryFileName"] = filename

        if instance.data["family"] == "reveries.pointcache":
            instance.data["repr.Alembic.reprRoot"] = repr_root

        instance.data["repr.Alembic._delayRun"] = {
            "func": self.render,
            "args": [ropnode],
        }

    def export_abc_seq(self, instance):
        ropnode = instance[0]

        # Get the first frame filename from pre-collected data
        output = instance.data["frameOutputs"][0]
        # Set custom staging dir
        staging_dir, filename = os.path.split(output)
        repr_root = instance.data["reprRoot"]

        start = instance.data["startFrame"]
        end = instance.data["endFrame"]
        step = instance.data["step"]

        files = list()
        for path in instance.data["frameOutputs"]:
            files.append(os.path.basename(path))

        instance.data["repr.AlembicSeq._stage"] = staging_dir
        instance.data["repr.AlembicSeq._hardlinks"] = files
        instance.data["repr.AlembicSeq.entryFileName"] = filename
        instance.data["repr.AlembicSeq.startFrame"] = start
        instance.data["repr.AlembicSeq.endFrame"] = end
        instance.data["repr.AlembicSeq.step"] = step

        if instance.data["family"] == "reveries.pointcache":
            instance.data["repr.AlembicSeq.reprRoot"] = repr_root

        instance.data["repr.AlembicSeq._delayRun"] = {
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
