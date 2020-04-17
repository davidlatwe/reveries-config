
import pyblish.api


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
    order = pyblish.api.ValidatorOrder - 0.1
    hosts = ["maya"]
    families = ["reveries.model"]

    def process(self, instance):

        root = list(self.get_roots(instance))

        if not (len(root) == 1 and root[0].endswith("|ROOT")):
            self.log.error(
                "'%s' Must have a single root called 'ROOT'." % (instance)
            )
            raise Exception("%s <Model Assembly> Failed." % instance)

    def get_roots(self, nodes):
        from maya import cmds

        nodes = sorted(cmds.ls(nodes, long=True), reverse=True)
        roots = set()

        head = None
        while nodes:
            this = head or nodes.pop()
            that = nodes.pop()

            if that.startswith(this):
                head = this
            else:
                roots.add(this)
                head = that

            roots.add(head)

        return roots
