
import pyblish.api


class OpenFilePathEditor(pyblish.api.Action):

    label = "File Path Editor"
    on = "failed"

    def process(self, context, plugin):
        from maya import mel
        mel.eval("FilePathEditor;")


class ValidateTextureFilesExists(pyblish.api.InstancePlugin):
    """Ensure file exists
    """

    order = pyblish.api.ValidatorOrder
    label = "Texture Files Exists"
    hosts = ["maya"]
    families = [
        "reveries.texture",
    ]
    actions = [
        pyblish.api.Category("Helper"),
        OpenFilePathEditor,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        cmds.filePathEditor(refresh=True)
        unresloved = (cmds.filePathEditor(query=True,
                                          listFiles="",
                                          withAttribute=True,
                                          byType="file",
                                          unresolved=True) or [])

        for map_attr in unresloved[1::2]:
            file_node = map_attr.split(".", 1)[0]
            if file_node in instance:
                invalid.append(file_node)

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
