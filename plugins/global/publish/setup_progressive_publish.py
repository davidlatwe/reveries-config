
import pyblish.api


class SetupProgressivePublish(pyblish.api.InstancePlugin):
    """
    """
    order = pyblish.api.CollectorOrder + 0.4
    label = "Setup Progressive"
    families = [
        "reveries.standin",
        "reveries.rsproxy",
        "reveries.renderlayer",
    ]

    def process(self, instance):
        if instance.data.get("staticCache"):
            # Single frame standin
            return

        instance.data["setupProgressivePublish"] = True
