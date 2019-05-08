
import pyblish.api


class ValidateCollectionProcesses(pyblish.api.ContextPlugin):
    """Validate previous collector plugins all processed without error

    Currently Pyblish only stop on validation fail, so we use this plugin
    to validate previous collecting process results.

    """

    label = "Good Collecting"
    order = pyblish.api.ValidatorOrder - 0.4999

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Collected with error, there must be bugs.")
