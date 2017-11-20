import pyblish.api


class CollectMayaUnknownNodes(pyblish.api.InstancePlugin):
    """Collect unknown nodes inside of instance

    ```
    instance.data {
            unknown_nodes:  current working file
    }
    ```

    """

    order = pyblish.api.CollectorOrder
    host = ["maya"]
    label = "Unknown Nodes"

    def process(self, instance):
        instance.data.update(
            {
                "unknown_nodes": self._get_unknown_nodes(instance)
            }
        )

    @staticmethod
    def _get_unknown_nodes(instance):
        from maya import cmds
        return cmds.ls(instance, type='unknown')
