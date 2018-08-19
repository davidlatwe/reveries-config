
import pymel.core as pm
import pyblish.api


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "failed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        pm.select(plugin.invalid)


class RepairInvalid(pyblish.api.Action):
    label = "Regenerate AvalonUUID"
    on = "failed"

    def process(self, context, plugin):
        # Get nodes with pymel since we'll be renaming them
        # Since we don't want to keep checking the hierarchy
        # or full paths
        nodes = pm.ls(plugin.invalid)

        for node in nodes:
            namespace = node.namespace()
            if namespace:
                name = node.nodeName()
                node.rename(name[len(namespace):])


class ValidateNoNamespace(pyblish.api.InstancePlugin):
    """Ensure the nodes don't have a namespace"""

    families = [
        "reveries.model",
        "reveries.rig",
        "reveries.look",
    ]
    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ['maya']
    label = 'No Namespaces'

    invalid = []

    def process(self, instance):
        """Process all the nodes in the instance"""
        self.invalid[:] = [node for node in instance if get_namespace(node)]

        if self.invalid:
            self.log.error("Namespaces found: {0}".format(self.invalid))
            raise Exception("<No Namespaces> Failed.")

        self.log.info("%s <No Namespaces> Passed." % instance)


def get_namespace(node_name):
    # ensure only node's name (not parent path)
    node_name = node_name.rsplit("|")[-1]
    # ensure only namespace
    return node_name.rpartition(":")[0]
