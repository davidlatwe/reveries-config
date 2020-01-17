
import pyblish.api


class SubmitLocalWrite(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder - 0.1
    hosts = ["nuke"]
    label = "Local Write"

    families = [
        "reveries.write",
    ]

    targets = ["localhost"]

    def process(self, instance):
        import nuke

        context = instance.context
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        write = instance[0]
        nuke.render(write,
                    start=instance.data["startFrame"],
                    end=instance.data["endFrame"])
