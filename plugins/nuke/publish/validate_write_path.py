
import pyblish.api
import avalon.api


class ValidateWritePath(pyblish.api.InstancePlugin):
    """Validate write node's output path

    Write node's output path should be in project root.

    """

    label = "Validate Write Path"
    order = pyblish.api.ValidatorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write"
    ]

    def process(self, instance):
        root = instance.data.get("reprRoot", avalon.api.registered_root())
        outpath = instance.data["outputPath"]

        if not outpath.startswith(root):
            raise Exception("Please write output under %s" % root)
