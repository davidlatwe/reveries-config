from avalon import houdini
from reveries import lib


class CreateSetDressLayerUSD(houdini.Creator):
    """Publish SetDress layer USD"""

    label = "SetDress Layer (USD)"
    family = "reveries.setdress.layer"
    icon = "building"

    hosts = ["houdini"]

    def __init__(self, *args, **kwargs):
        super(CreateSetDressLayerUSD, self).__init__(*args, **kwargs)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        self.data["family"] = "reveries.setdress.layer_prim"

    def process(self):
        instance = super(CreateSetDressLayerUSD, self).process()
        file_path = "$HIP/pyblish/%s/%s_prim.usda" % (self.name, self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False
        }

        instance.setParms(parms)
