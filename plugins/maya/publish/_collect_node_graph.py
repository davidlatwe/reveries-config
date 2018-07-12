import pyblish.api
from tuxedo.utils import snapshot


class CollectMayaNodeGraph(pyblish.api.InstancePlugin):
    """Collect Maya DAG

    ```
    instance.data {
            nodeGraph:   All descendants of the instance
    }
    ```

    """

    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["maya"]
    label = "Maya Node Graph"

    def process(self, instance):
        instance.data.update(
            {
                "nodeGraph": self._mock_node_graph(instance)
            }
        )

    def _mock_node_graph(self, instance):
        from maya import cmds

        instance += (cmds.listRelatives(instance, allDescendents=True) or [])
        snap = snapshot.MayaNodeGraph()
        snap.mock(instance)
        snap.merge()

        return snap
