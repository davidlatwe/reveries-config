import pyblish.api
from maya import cmds


class SelectInvalid(pyblish.api.Action):
    label = "Select Invalid"
    on = "failed"
    icon = "hand-o-up"

    def process(self, context, plugin):
        cmds.select(plugin.invalid)


class ValidateModelContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'model' family

    - Must only contain: transforms, meshes and groups
    - At least one mesh

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.1
    actions = [SelectInvalid]
    hosts = ["maya"]
    label = "Model Content"

    invalid = []

    def process(self, instance):
        # Ensure only valid node types
        allowed = ('mesh', 'transform')
        nodes = cmds.ls(instance, long=True)
        valid = cmds.ls(instance, long=True, type=allowed)
        self.invalid[:] = set(nodes) - set(valid)

        if self.invalid:
            self.log.error("These nodes are not allowed: %s" % self.invalid)
            raise Exception("%s <Model Content> Failed." % instance)

        self.log.info("%s <Model Content> Passed." % instance)
