
import pyblish.api


class ValidateCollectionProcesses(pyblish.api.ContextPlugin):
    """確認先前的資料收集程序運行正常
    """

    """Validate previous collector plugins all processed without error

    Currently Pyblish only stop on validation fail, so we use this plugin
    to validate previous collecting process results.

    """

    label = "資料收集零錯誤"
    order = pyblish.api.ValidatorOrder - 0.49999

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Collected with error, there must be bugs.")
