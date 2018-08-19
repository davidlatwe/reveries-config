
import pyblish.api
from maya import cmds


class ValidateLookAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    """

    label = "Look Assembly"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.look"]

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)

        if not len(root) == 1:
            self.log.error(
                "'%s' Must have a single root." % (instance)
            )
            raise Exception("%s <Look Assembly> Failed." % instance)
