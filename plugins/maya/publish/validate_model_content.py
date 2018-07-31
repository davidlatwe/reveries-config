import pyblish.api
from reveries.maya import action
from maya import cmds


class ValidateModelContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'model' family

    - Must only contain: transforms, meshes and groups
    - At least one mesh

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.1
    actions = [action.SelectInvalidAction]
    hosts = ["maya"]
    label = "Model Content"

    def process(self, instance):
        # Ensure only valid node types
        allowed = ('mesh', 'transform')
        nodes = cmds.ls(instance, long=True)
        valid = cmds.ls(instance, long=True, type=allowed)
        invalid = set(nodes) - set(valid)

        if invalid:
            self.log.error("These nodes are not allowed: %s" % invalid)
            raise Exception("%s <Model Content> Failed." % instance)

        self.log.info("%s <Model Content> Passed." % instance)
