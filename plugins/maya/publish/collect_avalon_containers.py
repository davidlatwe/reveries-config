
import pyblish.api
import avalon.maya


class CollectAvalonContainers(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder - 0.25
    hosts = ["maya"]
    label = "Avalon Containers"

    def process(self, context):
        root_containers = dict()
        sub_containers = dict()

        containers = avalon.maya.pipeline.update_hierarchy(avalon.maya.ls())

        for container in containers:

            key = container["objectName"]

            if container.get("parent"):
                sub_containers[key] = container
                self.log.debug("Sub Container: {}".format(key))
            else:
                root_containers[key] = container
                self.log.info("Root Container: {}".format(key))

        context.data["RootContainers"] = root_containers
        context.data["SubContainers"] = sub_containers
