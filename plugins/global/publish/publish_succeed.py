
import pyblish.api


class PublishSucceed(pyblish.api.ContextPlugin):

    label = "Publish Succeed"
    order = pyblish.api.IntegratorOrder + 0.499999

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            version_manager = instance.data["versionManager"]
            version_manager.set_succeeded()
