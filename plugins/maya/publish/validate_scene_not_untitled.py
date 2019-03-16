
import pyblish.api


class ValidateSceneNotUntitled(pyblish.api.ContextPlugin):

    label = "Scene Is Not Untitled"
    order = pyblish.api.ValidatorOrder - 0.4998
    hosts = ["maya"]

    def process(self, context):
        from maya import cmds

        if not cmds.file(query=True, sceneName=True):
            raise Exception("Please save the scene.")
