
import pyblish.api


class CollectDelegatedInstance(pyblish.api.ContextPlugin):
    """Collect delegated instances form Context

    This plugin will set `instance.data["publish"] = False` if that instance
    is not delegated.

    This plugin should run after normal instance collector.

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Delegated Instance"

    def process(self, context):
        if not context.data.get("contractor_accepted"):
            return

        assignment = context.data["contractor_assignment"]

        collected_count = 0
        for instance in context:
            name = instance.data["name"]
            if name in assignment:
                # version lock
                instance.data["version_next"] = assignment[name]
                self.log.info("{} collected.".format(name))
                collected_count += 1
            else:
                # Remove not assigned subset instance
                instance.data["publish"] = False
                self.log.info("{} skipped.".format(name))

        self.log.info("Collected {} instances.".format(collected_count))

        if collected_count == 0:
            raise ValueError("No instance to publish, this is a bug.")

        if not collected_count == len(assignment):
            self.log.warning("Subset count did not match, this is a bug.")
