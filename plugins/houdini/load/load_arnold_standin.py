from avalon import api, io

from avalon.houdini import pipeline
from reveries.houdini.plugins import HoudiniBaseLoader
from reveries.utils import get_representation_path_


class ArnoldAssLoader(HoudiniBaseLoader, api.Loader):
    """Specific loader of Arnold Stand-in for Houdini"""

    label = "Load Arnold .ASS"
    order = -10
    icon = "coffee"
    color = "orange"
    hosts = ["houdini"]
    families = [
        "reveries.standin",
    ]
    representations = ["Ass"]

    def load(self, context, name=None, namespace=None, data=None):

        import hou

        # Format file name, Houdini only wants forward slashes
        representation = context["representation"]
        file_path = self.file_path(representation)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        obj = hou.node("/obj")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create an Arnold procedural node
        container = obj.createNode("arnold_procedural", node_name=node_name)
        container.setParms({"ar_filename": file_path})

        # Set new position for unpack node else it gets cluttered
        nodes = [container]
        for nr, node in enumerate(nodes):
            node.setPosition([0, (0 - nr)])

        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__,
                                     suffix="")

    def update(self, container, representation):

        node = container["node"]

        # Update the file path
        parents = io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)
        file_path = self.file_path(representation)
        file_path = file_path.replace("\\", "/")

        node.setParms({"ar_filename": file_path})

        # Update attribute
        node.setParms({"representation": str(representation["_id"])})

    def remove(self, container):

        node = container["node"]
        node.destroy()
