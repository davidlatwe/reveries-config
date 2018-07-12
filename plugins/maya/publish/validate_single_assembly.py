import pyblish.api
from maya import cmds


class ValidateSingleAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    """

    families = [
        "reveries.model",
        "reveries.rig"
    ]
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    label = "Single Assembly"

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)
        family = instance.data["family"]

        rootMap = {
            "reveries.model": ["MODEL"],
            "reveries.rig": ["RIG"]
        }

        if not root == rootMap[family]:
            self.log.error(
                "'%s' Must have a single root called %s." % (
                    instance, rootMap[family])
            )
            raise Exception("%s <Single Assembly> Failed." % instance)

        self.log.info("%s <Single Assembly> Passed." % instance)
