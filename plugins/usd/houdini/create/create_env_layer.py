from avalon import houdini
from reveries import lib


class CreateLayoutLayerUSD(houdini.Creator):
    """Publish environment layer USD"""

    label = "Environment Layer (USD)"
    family = "reveries.env.layer"
    icon = "building"

    def __init__(self, *args, **kwargs):
        super(CreateLayoutLayerUSD, self).__init__(*args, **kwargs)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

    def process(self):
        instance = super(CreateLayoutLayerUSD, self).process()
        file_path = "$HIP/pyblish/%s/%s_prim.usda" % (self.name, self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False
        }

        instance.setParms(parms)
