import os
import traceback

import pyblish.api


class ExtractFxLayerUSD(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.2
    label = "Extract Fx Layer USD Export"
    # hosts = ["houdini"]
    families = [
        "reveries.fx.layer_prim",
    ]

    def process(self, instance):
        from reveries.common.build_delay_run import DelayRunBuilder

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

        instance.data["_preflighted"] = True

        # Create delay running
        delay_builder = DelayRunBuilder(instance)

        instance.data["deadline_plugin"] = "HoudiniBatch"

        instance.data["repr.USD._delayRun"] = {
            "func": self.export_usd,
            "args": [
                delay_builder.instance_data, delay_builder.context_data,
                ropnode
            ],
            # "order": 10
        }

    def export_usd(self, instance_data, context_data, node_name):
        import hou

        # Export usd
        try:
            node = hou.node("/out/{}".format(node_name))
            if node:
                node.render()
                self._publish_instance(instance_data, context_data=context_data)
            else:
                msg = "Export fx layer failed, node \"{}\" not exists.".\
                    format(node_name)
                raise RuntimeError(msg)

        except hou.Error as exc:
            print("FX layer export failed: {}".format(traceback.print_exc()))
            raise RuntimeError("Render failed: {0}".format(exc))

    def _publish_instance(self, instance_data, context_data=None):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
