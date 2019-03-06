
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
            members = cmds.sets(container, query=True) or []
            shapes = cmds.listRelatives(members, shapes=True) or []
            members = cmds.ls(members + shapes, long=True)
            container_members[container] = set(members)

        # Scan dependencies for each instance

        for instance in context:

            self.log.info("Collecting dependency: %s" % instance.data["name"])

            # Collect nodes which related to instnace's member
            hierarchy = set(instance)

            try:
                _history = cmds.listHistory(instance, leaf=False)
            except RuntimeError:
                # Found no items to list the history for.
                _history = []

            history = set(cmds.ls(_history, long=True))
            instance_nodes = hierarchy.union(history)

            # Compute dependency from the coverage between instance and
            # container.
            for con, con_member in container_members.items():
                if not instance_nodes.intersection(con_member):
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
                self.log.info("Collected: %s - %s" % (namespace, name))

            # Register dependency from data.futureDependencies for those
            # not yet being published (containerized in scene).
            future_dependencies = instance.data["futureDependencies"]
            for name, pregenerated_version_id in future_dependencies.items():
                self.register_dependency(instance, pregenerated_version_id)
                self.log.info("Collected (Future): %s" % name)

    def register_dependency(self, instance, version_id):
        """
        """
        version_id = str(version_id)

        if version_id not in instance.data["dependencies"]:
            instance.data["dependencies"][version_id] = {"count": 1}
        else:
            instance.data["dependencies"][version_id]["count"] += 1
