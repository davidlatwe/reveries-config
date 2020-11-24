from avalon import houdini
from reveries import lib


class CreateFxLayerUSD(houdini.Creator):
    """Publish FX layer USD"""

    label = "FX Layer (USD)"
    family = "reveries.fxlayer"
    icon = "building"

    hosts = ["houdini"]

    def __init__(self, *args, **kwargs):
        super(CreateFxLayerUSD, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        # self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        self.data["family"] = "reveries.fx.layer_prim"
        self.data["usdType"] = [
            "Sublayer",
            "Reference"
        ]

    def process(self):
        import hou

        instance = super(CreateFxLayerUSD, self).process()
        file_path = "$HIP/pyblish/{0}/{0}_prim.usda".format(self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False,
        }

        instance.setParms(parms)
        instance.setColor(hou.Color((0.063, 0.063, 0.292)))
