
import pyblish.api


class ValidateSceneNotLocked(pyblish.api.ContextPlugin):
    """Nothing can be published if scene is locked
    """

    label = "Scene Is Not Locked"
    order = pyblish.api.ValidatorOrder - 0.4999
    hosts = ["maya"]

    def process(self, context):
        from avalon import maya

        if maya.is_locked():
            raise Exception("Scene has been locked, please save the scene "
                            "with another name.")
