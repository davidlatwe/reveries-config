
import pyblish.api


class CollectStandInRoot(pyblish.api.InstancePlugin):
    """Inject arnold standin storage root path into instance"""

    order = pyblish.api.CollectorOrder
    label = "Root Path For Render Proxy"
    families = [
        "reveries.standin",
        "reveries.rsproxy",
    ]

    def process(self, instance):
        project = instance.context.data["projectDoc"]
        standin_root = project["data"].get("standinRoot")
        if standin_root:
            instance.data["reprRoot"] = standin_root
