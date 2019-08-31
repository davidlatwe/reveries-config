
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateTextureNoDirectTX(pyblish.api.InstancePlugin):
    """Directly use TX map in file node is not allowed

    (NOTE): If the original image is missing.. change the file extension
            from `.tx` to `.tif` then edit or save as.

    """

    order = pyblish.api.ValidatorOrder
    label = "No Direct TX Used"
    hosts = ["maya"]
    families = [
        "reveries.texture",
        "reveries.standin",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Do NOT use TX map directly.")

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        for data in instance.data.get("fileData", []):
            node = data["node"]
            fpattern = data["fpattern"]
            if fpattern.endswith(".tx"):
                invalid.append(node)

        return invalid
