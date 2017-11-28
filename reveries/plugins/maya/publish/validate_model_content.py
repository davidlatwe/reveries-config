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

    @classmethod
    def get_invalid(cls, instance):

        hierarchy = instance.data.get("hierarchy", None)
        if not hierarchy:
            cls.log.error("Instance has no nodes!")
            return instance

        if not instance.data.get("meshes", None):
            cls.log.error("Instance has no meshes!")
            return instance

        # Ensure only valid node types
        allowed = ('mesh', 'transform')
        nodes = cmds.ls(hierarchy, long=True)
        valid = cmds.ls(hierarchy, long=True, type=allowed)
        invalid = set(nodes) - set(valid)

        if invalid:
            cls.log.error("These nodes are not allowed: %s" % invalid)

        return list(invalid)

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("%s <Model Content> Failed." % instance)

        self.log.info("%s <Model Content> Passed." % instance)
