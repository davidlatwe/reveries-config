
import pyblish.api
import avalon.api
import avalon.io as io


class ValidateLatestVersionLoaded(pyblish.api.ContextPlugin):
    """Checking loaded subsets' version outdated or not

    Show warning if there are subset's version outdated.

    """
    order = pyblish.api.ValidatorOrder - 0.4
    label = "Latest Version Loaded"

    def process(self, context):
        host = avalon.api.registered_host()

        checked = set()
        outdated = dict()

        # We may have missing representation due to the limited
        # environment. E.g. When Out sourcing the rendering job
        # and the database overthere is incomplete.
        missing = dict()

        for container in host.ls():
            container_node = container["objectName"]
            representation_id = io.ObjectId(container["representation"])

            if representation_id in checked:
                if representation_id in outdated:
                    outdated[representation_id].append(container_node)

                if representation_id in missing:
                    missing[representation_id].append(container_node)

                continue

            checked.add(representation_id)

            representation = io.find_one({"_id": representation_id})
            if representation is None:
                missing[representation_id] = [container_node]

                continue

            version = io.find_one({"_id": representation["parent"]})
            highest_version = io.find_one({"type": "version",
                                           "parent": version["parent"]},
                                          sort=[("name", -1)])

            if version["name"] < highest_version["name"]:
                outdated[representation_id] = [container_node]

        if outdated:
            nodes = "\n".join(n for x in outdated.values() for n in x)
            self.log.warning("The following subsets are outdated :\n"
                             "" + nodes)

        if missing:
            nodes = "\n".join(n for x in missing.values() for n in x)
            self.log.warning("The following subsets are not in database :\n"
                             "" + nodes)
