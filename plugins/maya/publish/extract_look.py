
import os
import json
import contextlib

import pyblish.api

from avalon.maya.pipeline import parse_container
from avalon.pipeline import get_representation_context
from reveries.plugins import PackageExtractor


class ExtractLook(PackageExtractor):
    """Export shaders for rendering

    Shaders are associated with an "mdID" attribute on each *transform* node.
    The extracted file is then given the name of the shader, and thereafter
    a relationship is created between a mesh and a file on disk.

    """

    label = "Extract Look"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.look"]

    representations = [
        "LookDev"
    ]

    def extract_LookDev(self):

        from maya import cmds
        from avalon import maya
        from reveries.maya import lib, capsule

        entry_file = self.file_name("ma")
        package_path = self.create_package(entry_file)

        # Extract shaders
        #
        entry_path = os.path.join(package_path, entry_file)

        self.log.info("Extracting shaders..")

        with contextlib.nested(
            maya.maintained_selection(),
            capsule.undo_chunk(),
            capsule.no_refresh(),
        ):
            # From texture extractor
            file_node_path = self.context.data.get("fileNodePath")
            if file_node_path is not None:
                # Change texture path to published location
                for file_node in cmds.ls(self.member, type="file"):
                    attr_name = file_node + ".fileTextureName"
                    final_path = file_node_path[file_node]

                    # Set texture file path to publish location
                    cmds.setAttr(attr_name, final_path, type="string")

            # Select full shading network
            # If only select shadingGroups, and if there are any node
            # connected to Dag node (i.e. drivenKey), then the command
            # will not only export selected shadingGroups' shading network,
            # but also export other related DAG nodes (i.e. full hierarchy)
            cmds.select(self.member,
                        replace=True,
                        noExpand=True)

            cmds.file(entry_path,
                      options="v=0;",
                      type="mayaAscii",
                      force=True,
                      exportSelected=True,
                      preserveReferences=False,
                      constructionHistory=False)

        # Serialise shaders relationships
        #
        link_file = self.file_name("json")
        link_path = os.path.join(package_path, link_file)

        self.log.info("Serialising shaders..")

        shader_by_id = lib.serialise_shaders(self.data["dagMembers"])

        # Animatable attrs
        # Custom attributes in assembly node which require to be animated.
        self.log.info("Serialising animatable attributes..")
        animatable = dict()
        root = cmds.ls(self.data["dagMembers"], assemblies=True)
        if root:
            root = root[0]
            for attr in cmds.listAttr(root, userDefined=True) or list():
                animatable[attr] = cmds.listConnections(root + "." + attr,
                                                        destination=True,
                                                        source=False,
                                                        plugs=True)

        meshes = cmds.ls(self.data["dagMembers"],
                         visible=True,
                         noIntermediate=True,
                         type="mesh")

        # CreaseSet
        crease_sets = dict()
        creases = list()

        for node in meshes:
            creases += cmds.ls(cmds.listSets(object=node), type="creaseSet")

        creases = list(set(creases))

        for cres in creases:
            level = cmds.getAttr("creaseLevel")
            if level not in crease_sets:
                crease_sets[level] = list()
            crease_sets[level] += cmds.sets(cres, query=True)

        # VRay Attributes
        vray_attrs = dict()

        try:
            from reveries.maya import vray
        except RuntimeError as e:
            self.log.debug(e)
        else:
            for node in meshes:
                # - shape
                values = vray.attributes_gather(node)
                if values:
                    vray_attrs[node] = values

                # - transfrom
                parent = cmds.listRelatives(node, parent=True)
                if parent:
                    values = vray.attributes_gather(parent[0])
                    if values:
                        vray_attrs[parent[0]] = values

        # Get model subset id
        targets = list()
        for container_name in self.data["pairedContainers"]:
            model_container = parse_container(container_name)
            representation_id = model_container["representation"]
            context = get_representation_context(representation_id)
            targets.append(context["subset"]["_id"])

        relationships = {
            "shaderById": shader_by_id,
            "animatable": animatable,
            "creaseSets": crease_sets,
            "vrayAttrs": vray_attrs,
        }

        self.log.info("Extracting serialisation..")
        with open(link_path, "w") as f:
            json.dump(relationships, f, indent=4)

        self.add_data({
            "linkFname": link_file,
            "targetSubsets": targets,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=package_path)
        )
