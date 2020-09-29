import avalon

import pyblish.api


class ValidateLOPPath(pyblish.api.InstancePlugin):
    """Validate renderer setting exists in db."""

    order = pyblish.api.ValidatorOrder

    label = "Validate LOP Path"
    hosts = ["houdini"]
    families = [
        "reveries.layout",
        "reveries.layout.layer"
    ]

    def process(self, instance):
        node = instance[0]
        lop_path = node.parm("loppath").eval()
        if not lop_path:
            raise ValueError("{} LOP Path does not exist.".format(node))

        print('instance: ', instance[:])
