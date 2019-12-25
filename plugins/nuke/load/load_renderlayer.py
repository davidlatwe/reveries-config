
import os
import nuke
import avalon.api
from reveries.plugins import PackageLoader


class RenderLayerLoader(PackageLoader, avalon.api.Loader):

    label = "Load RenderLayer"
    icon = "camera-retro"
    color = "#28EDC9"

    hosts = ["nuke"]

    families = ["reveries.renderlayer"]

    representations = [
        "renderLayer",
    ]

    def load(self, context, name, namespace, options):

        representation = context["representation"]

        for name, data in representation["data"]["sequence"].items():
            path = os.path.join(
                data["dirPath"],
                data["fname"]
            ).replace("\\", "/")

            read = nuke.Node("Read")
            read["file"].setValue(path)
            # Frame range
            # resolution
