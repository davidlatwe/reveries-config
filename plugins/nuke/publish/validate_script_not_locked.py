
import pyblish.api


class ValidateScriptNotLocked(pyblish.api.ContextPlugin):
    """Nothing can be published if script is locked
    """

    label = "Script Is Not Locked"
    order = pyblish.api.ValidatorOrder - 0.4999
    hosts = ["nuke"]

    def process(self, context):
        from reveries.nuke import pipeline

        if pipeline.is_locked():
            raise Exception("Script has been locked, please save the script "
                            "with another name.")
