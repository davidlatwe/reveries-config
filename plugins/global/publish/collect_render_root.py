
import pyblish.api


class CollectRenderRoot(pyblish.api.InstancePlugin):
    """Inject render storage root path into instance"""

    order = pyblish.api.CollectorOrder
    label = "Root Path For Render"
    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):
        render_root = instance.data.get("reprRoot")
        if render_root:
            self.log.info("Pre-defined render output root: %s" % render_root)
            return

        project = instance.context.data["projectDoc"]
        project_render_root = project["data"].get("renderRoot")
        instance_render_root = instance.data.get("renderRoot", "").strip()

        render_root = instance_render_root or project_render_root
        if render_root:
            instance.data["reprRoot"] = render_root
            self.log.info("Render output root: %s" % render_root)
