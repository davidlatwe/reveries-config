
import pyblish.api


class ValidateContextHasInstance(pyblish.api.ContextPlugin):
    """Context must have instance to publish

    Context must have at least one instance to publish, please create one
    if there is none.

    """

    label = "Has Instance"
    order = pyblish.api.ValidatorOrder - 0.49

    def process(self, context):
        msg = "No instance to publish, please create at least one instance."
        assert len(context), msg

        msg = "No instance to publish, please enable at least one instance."
        assert any(inst.data.get("publish", True) for inst in context), msg
