
import pyblish.api
from maya import cmds

from reveries.maya.lib import TRANSFORM_ATTRS


class ValidateRigAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    """

    label = "Rig Assembly"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.rig"]

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)

        if not (len(root) == 1 and root[0] == "RIG"):
            self.log.error(
                "'%s' Must have a single root called 'RIG'." % (instance)
            )
            raise Exception("%s <Rig Assembly> Failed." % instance)

        # Validate Keyables
        #
        keyables = cmds.listAttr(root[0], keyable=True) or list()

        # Transforms and Visibility should not be keyable
        NON_KEYABLE = TRANSFORM_ATTRS + ["visibility"]

        if any(attr in keyables for attr in NON_KEYABLE):
            self.log.error("Rig's assembly node 'RIG' should not have these "
                           "attributes keyable: {}".format(NON_KEYABLE))
            raise RuntimeError

        # FacialConrtols
        # (TODO)

        # LowPoly Switch
        # (TODO)
