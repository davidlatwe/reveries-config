import pyblish.api


class CollectAvalonUUID(pyblish.api.InstancePlugin):
    """Collect certain type of node's uuid attribute, currently for model

    ```
    instance.data {
            avalon_uuid:  A dict() which the key is node's uuid and
                          the value is a list() content node's long name
                          ("None" key for node's who does not have uuid)
    }
    ```

    """

    families = ["reveries.model"]
    order = pyblish.api.CollectorOrder
    host = ["maya"]
    label = "Avalon UUID"

    def process(self, instance):
        instance.data.update(
            {
                "avalon_uuid": self._get_avalon_uuid(instance)
            }
        )

    def _get_avalon_uuid(self, instance):
        """
        Recoed every mesh's transform node's avalon uuid attribute
        """
        from maya import cmds
        from collections import defaultdict

        avalon_uuid = defaultdict(list)
        nodes = list(instance)
        nodes += cmds.listRelatives(
            instance, allDescendents=True, fullPath=True) or []

        for node in nodes:
            # Only check transforms with shapes that are meshes
            if not cmds.nodeType(node) == "transform":
                continue
            shapes = cmds.listRelatives(node, shapes=True, type="mesh") or []
            meshes = cmds.ls(shapes, type="mesh")
            if not meshes:
                continue
            # get uuid
            try:
                uuid = cmds.getAttr(node + ".avID")
            except ValueError:
                uuid = "None"
            avalon_uuid[uuid].append(node)

        return avalon_uuid
