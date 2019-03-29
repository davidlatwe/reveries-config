
import pyblish.api
import avalon.io


class CollectAvalonDependencies(pyblish.api.ContextPlugin):
    """Collect Avalon dependencies from root containers
    """

    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["maya"]
    label = "Avalon Dependencies"

    def process(self, context):
        from maya import cmds

        root_containers = context.data["RootContainers"]
        container_members = dict()

        # Collect root containers' members

        for container in root_containers:
            members = set()
            members.update(cmds.ls(cmds.sets(container,
                                             query=True,
                                             nodesOnly=True),
                                   long=True))
            container_members[container] = members

        # Scan dependencies for each instance

        for instance in context:

            self.log.info("Collecting dependency: %s" % instance.data["name"])

            members = set(instance)

            # Compute dependency from the coverage between instance and
            # container.
            for con, con_member in container_members.items():

                if not members.intersection(con_member):
                    # Try history
                    history = instance.data["allHistory"]
                    if not history.intersection(con_member):
                        # Not dependent
                        continue

                namespace = root_containers[con]["namespace"]
                name = root_containers[con]["name"]

                repr_id = root_containers[con]["representation"]
                repr_id = avalon.io.ObjectId(repr_id)
                representation = avalon.io.find_one({"_id": repr_id})

                if representation is None:
                    self.log.warning("Dependency representation not found, "
                                     "this should not happen.")
                    continue

                version = avalon.io.find_one({"_id": representation["parent"]})

                self.register_dependency(instance, version["_id"])
                self.log.debug("Collected: %s - %s" % (namespace, name))

            # Register dependency from data.futureDependencies for those
            # not yet being published (containerized in scene).
            future_dependencies = instance.data["futureDependencies"]
            for name, pregenerated_version_id in future_dependencies.items():
                self.register_dependency(instance, pregenerated_version_id)
                self.log.debug("Collected (Future): %s" % name)

    def register_dependency(self, instance, version_id):
        """
        """
        version_id = str(version_id)

        if version_id not in instance.data["dependencies"]:
            instance.data["dependencies"][version_id] = {"count": 1}
        else:
            instance.data["dependencies"][version_id]["count"] += 1
