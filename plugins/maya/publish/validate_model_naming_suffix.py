
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidAction


class ValidateModelNamingSuffix(pyblish.api.InstancePlugin):
    """Validate geometry naming suffix

    All geometry node should have a "_GEO" suffix
    This is optional.

    """
    label = "Model Naming Suffix"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = [
        "reveries.model",
    ]

    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
    ]

    optional = True

    suffix = "_GEO"

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = list()

        transforms = cmds.listRelatives(
            cmds.ls(type="mesh", long=True, noIntermediate=True),
            parent=True,
            type="transform")

        for transform in transforms:
            if not transform.endswith(cls.suffix):
                cls.log.error("Invalid suffix: %s" % transform)
                invalid.append(transform)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception("%s <Model Naming Suffix> Failed." % instance)
