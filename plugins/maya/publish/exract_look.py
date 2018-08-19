
import os
import json
import pyblish.api

from reveries.plugins import repr_obj, BaseExtractor
from reveries.maya import vray


class ExtractLook(BaseExtractor):
    """Export shaders for rendering

    Shaders are associated with an "mdID" attribute on each *transform* node.
    The extracted file is then given the name of the shader, and thereafter
    a relationship is created between a mesh and a file on disk.

    """

    label = "Look"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.look"]

    representations = [
        repr_obj("LookDev", "ma")
    ]

    def dispatch(self):
        self.extract()

    def extract_LookDev(self, representation):

        from maya import cmds
        from avalon import maya
        from reveries.maya import lib, capsule

        dirname = self.extraction_dir(representation)

        # Extract Textures ?
        # perhapes, texture itself should be a family ?
        # able to publish alone, and able to publish with lookDev ?

        # Extract shaders
        #
        filename = self.extraction_fname(representation)
        out_path = os.path.join(dirname, filename)

        self.log.info("Extracting shaders..")

        with maya.maintained_selection():
            with capsule.no_refresh(with_undo=True):
                # Change texture file path to publish path
                cmds.ls(self.data["look_members"], type="file")

                # Select full shading network
                # If only select shadingGroups, and if there are any node
                # connected to Dag node (i.e. drivenKey), then the command
                # will not only export selected shadingGroups' shading network,
                # but also export other related DAG nodes (i.e. full hierarchy)
                cmds.select(self.data["look_members"],
                            replace=True,
                            noExpand=True)

                cmds.file(out_path,
                          options="v=0;",
                          type="mayaAscii",
                          force=True,
                          exportSelected=True,
                          preserveReferences=False,
                          constructionHistory=False)

        # Serialise shaders relationships
        #
        jsname = self.extraction_fname(repr_obj("_", "json"))
        json_path = os.path.join(dirname, jsname)

        self.log.info("Serialising shaders..")

        dag_set_members = lib.serialise_shaders(self.member)

        # Animatable attrs
        # Custom attributes in assembly node which require to be animated.
        self.log.info("Serialising animatable attributes..")
        animatable = dict()
        root = cmds.ls(self.member, assemblies=True)[0]
        for attr in cmds.listAttr(root, userDefined=True):
            animatable[attr] = cmds.listConnections(root + "." + attr,
                                                    destination=True,
                                                    source=False,
                                                    plugs=True)

        meshes = cmds.ls(self.member,
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

        relationships = {
            "dag_set_members": dag_set_members,
            "animatable": animatable,
            "crease_sets": crease_sets,
            "vray_attrs": vray_attrs,
        }

        self.log.info("Extracting serialisation..")
        with open(json_path, "w") as f:
            json.dump(relationships, f, indent=4)

        # Stage

        self.stage_files(representation)

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=out_path)
        )
