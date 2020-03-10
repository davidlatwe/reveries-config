
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateTextureNoFunnyPath(pyblish.api.InstancePlugin):
    """Textrue file path should use only ASCII characters

    Use only English or numbers in file path.

    """

    order = pyblish.api.ValidatorOrder
    label = "No Funny Path"
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
            raise Exception("Invalid file path found.")

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        for data in instance.data.get("fileData", []):
            node = data["node"]
            path = data["dir"] + "/" + data["fpattern"]
            if cls.is_funny(path):
                invalid.append(node)

        return invalid

    @classmethod
    def is_funny(cls, path):
        """Not all ASCII characters"""
        return not all(ord(char) < 128 for char in path)
