
import pyblish.api


class CollectAvalonContainers(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder - 0.25
    hosts = ["maya"]
    label = "Avalon Containers"

    def process(self, context):
        import avalon.maya

        root_containers = dict()
        sub_containers = dict()

        containers = avalon.maya.pipeline.update_hierarchy(avalon.maya.ls())

        for container in containers:

            key = container["objectName"]

            if container.get("parent"):
                sub_containers[key] = container
            else:
                root_containers[key] = container

        context.data["RootContainers"] = root_containers
        context.data["SubContainers"] = sub_containers
