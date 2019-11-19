
import os
import contextlib
import pyblish.api

import maya.cmds as cmds

from reveries.maya import capsule, io, utils, lib
from reveries.plugins import PackageExtractor


class ExtractModel(PackageExtractor):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Model"
    families = ["reveries.model"]

    representations = [
        "mayaBinary",
        "Alembic",
    ]

    def extract(self):

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(self.member),
            capsule.no_smooth_preview(),
            capsule.maintained_selection(),
            capsule.without_extension(),
        ):
            super(ExtractModel, self).extract()

    def extract_mayaBinary(self, packager):
        entry_file = packager.file_name("mb")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)

        mesh_nodes = cmds.ls(self.member,
                             type="mesh",
                             noIntermediate=True,
                             long=True)
        clay_shader = "initialShadingGroup"

        # Perform extraction
        cmds.select(self.member, noExpand=True)

        with contextlib.nested(
            capsule.assign_shader(mesh_nodes, shadingEngine=clay_shader),
            capsule.undo_chunk_when_no_undo(),
        ):
            # Remove mesh history, for removing all intermediate nodes
            transforms = cmds.ls(self.member, type="transform")
            cmds.delete(transforms, constructionHistory=True)
            # Remove all stray shapes, ensure no intermediate nodes
            all_meshes = set(cmds.ls(self.member, type="mesh", long=True))
            cmds.delete(list(all_meshes - set(mesh_nodes)))

            geo_id_and_hash = self.hash(set(mesh_nodes))
            packager.add_data({"modelProfile": geo_id_and_hash})

            cmds.file(
                entry_path,
                force=True,
                typ="mayaBinary",
                exportSelected=True,
                preserveReferences=False,
                # Shader assignment is the responsibility of
                # riggers, for animators, and lookdev, for
                # rendering.
                shader=False,
                # Construction history inherited from collection
                # This enables a selective export of nodes
                # relevant to this particular plug-in.
                constructionHistory=False,
                channels=False,
                constraints=False,
                expressions=False,
            )

        packager.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )

    def extract_Alembic(self, packager):
        entry_file = packager.file_name("abc")
        package_path = packager.create_package()
        entry_path = os.path.join(package_path, entry_file)

        cmds.select(self.member, noExpand=True)

        frame = cmds.currentTime(query=True)
        io.export_alembic(
            entry_path,
            frame,
            frame,
            selection=True,
            renderableOnly=True,
            writeCreases=True,
            worldSpace=True,
            attr=[
                lib.AVALON_ID_ATTR_LONG,
            ],
            attrPrefix=[
                "ai",  # Write out Arnold attributes
            ],
        )

        packager.add_data({
            "entryFileName": entry_file,
        })

    def hash(self, mesh_nodes):
        # Hash model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = utils.MeshHasher()
        for mesh in mesh_nodes:
            # Get ID
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            id = utils.get_id(transform)
            assert id is not None, ("Some mesh has no Avalon UUID. "
                                    "This should not happend.")
            hasher.set_mesh(mesh)
            hasher.update_points()
            hasher.update_normals()
            hasher.update_uvmap()

            result = hasher.digest()
            result["hierarchy"] = transform

            # May have duplicated Id
            if id not in geo_id_and_hash:
                geo_id_and_hash[id] = list()
            geo_id_and_hash[id].append(result)

            hasher.clear()

        return geo_id_and_hash
