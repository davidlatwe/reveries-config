
import pyblish.api
from maya import cmds


class ValidateModelAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    """

    label = "Model Assembly"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.model"]

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)

        if not root == "MODEL":
            self.log.error(
                "'%s' Must have a single root called 'MODEL'." % (instance)
            )
            raise Exception("%s <Model Assembly> Failed." % instance)
