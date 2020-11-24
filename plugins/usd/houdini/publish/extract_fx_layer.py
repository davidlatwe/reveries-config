import os
import traceback

import pyblish.api


class ExtractFxLayerUSD(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.2
    label = "Extract Fx Layer USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.fx.layer_prim",
    ]

    def process(self, instance):
        import hou

        ropnode = instance[0]

        # Get the filename from the filename parameter
        output = ropnode.evalParm("lopoutput")
        usd_type = ropnode.evalParm("usdType")

        # Set custom staging dir
        staging_dir, filename = os.path.split(output)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename]
        instance.data["repr.USD.entryFileName"] = filename
        instance.data["subsetGroup"] = "Fx"
        instance.data["usd_type"] = usd_type

        try:
            ropnode.render()
            self._publish_instance(instance)

        except hou.Error as exc:
            # The hou.Error is not inherited from a Python Exception class,
            # so we explicitly capture the houdini error, otherwise pyblish
            # will remain hanging.
            traceback.print_exc()
            raise RuntimeError("Render failed: {0}".format(exc))

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
