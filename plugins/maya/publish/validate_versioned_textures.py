
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Not Versioned"


class ValidateVersionedTextures(pyblish.api.InstancePlugin):
    """All surface node in scene should be part of versioned subset

    Should be containerized or instance that is going to be published

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

        files = set(instance.data["fileNodes"])
        root = instance.data["relativeRoot"]

        has_versioned = set()
        for node in files:
            file_path = cmds.getAttr(node + ".fileTextureName")
            if all(key in file_path for key in root):
                # As long as the texture file path starts with project
                # env vars, consider it's been published.
                has_versioned.add(node)

        not_versioned = files - has_versioned

        return list(not_versioned)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            for i in invalid:
                self.log.error(i)
            raise Exception("Texture node not versioned.")
