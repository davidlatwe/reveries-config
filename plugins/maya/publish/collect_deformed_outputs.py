
import pyblish.api
import maya.cmds as cmds

from reveries.maya import lib
from avalon.maya.pipeline import AVALON_CONTAINER_ID


def find_out_sets(nodes):
    return [member for member in cmds.ls(nodes, type="objectSet")
            if member.endswith("OutSet")]


def pick_cacheable(nodes):
    nodes = cmds.listRelatives(nodes, allDescendents=True, fullPath=True) or []
    shapes = cmds.ls(nodes,
                     type="deformableShape",
                     noIntermediate=True,
                     long=True)
    cacheables = set()
    for node in shapes:
        parent = cmds.listRelatives(node, parent=True, fullPath=True)
        transforms = cmds.ls(parent, long=True)
        cacheables.update(transforms)

    return list(cacheables)


class CollectDeformedOutputs(pyblish.api.InstancePlugin):
    """Collect out geometry data for instance.
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Deformed Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache",
    ]

    def process(self, instance):
        out_cache = dict()

        def update_out_cache(out_set, namespace):
            members = pick_cacheable(cmds.sets(out_set, query=True) or [])
            out_name = namespace[1:]  # Remove leading ":"
            if out_name not in out_cache:
                out_cache[out_name] = list()
            out_cache[out_name] += members

            self.log.info("Cacheables from {0!r} collected: {1!r}"
                          "".format(out_set, out_name))

        containers = lib.lsAttrs({"id": AVALON_CONTAINER_ID})
        out_sets = find_out_sets(instance)

        if out_sets:
            containers = {
                container: set(cmds.ls(cmds.sets(container, query=True),
                                       long=True))
                for container in containers
            }
            for out_set in out_sets:
                for container, content in containers.items():
                    if out_set in content:
                        namespace = cmds.getAttr(container + ".namespace")
                        update_out_cache(out_set, namespace)
                        break

        else:
            self.log.debug("Looking for 'OutSet' nodes..")
            collected = set(instance)

            for container in containers:
                content = cmds.ls(cmds.sets(container, query=True), long=True)

                if set(content).intersection(collected):
                    namespace = cmds.getAttr(container + ".namespace")
                    for out_set in find_out_sets(content):
                        update_out_cache(out_set, namespace)

        if not out_cache:
            self.log.info("No 'OutSet' found, cache from instance member.")
            out_cache[""] = pick_cacheable(instance)

        # Store data in the instance for the validator
        instance.data["outCache"] = out_cache

        # Assign contractor
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
