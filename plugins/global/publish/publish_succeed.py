
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

            packager = instance.data["packager"]
            packager.unlock()
            # (TODO) If publish process stopped by user, version dir will
            #        remain locked since this plugin may not be executed.
            #        To solve this, may require pyblish/pyblish-base#352
            #        be implemented.
