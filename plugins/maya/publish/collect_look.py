
import pyblish.api
import avalon.io
from avalon.pipeline import AVALON_CONTAINER_ID
from maya import cmds
from reveries.maya import lib


class CollectLook(pyblish.api.InstancePlugin):
    """Collect mesh's shading network and objectSets
    """

    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Collect Look"
    families = ["reveries.look"]

    def process(self, instance):
        meshes = cmds.ls(instance,
                         visible=True,
                         noIntermediate=True,
                         type="mesh")

        # Collect paired model container
        paired = list()
        containers = lib.lsAttr("id", AVALON_CONTAINER_ID)
        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            for set_ in cmds.listSets(object=transform):
                if set_ in containers and set_ not in paired:
                    paired.append(set_)
        instance.data["paired_container"] = paired

        # Collect shading networks
        shaders = cmds.listConnections(meshes, type="shadingEngine")
        upstream_nodes = cmds.listHistory(shaders)
        # (NOTE): The flag `pruneDagObjects` will also filter out
        # `place3dTexture` type node.

        # Remove unwanted types
        unwanted_types = ("groupId", "groupParts", "mesh")
        unwanted = set(cmds.ls(upstream_nodes, type=unwanted_types))
        upstream_nodes = list(set(upstream_nodes) - unwanted)

        instance.data["dag_members"] = instance[:]
        instance[:] = upstream_nodes

        # Collect previous texture file hash.
        # dict {hash: "/file/path"}
        instance.data["look_textures"] = dict()

        asset_id = instance.data["asset_doc"]["_id"]
        subset = avalon.io.find_one({"type": "subset",
                                     "parent": asset_id,
                                     "name": instance.data["subset"]})
        if subset is None:
            return

        version = avalon.io.find_one({"type": "version",
                                      "parent": subset["_id"]},
                                     {"name": True},
                                     sort=[("name", -1)])
        if version is None:
            return

        representation = avalon.io.find_one({"type": "representation",
                                             "name": "LookDev",
                                             "parent": version["_id"]},
                                            {"data.textures": True})
        if representation is None:
            raise Exception("Version exists but no representation, "
                            "this is a bug.")

        instance.data["look_textures"] = representation["data"]["textures"]
