
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
    def get_invalid(cls, instance):
        from maya import cmds
        from reveries.maya.lib import is_versioned_texture_path

        files = set(instance.data["fileNodes"])

        has_versioned = set()
        for node in files:
            file_path = cmds.getAttr(node + ".fileTextureName")
            if is_versioned_texture_path(file_path):
                has_versioned.add(node)

        not_versioned = files - has_versioned

        return list(not_versioned)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Texture node not versioned.")
