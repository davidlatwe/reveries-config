from avalon import houdini
from reveries import lib


class CreateLightingUSD(houdini.Creator):
    """Publish Lighting USD"""

    label = "Lighting (USD)"
    family = "reveries.lgt"
    icon = "lightbulb-o"

    hosts = ["houdini"]

    def __init__(self, *args, **kwargs):
        super(CreateLightingUSD, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        # self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        self.data["family"] = "reveries.lgt.usd"

    def process(self):
        import hou

        instance = super(CreateLightingUSD, self).process()
        file_path = "$HIP/pyblish/{0}/lgt_prim.usda".format(self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False,
        }

        instance.setParms(parms)
        instance.setColor(hou.Color((0.063, 0.257, 0.083)))
