
import os
import pyblish.api
import avalon.io as io


class ValidateVersionUnipue(pyblish.api.InstancePlugin):

    label = "Version Unique"
    order = pyblish.api.ValidatorOrder + 0.499

    def process(self, instance):

        subset = instance.data["subset_doc"]

        if subset is not None:

            next_version = instance.data["version_next"]

            # Ensure version unique
            conflict = io.find_one({"type": "version",
                                    "parent": subset["_id"],
                                    "name": next_version})
            if conflict is not None:
                self.log.error("Conflict version ID: {}"
                               "".format(conflict["_id"]))
                msg = ("Version {0} of subset {1} already exists."
                       "".format(next_version, subset["name"]))
                self.log.critical(msg)
                raise RuntimeError(msg)

        publish_dir = instance.data["publish_dir"]

        if os.path.isdir(publish_dir):
            self.log.error("Version dir exists: {}".format(publish_dir))
            msg = "Version dir existed, publish abort."
            self.log.error(msg)
            raise RuntimeError(msg)
