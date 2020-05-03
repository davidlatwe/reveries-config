
import pyblish.api
from reveries import plugins
from reveries.plugins import context_process


class ValidateNamespaceClean(pyblish.api.InstancePlugin):
    """Ensure container namespace is not dirty

    Sometimes subset's namespace may change or remove due to scene import
    or other reason. If that happened and container's imprinted attribute
    "namespace" didn't update, publishing subset like `setdress` may fail
    on load due to the hierarchical data was built from dirty containers.

    """

    label = "Namespace Clean"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.setdress"]
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidContextAction,
        pyblish.api.Category("Fix It"),
        plugins.RepairContextAction,
    ]

    @context_process
    def process(self, context):
        invalids = self.get_invalid(context)
        if invalids:
            raise Exception("Container namespace dirty. Click 'Fix It' "
                            "to reslove.")

    @classmethod
    def get_invalid(cls, context):
        containers = list(context.data["RootContainers"].values())
        containers += list(context.data["SubContainers"].values())
        invalids = cls.get_invalid_containers(containers)

        return [con["subsetGroup"] for con in invalids]

    @classmethod
    def get_invalid_containers(cls, containers):
        from reveries.maya import lib

        invalids = list()

        for container in containers:
            namespace = lib.get_ns(container["subsetGroup"])
            if container["namespace"] != namespace:
                invalids.append(container)

        return invalids

    @classmethod
    def fix_invalid(cls, context):
        from maya import cmds
        from reveries.maya import lib

        containers = list(context.data["RootContainers"].values())
        containers += list(context.data["SubContainers"].values())
        invalids = cls.get_invalid_containers(containers)

        for container in invalids:

            namespace = lib.get_ns(container["subsetGroup"])

            con_node = container["objectName"]
            cmds.setAttr(con_node + ".namespace", namespace, type="string")
            container["namespace"] = namespace
