
import pyblish.api
from reveries.plugins import context_process


class CollectLoadedNamespaces(pyblish.api.InstancePlugin):
    """Collect loaded subsets' namespaces and their content
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Loaded Namespaces"
    families = [
        "reveries.rig",
    ]

    @context_process
    def process(self, context):
        from maya import cmds

        loaded_namespace = set()
        loaded_content = set()

        all_containers = dict()
        all_containers.update(context.data["RootContainers"])
        all_containers.update(context.data["SubContainers"])

        for container in all_containers.values():
            if container.get("loader") == "LookLoader":
                # lookDev does not have `subsetGroup`
                continue

            group = container["subsetGroup"]
            members = cmds.sets(container["objectName"], query=True)

            loaded_content.add(group)
            loaded_content.update(cmds.ls(members,
                                          long=True,
                                          referencedNodes=True))

            loaded_namespace.add(container["namespace"])

        context.data["loadedNamespace"] = loaded_namespace
        context.data["loadedNamespaceContent"] = loaded_content
