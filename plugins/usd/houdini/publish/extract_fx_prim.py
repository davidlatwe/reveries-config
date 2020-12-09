import os

import pyblish.api


class ExtractFxPrimUSD(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.21
    label = "Extract Fx USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.fx.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.usd.pipeline import fx_prim_export

        # Set comment
        context = instance.context
        context.data["comment"] = "Auto generate"
        # subset_name = instance.data["subset"]

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        filename = 'fx_prim.usda'

        final_output = os.path.join(staging_dir, filename)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename]
        instance.data["repr.USD.entryFileName"] = filename

        # Export setdressPrim
        shot_name = instance.data['asset']
        fx_prim_export.FxPrimExport.export(final_output, shot_name)

        # ==== Publish instance ==== #
        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
