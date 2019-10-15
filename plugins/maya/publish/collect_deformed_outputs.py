
import pyblish.api
import maya.cmds as cmds

from reveries.maya import lib, pipeline


class CollectDeformedOutputs(pyblish.api.InstancePlugin):
    """Collect out geometry data for instance.

    Only visible objects will be cached.

    If the caching source has any objectSet which name is or endswith
    "OutSet", will create instances from them. For "OutSet" that has
    prefix, will use that prefix as variant of subset.

    For example:
             "OutSet" -> "pointcache.Boy_model_01_Default"
          "SimOutSet" -> "pointcache.Boy_model_01_Sim"
        "ClothOutSet" -> "pointcache.Boy_model_01_Cloth"

    If no "OutSet", collect deformable nodes directly from instance
    member (selection).

    """

    order = pyblish.api.CollectorOrder - 0.2999
    label = "Collect Deformed Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache",
    ]

    def process(self, instance):

        # Frame range
        if instance.data["staticCache"]:
            start_frame = cmds.currentTime(query=True)
            end_frame = cmds.currentTime(query=True)
        else:
            get = (lambda f: cmds.playbackOptions(query=True, **f))
            start_frame = get({"minTime": True})
            end_frame = get({"maxTime": True})

        members = instance[:]
        out_sets = list()

        # Find OutSet from subset group nodes
        for group in cmds.ls(members, type="transform", long=True):
            if cmds.listRelatives(group, shapes=True):
                continue

            try:
                container = pipeline.get_container_from_group(group)
            except AssertionError:
                # Not a subset group node
                continue

            nodes = cmds.sets(container, query=True)
            sets = [
                s for s in cmds.ls(nodes, type="objectSet")
                if s.endswith("OutSet")
            ]
            if sets:
                out_sets += sets
                members.remove(group)

        # Collect cacheable nodes

        created = False
        backup = instance

        if out_sets:
            # Cacheables from OutSet of loaded subset
            out_cache = dict()

            for node in out_sets:
                name = node.rsplit(":", 1)[-1][:-len("OutSet")] or "Default"
                self.log.info(name)
                namespace = lib.get_ns(node)
                set_member = cmds.sets(node, query=True) or []
                cacheables = lib.pick_cacheable(set_member)
                cacheables = lib.get_visible_in_frame_range(cacheables,
                                                            int(start_frame),
                                                            int(end_frame))
                # Plus locator
                cacheables += self.pick_locators(set_member)

                out_cache[(namespace, name)] = cacheables

                for n in cacheables:
                    if n in members:
                        members.remove(n)

            # Re-Create instances
            context = instance.context
            source_data = instance.data

            for (namespace, name), cacheables in out_cache.items():

                if not cacheables:
                    self.log.debug("Skip empty OutSet %s in %s"
                                   % (name, namespace))
                    continue

                namespace = namespace[1:]  # Remove root ":"
                # For filesystem, remove other ":" if the namespace is nested
                namespace = namespace.replace(":", "._.")

                instance = context.create_instance(namespace + "." + name)
                created = True

                instance.data.update(source_data)
                instance.data["subset"] = ".".join(["pointcache",
                                                    namespace,
                                                    name])
                instance[:] = cacheables
                instance.data["outCache"] = cacheables
                instance.data["requireAvalonUUID"] = cacheables
                instance.data["startFrame"] = start_frame
                instance.data["endFrame"] = end_frame

                self.assign_contractor(instance)

        if not members:
            # Nothing left, all in/has OutSet

            if not created:
                cmds.error("No pointcache instance created.")
            else:
                context.remove(backup)

        else:
            # Cache nodes that were not in any OutSet

            instance = backup

            # Cacheables from instance member
            cacheables = lib.pick_cacheable(members)
            cacheables = lib.get_visible_in_frame_range(cacheables,
                                                        int(start_frame),
                                                        int(end_frame))
            # Plus locator
            cacheables += self.pick_locators(members)

            instance[:] = cacheables
            instance.data["outCache"] = cacheables
            instance.data["requireAvalonUUID"] = cacheables
            instance.data["startFrame"] = start_frame
            instance.data["endFrame"] = end_frame

            self.assign_contractor(instance)

    def pick_locators(self, members):
        return cmds.listRelatives(cmds.ls(members, type="locator"),
                                  parent=True,
                                  fullPath=True) or []

    def assign_contractor(self, instance):
        if instance.data["deadlineEnable"]:
            instance.data["useContractor"] = True
            instance.data["publishContractor"] = "deadline.maya.script"
