
import pyblish.api


class ExtractVersionDirectory(pyblish.api.InstancePlugin):
    """計算下一個版本號並創建資料夾
    """

    label = "創建版號"
    order = pyblish.api.ExtractorOrder - 0.4

    def process(self, instance):
        """Get a version dir which binded to current workfile
        """
        packager = instance.data["packager"]

        instance.data["versionDir"] = packager.version_dir()
        instance.data["versionNext"] = packager.version_num()
