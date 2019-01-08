
import pyblish.api
import avalon.io


class CollectAvalonDependencies(pyblish.api.ContextPlugin):
    """Collect Avalon dependencies from containers
    """

    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["maya"]
    label = "Avalon Dependencies"

    def process(self, context):
        from maya import cmds

        root_containers = context.data["RootContainers"]
        container_members = dict()

        for container in root_containers:
            members = cmds.sets(container, query=True) or []
            shapes = cmds.listRelatives(members, shapes=True) or []
            members = cmds.ls(members + shapes, long=True)
            container_members[container] = set(members)

        for instance in context:

            self.log.info("Collecting dependency: %s" % instance.data["name"])

            hierarchy = set(instance)
            _history = cmds.listHistory(instance, leaf=False)
            history = set(cmds.ls(_history, long=True))
            instance_nodes = hierarchy.union(history)

            for con, con_member in container_members.items():
                if not instance_nodes.intersection(con_member):
                    # Not dependent
                    continue

                namespace = root_containers[con]["namespace"]
                name = root_containers[con]["name"]

                repr_id = root_containers[con]["representation"]
                repr_id = avalon.io.ObjectId(repr_id)
                representation = avalon.io.find_one({"_id": repr_id})
                version = avalon.io.find_one({"_id": representation["parent"]})

                self.register_dependency(instance, version["_id"])
                self.log.info("Collected: %s - %s" % (namespace, name))

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
