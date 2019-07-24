
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Not Versioned"


class ValidateVersionedTextures(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Has Versioned Textures"
    families = [
        "reveries.standin",
    ]

    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    @classmethod
    def is_versioned_path(cls, path):
        import re

        pattern = (
            ".*[/\\\]publish"  # publish root
            "[/\\\]texture.*"  # subset dir
            "[/\\\]v[0-9]{3}"  # version dir
            "[/\\\]TexturePack"  # representation dir
        )

        return bool(re.match(pattern, path))

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        files = set(instance.data["fileNodes"])

        has_versioned = set()
        for node in files:
            file_path = cmds.getAttr(node + ".fileTextureName")
            if cls.is_versioned_path(file_path):
                has_versioned.add(node)

        not_versioned = files - has_versioned

        return list(not_versioned)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Texture node not versioned.")
