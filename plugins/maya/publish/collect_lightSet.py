
import pyblish.api

from reveries import plugins
from reveries.maya import pipeline


def create_texture_subset_from_lightSet(instance, textures):
    """
    """
    family = "reveries.texture"
    subset = instance.data["subset"]
    subset = "texture" + subset[0].upper() + subset[1:]

    data = {"useTxMaps": True}

    child = plugins.create_dependency_instance(instance,
                                               subset,
                                               family,
                                               textures,
                                               data=data)
    instance.data["textureInstance"] = child


class CollectLightSet(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect LightSet"
    families = ["reveries.lightset"]

    def process(self, instance):
        from maya import cmds

        lights = list()
        light_types = dict()
        # Find all light node from shapes
        for node in cmds.ls(instance, type="shape", long=True):
            node_type = cmds.nodeType(node)
            if "Light" in node_type:
                # (NOTE) The light node from third party render engine might
                # not inherited from Maya `renderLight` type node, hence you
                # cannot use `cmds.ls(type="light")` nor `cmds.ls(lights=True)`
                # to find them.
                # Since I found there always have "Light" in thier type name,
                # so I use this as a workaround to filter out all the light
                # nodes.
                lights.append(node)
                # Collect by type
                if node_type not in light_types:
                    light_types[node_type] = list()
                light_types[node_type].append(node)

        instance.data["lights"] = lights
        instance.data["lightsByType"] = light_types
        instance.data["dagMembers"] = instance[:]

        upstream_nodes = cmds.ls(cmds.listHistory(lights), long=True)

        # Remove nodes that are not belong to current DAG hierarchy
        for node in cmds.ls(upstream_nodes, type="transform", long=True):
            if node not in instance.data["dagMembers"]:
                upstream_nodes.remove(node)

        instance[:] = list(set(upstream_nodes + instance.data["dagMembers"]))

        self.collect_ai_mesh_light(instance)
        self.collect_ai_shader_emission(instance)

        stray = pipeline.find_stray_textures(instance)
        if stray:
            create_texture_subset_from_lightSet(instance, stray)

    def collect_ai_mesh_light(self, instance):
        from maya import cmds

        if "aiMeshLight" in instance.data["lightsByType"]:
            self.log.info("Collecting Arnold mesh light sources..")

            for lit in instance.data["lightsByType"]["aiMeshLight"]:
                mesh = cmds.listConnections(lit + ".inMesh", shapes=True)
                instance.data["lights"] += cmds.ls(mesh, long=True)

    def collect_ai_shader_emission(self, instance):
        from maya import cmds

        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            return

        self.log.info("Collecting Arnold shader emission light sources..")

        for node in cmds.ls(instance.data["dagMembers"],
                            type="mesh",
                            long=True,
                            noIntermediate=True):

            shadings = cmds.listConnections(node,
                                            type="shadingEngine",
                                            source=False,
                                            destination=True) or []
            if not len(shadings) == 1:
                continue

            shaders = cmds.listConnections(shadings[0] + ".surfaceShader",
                                           type="aiStandardSurface",
                                           source=True,
                                           destination=False) or []
            if not len(shaders) == 1:
                continue

            if not cmds.getAttr(shaders[0] + ".emission"):
                continue

            emission = cmds.listConnections(shaders[0] + ".emissionColor",
                                            type="file",
                                            source=True,
                                            destination=False) or []
            if emission:
                instance.data["lights"].append(node)
                instance += emission  # File nodes will be collected later
