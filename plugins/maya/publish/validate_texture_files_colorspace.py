
import pyblish.api

from reveries.maya import plugins


class ValidateTextureFilesColorspace(pyblish.api.InstancePlugin):
    """Ensure each texture file assigned with same color space

    Same texture file referenced multiple times with different color spaces
    is not allowed.

    In most cases, one image file should have only one correct color space,
    so if multiple file node linked to the same file, those file nodes should
    have identical color space settings.

    """

    order = pyblish.api.ValidatorOrder
    label = "Same Texture Same Colorspace"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        colorspaces = dict()

        for data in instance.data.get("fileData", []):
            node = data["node"]
            fpattern = data["fpattern"]
            colorspace = data["colorSpace"]

            if fpattern not in colorspaces:
                colorspaces[fpattern] = dict()

            if colorspace not in colorspaces[fpattern]:
                colorspaces[fpattern][colorspace] = list()

            colorspaces[fpattern][colorspace].append(node)

        for fpattern, colorspace in colorspaces.items():
            if len(colorspace) > 1:
                cls.log.error("%s is referenced multiple times with "
                              "different color spaces" % fpattern)
                for nodes in colorspace.values():
                    invalid += nodes

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception("%s has same texture with different "
                            "colorspaces." % instance)
