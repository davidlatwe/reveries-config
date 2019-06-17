
import pyblish.api
import maya.cmds as cmds

from reveries.maya import lib, pipeline


class CollectDeformedOutputs(pyblish.api.InstancePlugin):
    """Collect out geometry data for instance.

    If node's visibility is off, will not be cached, but hidden by
    displayLayer will.

    If the subset variant is "default", collect deformable nodes from
    objectSets of the loaded subset, which name is or endswith "OutSet",
    and create instances from them. For "OutSet" that has prefix, will
    use that prefix as variant of subset.

    For example:
             "OutSet" -> "pointcache.Boy_model_01_Default"
          "SimOutSet" -> "pointcache.Boy_model_01_Sim"
        "ClothOutSet" -> "pointcache.Boy_model_01_Cloth"

    If the subset variant is Not "default", collect deformable node
    from instance member (selection).

    """

    order = pyblish.api.CollectorOrder - 0.2999
    label = "Collect Deformed Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache",
    ]

    def process(self, instance):

        variant = instance.data["subset"][len("pointcache"):].lower()
        members = instance[:]

        if variant == "default":
            # Collect cacheable nodes from OutSet of loaded subset
            out_cache = dict()
            out_sets = list()
            created = False

            for node in cmds.ls(members, type="transform", long=True):
                try:
                    container = pipeline.get_container_from_group(node)
                except AssertionError:
                    continue

                sets = cmds.ls(cmds.sets(container, query=True),
                               type="objectSet")
                out_sets += [s for s in sets if s.endswith("OutSet")]

            for node in out_sets:
                name = node.rsplit(":", 1)[-1][:-len("OutSet")] or "Default"
                self.log.info(name)
                namespace = lib.get_ns(node)[1:]  # Remove root ":"
                cacheables = lib.pick_cacheable(cmds.sets(node,
                                                          query=True) or [])
                cacheables = self.cache_by_visibility(cacheables)

                out_cache[(namespace, name)] = cacheables

            # Re-Create instances
            context = instance.context
            backup = instance
            source_data = instance.data

            for (namespace, name), cacheables in out_cache.items():

                if not cacheables:
                    self.log.debug("Skip empty OutSet %s in %s"
                                   % (name, namespace))
                    continue

                instance = context.create_instance(namespace + "." + name)
                created = True

                instance.data.update(source_data)
                instance.data["subset"] = ".".join(["pointcache",
                                                    namespace,
                                                    name])
                instance[:] = cacheables
                instance.data["outCache"] = cacheables
                instance.data["requireAvalonUUID"] = cacheables

                self.assign_contractor(instance)

            if not created:
                cmds.error("No pointcache instance created.")
            else:
                context.remove(backup)

        else:
            # Collect cacheable nodes from instance member
            cacheables = lib.pick_cacheable(members)
            cacheables = self.cache_by_visibility(cacheables)

            instance[:] = cacheables
            instance.data["outCache"] = cacheables
            instance.data["requireAvalonUUID"] = cacheables

            self.assign_contractor(instance)

    def cache_by_visibility(self, cacheables):
        for node in list(cacheables):
            if not lib.is_visible(node, displayLayer=False):
                cacheables.remove(node)
        return cacheables

    def assign_contractor(self, instance):
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
