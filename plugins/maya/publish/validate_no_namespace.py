
import pymel.core as pm
import pyblish.api
from reveries.maya import action


class ValidateNoNamespace(pyblish.api.InstancePlugin):
    """Ensure the nodes don't have a namespace"""

    families = [
        "reveries.model",
        "reveries.rig"
    ]
    order = pyblish.api.ValidatorOrder + 0.45
    actions = [action.SelectInvalidAction,
               action.RepairAction]
    hosts = ['maya']
    label = 'No Namespaces'

    @staticmethod
    def get_invalid(instance):
        nodes = instance.data.get("hierarchy", None)
        return [node for node in nodes if get_namespace(node)]

    def process(self, instance):
        """Process all the nodes in the instance"""
        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("Namespaces found: {0}".format(invalid))
            raise Exception("<No Namespaces> Failed.")

        self.log.info("%s <No Namespaces> Passed." % instance)

    @classmethod
    def repair(cls, instance):
        """Remove all namespaces from the nodes in the instance"""

        invalid = cls.get_invalid(instance)

        # Get nodes with pymel since we'll be renaming them
        # Since we don't want to keep checking the hierarchy
        # or full paths
        nodes = pm.ls(invalid)

        for node in nodes:
            namespace = node.namespace()
            if namespace:
                name = node.nodeName()
                node.rename(name[len(namespace):])


def get_namespace(node_name):
    # ensure only node's name (not parent path)
    node_name = node_name.rsplit("|")[-1]
    # ensure only namespace
    return node_name.rpartition(":")[0]
