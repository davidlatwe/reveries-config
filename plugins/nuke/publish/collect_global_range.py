
import pyblish.api


class CollectGlobalRange(pyblish.api.ContextPlugin):

    label = "Global Range"
    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["nuke"]

    def process(self, context):
        import nuke

        root = nuke.Root()
        first_frame = root.firstFrame()
        last_frame = root.lastFrame()
        fps = root.fps()

        context.data["startFrame"] = first_frame
        context.data["endFrame"] = last_frame
        context.data["fps"] = fps

        context.data["label"] += " [%d-%d]" % (first_frame, last_frame)
        context.data["label"] += " %d FPS" % fps

        self.log.info("Global range: %d-%d" % (first_frame, last_frame))
        self.log.info("Global FPS: %d" % fps)
