
import os
import pyblish.api

from reveries.maya import plugins


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
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Helper"),
        OpenFilePathEditor,
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = dict()

        for data in instance.data.get("fileData", []):
            node = data["node"]
            for file in data["fnames"]:
                file_path = os.path.join(data["dir"], file)

                if not os.path.isfile(file_path):
                    if node not in invalid:
                        invalid[node] = [file_path]
                    else:
                        invalid[node].append(file_path)

            if node in invalid:
                count = len(invalid[node])
                cls.log.error("File node '%s' has %d missing map."
                              % (node, count))

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
