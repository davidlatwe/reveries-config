
import pyblish.api


class AvalonLockNodes(pyblish.api.ContextPlugin):
    """Flush undo queue and remove the modified state of the entire scene
    """

    label = "Lock Nodes"
    order = pyblish.api.IntegratorOrder + 0.499999
    hosts = ["maya"]

    def process(self, context):
        from reveries.maya.pipeline import lock_edit, is_editable

        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        if not context.data.get("_has_privileged_instance"):
            return

        assert is_editable(), "Scene already not editable, this is a bug."

        lock_edit()
