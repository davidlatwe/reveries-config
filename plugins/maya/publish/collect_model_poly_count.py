import pyblish.api


class CollectModelPolyCount(pyblish.api.InstancePlugin):
    """Collect instance's mesh poly count for model valitation

    ```
    instance.data {
            poly_count: model instance's full poly count
    }
    ```

    """

    families = ["reveries.model"]
    order = pyblish.api.CollectorOrder + 0.2
    host = ["maya"]
    label = "Model Poly Count"

    def process(self, instance):
        instance.data.update(
            {
                "poly_count": self._get_poly_count(instance)
            }
        )

    @staticmethod
    def _get_poly_count(instance):
        from maya import cmds

        return cmds.polyEvaluate(
            cmds.ls(
                cmds.listRelatives(
                    instance,
                    allDescendents=True,
                    type='mesh'
                ),
                noIntermediate=True
            ),
            triangle=True
        )
