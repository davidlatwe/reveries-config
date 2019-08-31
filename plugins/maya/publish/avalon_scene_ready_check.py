
import pyblish.api


class AvalonCheckSceneReady(pyblish.api.ContextPlugin):
    """Validate current scene still fit the definition of *ready*

    By checking new undo commands in undo queue after collecting, and consider
    scene is not ready if there are any non-select command.

    """

    order = pyblish.api.ValidatorOrder - 0.499999
    label = "Is Scene Ready"
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds
        from reveries.maya import capsule

        if not cmds.undoInfo(query=True, state=True):
            raise Exception("Undo queue is not open, please reset.")

        with capsule.OutputDeque(format=lambda l: l.split(": ", 1)[-1].strip(),
                                 skip=context.data["_undoCount"],
                                 ) as undo_list:
            cmds.undoInfo(query=True, printQueue=True)

        while undo_list:
            history = undo_list.popleft()
            # self.log.debug(history)

            if history.startswith("select"):
                continue

            raise Exception("Scene has been modified, no longer in *ready* "
                            "state. Please reset.")
