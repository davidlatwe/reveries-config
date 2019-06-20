
import pyblish.api
import maya.cmds as cmds


class CollectHierarchyData(pyblish.api.InstancePlugin):
    """Collect hierarcial container data
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Hierarchy Data"
    families = [
        "reveries.setdress",
    ]

    def process(self, instance):

        subset_slots = list()  # subsets' reference group node's parent node
        subset_data = list()

        self.sub_containers = instance.context.data["SubContainers"]
        root_containers = instance.context.data["RootContainers"].values()

        for container in root_containers:

            subset_group = container.get("subsetGroup")

            if subset_group in instance:
                if not cmds.getAttr(subset_group + ".visibility"):
                    self.log.info("Hidden subset: {!r}, skipping .."
                                  "".format(subset_group))
                    continue

                self.log.info("Collecting {!r} ..".format(subset_group))

                # The namespace stored in container was absolute name,
                # need to save as relative name.
                # e.g. ":awesome" -> "awesome"
                namespace = container["namespace"][1:]

                slot = cmds.listRelatives(subset_group,
                                          parent=True,
                                          fullPath=True)
                slot = (slot or [None])[0]

                data = {
                    "namespace": namespace,
                    "containerId": container["containerId"],
                    "slot": slot,
                    "loader": container["loader"],
                    "representation": container["representation"],
                    "hierarchy": self.walk_hierarchy(container),

                    # For extraction use, will be removed
                    "_container": container,
                }

                subset_data.append(data)

                if slot not in subset_slots:
                    subset_slots.append(slot)

        instance.data["subsetSlots"] = subset_slots
        instance.data["subsetData"] = subset_data

    def walk_hierarchy(self, container):
        child_rp = dict()

        for child in container["children"]:

            child_container = self.sub_containers[child]

            subset_group = child_container["subsetGroup"]
            if not cmds.getAttr(subset_group + ".visibility"):
                self.log.debug("Hidden child subset: {!r}, skipping .."
                               "".format(subset_group))
                continue

            child_container_id = child_container["containerId"]

            child_representation_id = child_container["representation"]
            child_namespace = child_container["namespace"].rsplit(":", 1)[-1]
            child_ident = child_representation_id + "|" + child_namespace

            child_rp[child_container_id] = {
                child_ident: self.walk_hierarchy(child_container)
            }

        return child_rp
