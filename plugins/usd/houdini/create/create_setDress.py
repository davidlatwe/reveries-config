from avalon import houdini
from reveries import lib


class CreateSetDressUSD(houdini.Creator):
    """Publish Setdress USD"""

    label = "SetDress (USD)"
    family = "reveries.setdress"
    icon = "building"

    hosts = ["houdini"]

    def __init__(self, *args, **kwargs):
        super(CreateSetDressUSD, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        # self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["overSessionAsset"] = False

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

        self.data["family"] = "reveries.setdress.layer_prim"

    def process(self):
        import hou

        instance = super(CreateSetDressUSD, self).process()
        file_path = "$HIP/pyblish/{0}/{0}_prim.usd".format(self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False,
            # "savestyle": "flattenalllayers"
        }

        instance.setParms(parms)
        instance.setColor(hou.Color((0.92, 0.67, 0.05)))
