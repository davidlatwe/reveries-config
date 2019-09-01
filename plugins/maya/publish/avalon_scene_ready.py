
import pyblish.api


class AvalonSceneReady(pyblish.api.ContextPlugin):
    """Define current scene in ready state

    Collecte current undo count for later validation.

    """

    order = pyblish.api.CollectorOrder + 0.49999
    label = "Scene Ready"
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds
        from reveries.maya import capsule

        # Ensure undo queue is active
        cmds.undoInfo(state=True)

        with capsule.OutputDeque() as undo_list:
            cmds.undoInfo(query=True, printQueue=True)

        context.data["_undoCount"] = len(undo_list)
