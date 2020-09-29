import os
import pyblish.api


class ExtractLayoutLayer(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.2
    label = "Extract Layout Layer"
    hosts = ["houdini"]
    families = [
        "reveries.layout.layer",
    ]

    def process(self, instance):
        import hou

        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("lopoutput")
        # Set custom staging dir
        staging_dir, filename = os.path.split(output)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename]
        instance.data["repr.USD.entryFileName"] = filename

        try:
            ropnode.render()
            self._publish_instance(instance)

        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            import traceback
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["published"] = True
