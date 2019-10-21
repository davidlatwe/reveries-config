
import pyblish.api


class ValidateContextHasInstance(pyblish.api.ContextPlugin):
    """確認場景有物件需要發佈

    如果這個檢查出現錯誤，請使用 Creator 工具創建 Subset Instance 再進行發佈

    """

    """Context must have instance to publish

    Context must have at least one instance to publish, please create one
    if there is none.

    """

    label = "發佈項目提交"
    order = pyblish.api.ValidatorOrder - 0.49

    def process(self, context):
        msg = "No instance to publish, please create at least one instance."
        assert len(context), msg

        msg = "No instance to publish, please enable at least one instance."
        assert any(inst.data.get("publish", True) for inst in context), msg
