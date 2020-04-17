
import pyblish.api
from reveries import plugins


class CollectWriteOrder(pyblish.api.InstancePlugin):

    label = "Write Order"
    order = pyblish.api.CollectorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write"
    ]

    @plugins.context_process
    def process(self, context):

        writes = list()

        for instance in list(context):
            if instance.data["family"] != "reveries.write":
                continue

            write = instance[0]

            order = int(write["render_order"].value())
            instance.data["order"] = order

            instance.data["category"] = "Writes (ordered)"
            # Sort instance by render order
            context.remove(instance)
            writes.append(instance)

        for instance in sorted(writes, key=lambda i: i.data["order"]):
            context.append(instance)
