
import pyblish.api


class AvalonSceneReady(pyblish.api.ContextPlugin):
    """標記場景為預備狀態

    場景在被標記為預備狀態之後，如果有任何物件或數值的更動，狀態就會失效

    """

    """Define current scene in ready state

    Collecte current undo count for later validation.

    """

    order = pyblish.api.CollectorOrder + 0.49999
    label = "進入預備狀態"
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds
        from reveries.maya import capsule

        # Ensure undo queue is active
        cmds.undoInfo(state=True)

        with capsule.OutputDeque() as undo_list:
            cmds.undoInfo(query=True, printQueue=True)

        context.data["_undoCount"] = len(undo_list)
