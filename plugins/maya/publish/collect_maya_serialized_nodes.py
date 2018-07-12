import pyblish.api
from collections import defaultdict, OrderedDict
from maya import cmds


class CollectMayaSerializedNodes(pyblish.api.InstancePlugin):
    """Collect All descendants of the instance and serialize them

    ```
    instance.data {
            mayaNodes:   All serialized descendants of the instance
    }
    ```

    """

    order = pyblish.api.CollectorOrder - 0.19
    hosts = ["maya"]
    label = "Serialize Nodes"

    def process(self, instance):
        instance.data.update(
            {
                "mayaNodes": self._serialized_nodes(instance),
            }
        )

    @staticmethod
    def _maya_uuid(node):
        uuid = cmds.ls(node, uuid=True)
        if uuid:
            return str(uuid[0].rsplit('-', 1)[-1])
        else:
            return ""

    def _serialized_nodes(self, instance):
        # prepare vessel
        serialized_nodes = defaultdict(self._node_structure)
        # serialize all nodes
        instance += (cmds.listRelatives(instance, allDescendents=True) or [])
        for node in instance:
            long_name = cmds.ls(node, long=True)
            if long_name:
                dag_path = long_name[0]
                node_uuid = self._maya_uuid(dag_path)
                node_type = str(cmds.objectType(dag_path))
                parent_uuid = self._maya_uuid(dag_path.rsplit('|', 1)[0])
                serialized_nodes[node_uuid]["dagPath"] = dag_path
                serialized_nodes[node_uuid]["nodeType"] = node_type
                serialized_nodes[node_uuid]["parent"] = parent_uuid

        return serialized_nodes
