import os
import re
from avalon import api

from avalon.houdini import pipeline
from reveries.houdini.plugins import HoudiniBaseLoader


class VdbLoader(HoudiniBaseLoader, api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["reveries.vdbcache"]
    label = "Load VDB"
    representations = ["VDB"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import hou

        representation = context["representation"]
        file_path = self.file_path(representation)

        # Get the root node
        obj = hou.node("/obj")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create a new geo node
        container = obj.createNode("geo", node_name=node_name)

        # Remove the file node, it only loads static meshes
        # Houdini 17 has removed the file node from the geo node
        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        # Explicitly create a file node
        file_node = container.createNode("file", node_name=node_name)
        file_node.setParms({"file": self.format_path(file_path)})

        # Set display on last node
        file_node.setDisplayFlag(True)

        nodes = [container, file_node]
        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__,
                                     suffix="")

    def format_path(self, path):
        """Format file path correctly for single vdb or vdb sequence"""
        expanded_dir = os.path.dirname(os.path.expandvars(path))
        vdbs = [f for f in os.listdir(expanded_dir) if f.endswith(".vdb")]
        is_sequence = len(vdbs) > 1

        if is_sequence:
            head, tail = os.path.split(path)
            # Set <frame>.vdb to $F4.vdb
            # (TODO) The padding `$F4` is hardcoded, should be improved
            first = re.sub(r"\.(\d+)\.vdb$", ".$F4.vdb", tail)

            filename = os.path.join(head, first)
        else:
            filename = path

        filename = os.path.normpath(filename)
        filename = filename.replace("\\", "/")

        return filename

    def update(self, container, representation):

        node = container["node"]
        try:
            file_node = next(n for n in node.children() if
                             n.type().name() == "file")
        except StopIteration:
            self.log.error("Could not find node of type `alembic`")
            return

        # Update the file path
        file_path = api.get_representation_path(representation)
        file_path = self.format_path(file_path)

        file_node.setParms({"fileName": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def switch(self, container, representation):
        self.update(container, representation)
