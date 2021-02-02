import os
import pyblish.api


class ExtractRedshiftProxy(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Extract Redshift Proxy"
    hosts = ["houdini"]
    families = [
        "reveries.rsproxy",
    ]

    def process(self, instance):
        from reveries.houdini import lib

        ropnode = instance[0]

        files = list()

        if "frameOutputs" in instance.data:
            use_sequence = True
            output = instance.data["frameOutputs"][0]

            for path in instance.data["frameOutputs"]:
                files.append(os.path.basename(path))

        else:
            use_sequence = False
            output_parm = lib.get_output_parameter(ropnode)
            output = output_parm.eval()

        staging_dir, filename = os.path.split(output)
        repr_root = instance.data["reprRoot"]

        instance.data["repr.RsProxy._stage"] = staging_dir
        instance.data["repr.RsProxy._hardlinks"] = files or [filename]
        instance.data["repr.RsProxy.entryFileName"] = filename
        instance.data["repr.RsProxy.useSequence"] = use_sequence
        instance.data["repr.RsProxy.reprRoot"] = repr_root

        instance.data["repr.RsProxy._delayRun"] = {
            "func": self.render,
            "args": [ropnode.path()],
        }

    def render(self, ropnode_path):
        import hou

        try:
            ropnode = hou.node(ropnode_path)
            ropnode.render()
        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))
