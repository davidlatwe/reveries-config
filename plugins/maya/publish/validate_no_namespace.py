
import pyblish.api
from reveries import plugins


class RepairInvalid(plugins.RepairInstanceAction):

    label = "Remove Namespaces"


class ValidateNoNamespace(pyblish.api.InstancePlugin):
    """Ensure the nodes don't have a namespace"""

    families = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
    ]
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "No Namespaces"
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        context = instance.context
        protected = context.data.get("referencedNamespaceContent", set())

        invalid = [node for node in cmds.ls(instance, long=True)
                   if node not in protected and get_namespace(node)]

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("Namespaces found: {0}".format(invalid))
            raise Exception("<No Namespaces> Failed.")

        self.log.info("%s <No Namespaces> Passed." % instance)

    @classmethod
    def fix_invalid(cls, instance):

        import pymel.core as pm

        # Get nodes with pymel since we'll be renaming them
        # Since we don't want to keep checking the hierarchy
        # or full paths
        invalid = cls.get_invalid(instance)

        invalid_nodes = pm.ls(invalid)

        for node in invalid_nodes:
            namespace = node.namespace()
            if namespace:
                name = node.nodeName()
                node.rename(name[len(namespace):])


def get_namespace(node_name):
    # ensure only node's name (not parent path)
    node_name = node_name.rsplit("|")[-1]
    # ensure only namespace
    return node_name.rpartition(":")[0]
