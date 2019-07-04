
import pyblish.api
import maya.cmds as cmds

from reveries.maya import lib, pipeline


class CollectAnimatedOutputs(pyblish.api.InstancePlugin):
    """Collect transform animated nodes

    This only collect and extract animated transform nodes,
    shape node will not be included.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect Animated Outputs"
    hosts = ["maya"]
    families = [
        "reveries.animation",
    ]

    def process(self, instance):

        variant = instance.data["subset"][len("animation"):].lower()
        members = instance[:]

        # Re-Create instances
        context = instance.context
        context.remove(instance)
        source_data = instance.data

        ANIM_SET = "ControlSet"
        out_cache = dict()

        if variant == "default":
            # Collect animatable nodes from ControlSet of loaded subset
            out_sets = list()

            for node in cmds.ls(members, type="transform", long=True):
                try:
                    container = pipeline.get_container_from_group(node)
                except AssertionError:
                    continue

                sets = cmds.ls(cmds.sets(container, query=True),
                               type="objectSet")
                out_sets += [s for s in sets if s.endswith(ANIM_SET)]

            for node in out_sets:
                name = node.rsplit(":", 1)[-1][:-len(ANIM_SET)] or "Default"
                self.log.info(name)
                namespace = lib.get_ns(node)
                animatables = cmds.ls(cmds.sets(node, query=True), long=True)

                out_cache[namespace] = (name, animatables)

        else:
            # Collect animatable nodes from instance member
            for node in cmds.ls(members, type="transform", long=True):
                namespace = lib.get_ns(node)
                try:
                    # Must be containerized
                    pipeline.get_container_from_namespace(namespace)
                except RuntimeError:
                    continue

                if namespace not in out_cache:
                    out_cache[namespace] = (variant, list())
                out_cache[namespace][1].append(node)

        for namespace, (name, animatables) in out_cache.items():
            container = pipeline.get_container_from_namespace(namespace)
            asset_id = cmds.getAttr(container + ".assetId")

            fixed_namespace = namespace[1:]  # Remove root ":"
            # For filesystem, remove other ":" if the namespace is nested
            fixed_namespace = fixed_namespace.replace(":", "._.")

            instance = context.create_instance(fixed_namespace or name)
            instance.data.update(source_data)
            instance.data["subset"] = ".".join(["animation",
                                                fixed_namespace,
                                                name])
            instance[:] = animatables
            instance.data["outAnim"] = animatables
            instance.data["animatedNamespace"] = namespace
            instance.data["animatedAssetId"] = asset_id
            # (NOTE) Although we put those animatable nodes to validate
            #        AvalonUUID existence, but currently AvalonUUID is
            #        not needed on load.
            instance.data["requireAvalonUUID"] = animatables
