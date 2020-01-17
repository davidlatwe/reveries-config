
import pyblish.api


class PublishSucceed(pyblish.api.ContextPlugin):

    label = "Publish Succeed"
    order = pyblish.api.IntegratorOrder + 0.499999

    def process(self, context):
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            versioner = instance.data["versioner"]
            versioner.set_succeeded()
