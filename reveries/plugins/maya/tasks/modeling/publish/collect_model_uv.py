import pyblish.api


class CollectModelUV(pyblish.api.InstancePlugin):
    """Collect Model UV data for model validation

    ```
    instance.data {
            model_uvSet_state: Store each mesh's UV set's UV valid
                               status
            mesh_has_uv_count: Number of how many mesh has vaild UV
    }
    ```

    """

    families = ["reveries.model"]
    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["maya"]
    label = "Model UV"

    def process(self, instance):
        self._model_uvSet_state = dict()
        instance.data.update(
            {
                "model_uvSet_state": self._model_uvSet_state,
                "mesh_has_uv_count": self._collect_uv(instance)
            }
        )

    def _collect_uv(self, instance):
        from maya import cmds

        meshes = cmds.ls(instance.data["meshes"], noIntermediate=True)
        mesh_has_uv_count = 0
        for mesh in meshes:
            uvSets = cmds.polyUVSet(mesh, query=True, allUVSets=True) or []
            # ensure unique (sometimes maya will list 'map1' twice)
            uvSets = list(set(uvSets))
            # `_model_uvSet_state` store each UV set's UV valid status
            self._model_uvSet_state[mesh] = [
                self._check_uv(mesh, uvSet) for uvSet in uvSets
            ]
            if any(self._model_uvSet_state[mesh]):
                mesh_has_uv_count += 1

        return mesh_has_uv_count

    @classmethod
    def _check_uv(cls, mesh, uvSet):
        """
        Validates while collecting process, whether the current UV set
        has non-zero UVs and at least more than the vertex count. It's
        not really bulletproof, but a simple quick validation to check
        if there are likely UVs for every face.
        """
        from maya import cmds

        uv = cmds.polyEvaluate(mesh, uvs=uvSet, uv=True)
        if uv == 0:
            return False

        vertex = cmds.polyEvaluate(mesh, vertex=True)
        if uv < vertex:
            # Workaround:
            # Maya can have instanced UVs in a single mesh, for example
            # imported from an Alembic. With instanced UVs the UV count
            # from `maya.cmds.polyEvaluate(uv=True)` will only result in
            # the unique UV count instead of for all vertices.
            #
            # Note: Maya can save instanced UVs to `mayaAscii` but cannot
            #       load this as instanced. So saving, opening and saving
            #       again will lose this information.
            map_attr = "{}.map[*]".format(mesh)
            uv_to_vertex = cmds.polyListComponentConversion(map_attr,
                                                            toVertex=True)
            uv_vertex_count = cls._len_flattened(uv_to_vertex)
            if uv_vertex_count < vertex:
                return False
            else:
                cls.log.warning("Node has instanced UV points: "
                                "{0}".format(mesh))
        return True

    @staticmethod
    def _len_flattened(components):
        """Return the length of the list as if it was flattened.

        Maya will return consecutive components as a single entry
        when requesting with `maya.cmds.ls` without the `flatten`
        flag. Though enabling `flatten` on a large list (e.g. millions)
        will result in a slow result. This command will return the amount
        of entries in a non-flattened list by parsing the result with
        regex.

        Args:
            components (list): The non-flattened components.

        Returns:
            int: The amount of entries.

        """
        import re

        assert isinstance(components, (list, tuple))
        n = 0
        for c in components:
            match = re.search("\[([0-9]+):([0-9]+)\]", c)
            if match:
                start, end = match.groups()
                n += int(end) - int(start) + 1
            else:
                n += 1
        return n
