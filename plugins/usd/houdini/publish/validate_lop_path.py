import pyblish.api


class ValidateLOPPath(pyblish.api.InstancePlugin):
    """Validate already setting LOP Path."""

    order = pyblish.api.ValidatorOrder + 0.2

    label = "Validate LOP Path"
    hosts = ["houdini"]
    families = [
        "reveries.setdress.layer_prim"
    ]

    def process(self, instance):
        node = instance[0]
        lop_path = node.parm("loppath").eval()
        if not lop_path:
            raise ValueError("{} LOP Path does not exist.".format(node))
