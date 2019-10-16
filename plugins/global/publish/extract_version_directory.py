
import pyblish.api


class ExtractVersionDirectory(pyblish.api.InstancePlugin):
    """Create publish version directory
    """

    label = "Create Version Directory"
    order = pyblish.api.ExtractorOrder - 0.4

    def process(self, instance):
        """Get a version dir which binded to current workfile
        """
        versioner = instance.data["versioner"]

        instance.data["versionDir"] = versioner.version_dir()
        instance.data["versionNext"] = versioner.version_num()
