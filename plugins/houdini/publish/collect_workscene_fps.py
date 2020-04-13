import pyblish.api


class CollectWorksceneFPS(pyblish.api.ContextPlugin):
    """Get the FPS of the work scene"""

    label = "Workscene FPS"
    order = pyblish.api.CollectorOrder
    hosts = ["houdini"]

    def process(self, context):
        import hou

        fps = hou.fps()
        self.log.info("Workscene FPS: %s" % fps)
        context.data.update({"fps": fps})
