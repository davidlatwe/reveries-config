
import os
import pyblish.api


class CollectDelegatedInstance(pyblish.api.ContextPlugin):
    """Collect delegated instances form Context

    This plugin will set `instance.data["publish"] = False` if that instance
    is not delegated.

    This plugin should run after normal instance collector.

    """

    order = pyblish.api.CollectorOrder + 0.3
    label = "Delegated Instance"

    hosts = ["deadline"]

    def process(self, context):

        os_environ = os.environ.copy()
        assignment = dict()

        AVALON_CONTEXT_DATA_NAME = "AVALON_CONTEXT_DATA_NAME"
        AVALON_CONTEXT_DATA_VALUE = "AVALON_CONTEXT_DATA_VALUE"
        AVALON_DELEGATED_SUBSETS = "AVALON_DELEGATED_SUBSETS"

        for key in os_environ:
            # Context
            if key.startswith(AVALON_CONTEXT_DATA_NAME):
                # Read Context data
                #
                entry = os_environ[key]
                value = key.replace(AVALON_CONTEXT_DATA_NAME,
                                    AVALON_CONTEXT_DATA_VALUE)
                context.data[entry] = os_environ[value]

                continue

            # Instance
            if key == AVALON_DELEGATED_SUBSETS:
                # Read Instances' subset and version
                #
                for value in os_environ[key].split(";"):

                    subset_name, version_num = value.rsplit(":", 1)
                    version_num = int(version_num)

                    # Assign instance
                    assignment[subset_name] = version_num

                    self.log.info("Assigned subset {0!r}\n\tVer. Num: {1!r}"
                                  "".format(subset_name, version_num))

        self.log.info("Found {} delegated instances.".format(len(assignment)))

        collected_count = 0
        for instance in context:
            name = instance.data["subset"]
            if name in assignment:
                # version lock
                instance.data["versionNext"] = assignment[name]
                self.log.info("{} collected.".format(name))
                collected_count += 1
            else:
                # Remove not assigned subset instance
                instance.data["publish"] = False
                self.log.info("{} skipped.".format(name))

        self.log.info("Collected {} instances.".format(collected_count))

        if collected_count == 0:
            raise ValueError("No instance to publish, this is a bug.")

        if not collected_count == len(assignment):
            self.log.warning("Subset count did not match, this is a bug.")
