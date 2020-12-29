
import contextlib
import pyblish.api


class ExtractModelAsMayaBinary(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Model (mb)"
    families = [
        "reveries.model",
    ]

    def process(self, instance):
        from reveries import utils

        staging_dir = utils.stage_dir()
        filename = "%s.mb" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        nodes = instance[:]

        instance.data["repr.mayaBinary._stage"] = staging_dir
        instance.data["repr.mayaBinary._files"] = [filename]
        instance.data["repr.mayaBinary.entryFileName"] = filename

        geo_id_and_hash = self.extract_mayabinary(nodes, outpath)
        assert geo_id_and_hash is not None, ("Geometry hash not calculated.")

        instance.data["repr.mayaBinary.modelProfile"] = geo_id_and_hash

    def extract_mayabinary(self, nodes, outpath):
        import maya.cmds as cmds
        from reveries.maya import capsule

        geo_id_and_hash = None

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(nodes),
            capsule.no_smooth_preview(),
            capsule.maintained_selection(),
            capsule.without_extension(),
        ):

            mesh_nodes = cmds.ls(nodes,
                                 type="mesh",
                                 noIntermediate=True,
                                 long=True)
            clay_shader = "initialShadingGroup"

            # Perform extraction
            cmds.select(nodes, noExpand=True)

            with capsule.assign_shader(mesh_nodes,
                                       shadingEngine=clay_shader):

                with capsule.undo_chunk_when_no_undo():

                    # Remove mesh history, for removing all intermediate nodes
                    transforms = cmds.ls(nodes, type="transform")
                    cmds.delete(transforms, constructionHistory=True)
                    # Remove all stray shapes, ensure no intermediate nodes
                    all_meshes = set(cmds.ls(nodes, type="mesh", long=True))
                    cmds.delete(list(all_meshes - set(mesh_nodes)))

                    geo_id_and_hash = self.hash(set(mesh_nodes))

                    cmds.file(
                        outpath,
                        force=True,
                        typ="mayaBinary",
                        exportSelectedStrict=True,
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

        return geo_id_and_hash

    def hash(self, mesh_nodes):
        import maya.cmds as cmds
        from reveries.maya import utils as maya_utils

        # Hash model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = maya_utils.MeshHasher()
        for mesh in mesh_nodes:
            # Get ID
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            id = maya_utils.get_id(transform)
            assert id is not None, ("Geometry %s has no Avalon UUID. "
                                    "This should not happend." % transform)
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
