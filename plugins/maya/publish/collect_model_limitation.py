import pyblish.api


class CollectModelLimitation(pyblish.api.InstancePlugin):
    """Collect model production limitation for model valitation

    ```
    instance.data {
            max_poly_count:    max acceptable model poly count
            max_uv_sets_count: max acceptable model UV set count
    }
    ```

    """

    families = ["reveries.model"]
    order = pyblish.api.CollectorOrder
    host = ["maya"]
    label = "Model Limitation"

    def process(self, instance):
        instance.data.update(
            {
                "max_poly_count": self._get_max_poly_count(),
                "max_uv_sets_count": self._get_max_uv_sets_count()
            }
        )

    @staticmethod
    def _get_max_poly_count():
        return 0

    @staticmethod
    def _get_max_uv_sets_count():
        return 1
