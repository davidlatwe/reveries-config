from avalon import houdini
from reveries import lib


class CreateLayoutUSD(houdini.Creator):
    """Publish environment layer USD"""

    label = "Environment (USD)"
    family = "reveries.env"
    icon = "building"

    def __init__(self, *args, **kwargs):
        super(CreateLayoutUSD, self).__init__(*args, **kwargs)

        # Remove the `active`, we are checking the `bypass` flag of the nodes
        # self.data.pop("active", None)

        # Set node type to create for output
        self.data.update({"node_type": "usd"})

        self.data["deadlinePriority"] = 80
        self.data["deadlinePool"] = lib.get_deadline_pools()

    def process(self):
        instance = super(CreateLayoutUSD, self).process()
        file_path = "$HIP/pyblish/{}/env_prim.usda".format(self.name)

        parms = {
            "lopoutput": file_path,
            "defaultprim": "ROOT",
            "enableoutputprocessor_simplerelativepaths": False,
            "savestyle": "flattenalllayers"
        }

        instance.setParms(parms)
