import pyblish.api


class ValidateMeshNormals(pyblish.api.InstancePlugin):
    """Normals of a model may not be locked

    Locked normals shading during interactive use to behave
    unexpectedly. No part of the pipeline take advantage of
    the ability to lock normals.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    hosts = ["maya"]
    label = "Mesh Normals"

    def process(self, instance):
        from maya import cmds

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = list()
        for mesh in instance.data['meshes']:
            faces = cmds.polyListComponentConversion(mesh, toVertexFace=True)
            locked = cmds.polyNormalPerVertex(faces,
                                              query=True,
                                              freezeNormal=True)

            invalid.append(mesh) if any(locked) else None

        # On locked normals, indicate that validation has failed
        # with a friendly message for the user.
        if invalid:
            self.log.error(
                "'%s' Meshes found with locked normals:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Normals> Failed." % instance)

        self.log.info("%s <Mesh Normals> Passed." % instance)
