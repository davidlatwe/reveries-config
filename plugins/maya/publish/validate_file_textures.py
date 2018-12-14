
import os
import pyblish.api

from maya import cmds


class ValidateFileTextures(pyblish.api.InstancePlugin):
    """Ensure file exists
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Validate File Textures"
    families = [
        "reveries.look",
    ]

    @classmethod
    def get_invalid(cls, instance):

        file_nodes = cmds.ls(instance, type="file")

        if not file_nodes:
            return

        invalid = dict()

        for node in file_nodes:
            file_path = cmds.getAttr(node + ".fileTextureName",
                                     expandEnvironmentVariables=True)

            if not os.path.isfile(file_path):
                invalid[node] = file_path

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "'%s' Missing file textures on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + node + "'" for node in invalid))
            )
            raise Exception("%s has missing texture file." % instance)
