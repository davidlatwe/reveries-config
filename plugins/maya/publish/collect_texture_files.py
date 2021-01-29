
import pyblish.api


class CollectTextureFiles(pyblish.api.InstancePlugin):
    """Collect texture data from each file nodes in instance

    Get file name pattern from file node and all files that exists in storage
    by the pattern string with color space setting.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Texture File Path"
    hosts = ["maya"]
    families = [
        "reveries.texture",
        "reveries.standin",
        "reveries.rsproxy",
    ]

    def process(self, instance):
        from maya import cmds
        from reveries.maya import lib

        file_nodes = instance.data.get("fileNodes",
                                       cmds.ls(instance, type="file"))
        file_count, file_data = lib.profiling_file_nodes(file_nodes)

        instance.data["fileData"] = file_data

        self.log.info("Collected %d texture files from %s file node."
                      "" % (file_count, len(file_data)))
