
import pyblish.api


class CollectAtomsCrowdFrameRange(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect AtomsCrowd Frame Range"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]

    def process(self, instance):
        if instance.data.get("useCustomRange"):
            self.log.info("Using custom cache frame range.")
        else:
            self.log.warning("Using scene wide cache frame range.")
            instance.data["startFrame"] = instance.context.data["startFrame"]
            instance.data["endFrame"] = instance.context.data["endFrame"]

        self.log.info("Caching from frame %d to %d."
                      % (instance.data["startFrame"],
                         instance.data["endFrame"]))
