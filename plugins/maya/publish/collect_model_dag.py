import pyblish.api


class CollectIntermediateObject(pyblish.api.InstancePlugin):
    """Collect maya DAG hierarchy for model valitation

    ```
    instance.data {
            hierarchy:   All descendants of the instance
            transforms: `transform` type node from hierarchy
            meshes:     `mesh` type node from hierarchy
            mesh_count: `mesh` node count (no Intermediate)
    }
    ```

    """

    families = ["reveries.model"]
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["maya"]
    label = "Intermediate Object"

    def process(self, instance):
        instance.data.update(
            {
                "hierarchy": hierarchy,
                "transforms": self._get_transforms(hierarchy),
                "meshes": self._get_meshes(hierarchy),
                "mesh_count": self._get_mesh_count(hierarchy)
            }
        )

    @staticmethod
    def _get_mesh_count(hierarchy):
        from maya import cmds
        return len(cmds.ls(hierarchy, type="mesh", noIntermediate=True) or [])
