
import pyblish.api


class ValidateRenderInProjectRoot(pyblish.api.InstancePlugin):

    label = "Render In Project Root"
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["filesys"]
    targets = [
        "seqparser",
    ]
    families = [
        "reveries.renderlayer"
    ]

    def process(self, instance):
        import os
        from avalon import api

        path = os.path.realpath(instance.data["stagingDir"])
        root = os.path.realpath(api.registered_root())

        # If not on same drive
        if os.path.splitdrive(path)[0] != os.path.splitdrive(root)[0]:
            self.log.error("Render sequences should be in '%s'." % root)
            raise Exception("Please move render sequences to '%s' drive."
                            % root)
