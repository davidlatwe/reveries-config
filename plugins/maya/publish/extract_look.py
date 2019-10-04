
import os
import json
import contextlib

import pyblish.api

from maya import cmds

from reveries.plugins import PackageExtractor
from reveries.maya import utils


def read(attr_path):
    try:
        return cmds.getAttr(attr_path)
    except (RuntimeError, ValueError):
        pass


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

    def extract_LookDev(self, packager):

        from avalon import maya
        from reveries.maya import lib, capsule

        entry_file = packager.file_name("ma")
        package_path = packager.create_package()

        # Extract shaders
        #
        entry_path = os.path.join(package_path, entry_file)

        self.log.info("Extracting shaders..")

        texture = self.data.get("textureInstance")
        if texture is not None:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())
        else:
            file_node_attrs = dict()

        with contextlib.nested(
            maya.maintained_selection(),
            capsule.ref_edit_unlock(),
            # (NOTE) Ensure attribute unlock
            capsule.attribute_states(file_node_attrs.keys(), lock=False),
            # Change to published path
            capsule.attribute_values(file_node_attrs),
            capsule.no_refresh(),
        ):
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
                      constructionHistory=False,
                      channels=True,  # allow animation
                      constraints=False,
                      shader=True,
                      expressions=True)

        # Serialise shaders relationships
        #
        link_file = packager.file_name("json")
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

        surfaces = cmds.ls(self.data["dagMembers"],
                           noIntermediate=True,
                           type="surfaceShape")

        # CreaseSet
        crease_sets = dict()
        creases = list()

        for node in surfaces:
            creases += cmds.ls(cmds.listSets(object=node), type="creaseSet")

        creases = list(set(creases))

        for cres in creases:
            # Grouping crease set members with crease level value.
            level = cmds.getAttr(cres + ".creaseLevel")
            if level not in crease_sets:
                crease_sets[level] = list()

            for member in cmds.ls(cmds.sets(cres, query=True), long=True):
                node, edges = member.split(".")
                if node not in self.data["dagMembers"]:
                    continue
                # We have validated Avalon UUID, so there must be a valid ID.
                id = utils.get_id(node)
                crease_sets[level].append(id + "." + edges)

        # Arnold attributes
        arnold_attrs = dict()

        try:
            # (TODO) This should be improved. see issue #65
            from reveries.maya import arnold
        except RuntimeError as e:
            self.log.debug(e)
        else:
            ai_sets = dict()
            for objset in cmds.ls(type="objectSet"):
                if not lib.hasAttr(objset, "aiOverride"):
                    continue
                if not cmds.getAttr(objset + ".aiOverride"):
                    continue
                # Ignore pyblish family instance
                if (lib.hasAttr(objset, "id") and
                        read(objset + ".id") == "pyblish.avalon.instance"):
                    continue

                ai_sets[objset] = cmds.ls(cmds.sets(objset, query=True),
                                          long=True)

            # (TODO) Validate only transform nodes in ai set
            transforms = cmds.ls(cmds.listRelatives(surfaces, parent=True),
                                 long=True)
            for node in transforms:
                # There must be a valid ID
                id = utils.get_id(node)

                attrs = dict()

                # Collect all `ai*` attributes from shape
                shape = cmds.listRelatives(node,
                                           shapes=True,
                                           noIntermediate=True,
                                           fullPath=True) or [None]
                shape = shape[0]
                if shape is None:
                    continue

                for attr in cmds.listAttr(shape, fromPlugin=True) or []:
                    value = read(shape + "." + attr)
                    if value is not None:
                        attrs[attr] = value

                # Collect all override attributes from objectSet
                for ai_set, member in ai_sets.items():
                    if node not in member:
                        continue

                    for attr in cmds.listAttr(ai_set, userDefined=True) or []:
                        # Collect all user attributes from objecSet
                        # (NOTE) Some attribute like `castsShadows` does not
                        #        startswith "ai", but also affect rendering in
                        #        Arnold.
                        value = read(node + "." + attr)
                        if value is not None:
                            attrs[attr] = value

                arnold_attrs[id] = attrs

        # VRay Attributes
        vray_attrs = dict()

        try:
            from reveries.maya import vray
        except RuntimeError as e:
            self.log.debug(e)
        else:
            for node in surfaces:
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
            "shaderById": shader_by_id,
            "animatable": animatable,
            "creaseSets": crease_sets,
            "arnoldAttrs": arnold_attrs,
            "vrayAttrs": vray_attrs,
        }

        self.log.info("Extracting serialisation..")
        with open(link_path, "w") as f:
            json.dump(relationships, f)

        packager.add_data({
            "linkFname": link_file,
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=package_path)
        )
