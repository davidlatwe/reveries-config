
import pyblish.api
from maya import cmds


class ValidateModelAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner and named "ROOT".

    For example:

        |ROOT  <---------- put publishing model in this group
            L model_grp
            |   L other_mesh_A
            L other_mesh_B
            .
            .

    """

    label = "Model Assembly"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = [
        "reveries.model",
        "reveries.look",
    ]

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)

        if not (len(root) == 1 and root[0] == "ROOT"):
            self.log.error(
                "'%s' Must have a single root called 'ROOT'." % (instance)
            )
            raise Exception("%s <Model Assembly> Failed." % instance)
