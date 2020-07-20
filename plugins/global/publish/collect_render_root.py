
import pyblish.api


class CollectRenderRoot(pyblish.api.InstancePlugin):
    """Inject render storage root path into instance"""

    order = pyblish.api.CollectorOrder
    label = "Root Path For Render"
    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):
        project = instance.context.data["projectDoc"]
        render_root = project["data"].get("renderRoot")
        if render_root:
            instance.data["reprRoot"] = render_root
