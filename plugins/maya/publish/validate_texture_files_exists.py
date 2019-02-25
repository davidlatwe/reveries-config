
import os
import pyblish.api


class ValidateTextureFilesExists(pyblish.api.InstancePlugin):
    """Ensure file exists
    """

    order = pyblish.api.ValidatorOrder
    label = "Texture Files Exists"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds
        from maya.app.general.fileTexturePathResolver import (
            getFilePatternString,
            findAllFilesForPattern,
        )

        invalid = list()

        for file_node in instance:
            attr_name = file_node + ".fileTextureName"
            tiling_mode = cmds.getAttr(file_node + ".uvTilingMode")
            is_sequence = cmds.getAttr(file_node + ".useFrameExtension")
            img_path = cmds.getAttr(attr_name,
                                    expandEnvironmentVariables=True)

            pattern = getFilePatternString(img_path, is_sequence, tiling_mode)

            for file in findAllFilesForPattern(pattern, None):
                if not os.path.isfile(file):
                    invalid.append(file_node)
                    break

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Missing file textures on:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + file_node + "'" for file_node in invalid))
            )

            raise Exception("%s has missing texture." % instance)
