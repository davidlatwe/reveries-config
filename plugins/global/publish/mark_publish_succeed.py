
import pyblish.api


class MarkPublishSucceed(pyblish.api.ContextPlugin):

    label = "Succeed"
    order = pyblish.api.IntegratorOrder + 0.49999

    def process(self, context):
        if not all(result["success"] for result in context.data["results"]):
            self.log.error("Publish failed.")
            return

        context.data["publishSucceed"] = True
