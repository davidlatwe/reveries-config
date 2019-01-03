
import pyblish.api
import avalon.io


class CollectAvalonDependencies(pyblish.api.ContextPlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["maya"]
    label = "Avalon Dependencies"

    def process(self, context):
        from maya import cmds

        root_containers = context.data["RootContainers"]
        container_members = dict()

        for container in root_containers:
            members = cmds.ls(cmds.sets(container, query=True), long=True)
            container_members[container] = set(members)

        for instance in context:
            instance.data["dependencies"] = list()
            _cached = dict()

            hierarchy = set(instance)
            _history = cmds.listHistory(instance, leaf=False)
            history = set(cmds.ls(_history, long=True))
            instance_nodes = hierarchy.union(history)

            for con, con_member in container_members.items():
                if not instance_nodes.intersection(con_member):
                    # Not dependent
                    continue

                repr_id = root_containers[con]["representation"]
                repr_id = avalon.io.ObjectId(repr_id)

                representation = avalon.io.find_one({"_id": repr_id})
                version = avalon.io.find_one({"_id": representation["parent"]})
                subset = avalon.io.find_one({"_id": version["parent"]})
                asset = avalon.io.find_one({"_id": subset["parent"]})

                if repr_id not in _cached:

                    dependency = {
                        "asset": {
                            "_id": asset["_id"],
                            "name": asset["name"],
                        },
                        "subset": {
                            "_id": subset["_id"],
                            "name": subset["name"],
                        },
                        "version": {
                            "_id": version["_id"],
                            "name": version["name"],
                        },
                        "count": 1,
                    }

                    _cached[repr_id] = dependency
                    instance.data["dependencies"].append(dependency)

                else:
                    _cached[repr_id]["count"] += 1

                self.log.info("Dependency collected: %s" % subset["name"])
