
import pyblish.api
from reveries.plugins import context_process
from reveries.maya.plugins import MayaSelectInvalidContextAction


class ValidateNoNameCollision(pyblish.api.InstancePlugin):
    """Ensure nodes' base name won't change when removing namespaces"""

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "No Name Collision"
    families = [
        "reveries.rig",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidContextAction,
    ]

    @context_process
    def process(self, context):
        invalid = self.get_invalid(context)

        if invalid:
            raise Exception("Name collision found.")

    @classmethod
    def get_invalid(cls, context):
        from maya import cmds

        invalid = list()

        for node in context.data["referencedNamespaceContent"]:
            # Compose the leaf node name without namespace and see if it
            # exists. This ensure that when the namespace been removed,
            # base name stays the same.
            # For example, we have two nodes `foo:A|foo:B` and `foo:A|B`,
            # and the namespace `foo` is going to be removed. The node
            # `foo:A|B` is the invalid node and MUST rename since there
            # will be two `A|B` node when the namespace is gone, and we
            # don't wont it to be auto-renamed to `A|B1`.
            # (Note) This assumes the node has only one namespace depth,
            # hierarchical namespace will not work right.
            parts = node.rsplit("|", 1)
            leaf = ":".join(parts.pop().split(":")[-1])
            renamed = "|".join(parts + [leaf])

            if cmds.objExists(renamed):
                invalid.append(renamed)

        return invalid
