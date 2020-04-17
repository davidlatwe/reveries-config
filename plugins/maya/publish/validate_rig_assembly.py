
import pyblish.api


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
        from maya import cmds
        from reveries.maya.lib import TRANSFORM_ATTRS

        root = cmds.ls(instance, assemblies=True, long=True)

        if not (len(root) == 1 and root[0] == "|ROOT"):
            self.log.error(
                "'%s' Must have a single root called 'ROOT'." % (instance)
            )
            raise Exception("%s <Rig Assembly> Failed." % instance)

        # Validate Keyables
        #
        keyables = cmds.listAttr(root[0], keyable=True) or list()

        # Transforms should not be keyable
        if any(attr in keyables for attr in TRANSFORM_ATTRS):
            self.log.error("Rig's assembly node 'ROOT' should not have these "
                           "attributes keyable: {}".format(TRANSFORM_ATTRS))
            raise RuntimeError

        # FacialConrtols
        # (TODO)

        # LowPoly Switch
        # (TODO)
