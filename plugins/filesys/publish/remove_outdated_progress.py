
import os
import pyblish.api


class RemoveOutdatedProgress(pyblish.api.InstancePlugin):
    """Remove previous integrated progress outputs"""

    label = "Remove Outdated Progress"
    order = pyblish.api.ExtractorOrder - 0.41
    hosts = ["filesys"]

    def process(self, instance):
        outdated = instance.data.get("_progressiveOutdated", [])
        if not outdated:
            self.log.info("No outdated progress.")
            return

        removed = list()

        for file in outdated:
            if os.path.isfile(file):
                self.log.debug("Removing outdated file: %s" % file)
                try:
                    os.remove(file)
                except Exception as e:
                    self.log.error("Failed to remove: %s" % file)
                    raise e
                else:
                    removed.append(file)

        self.log.info("Assume %d outdated, removed %d."
                      % (len(outdated), len(removed)))
