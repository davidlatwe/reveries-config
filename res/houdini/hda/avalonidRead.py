"""Houdini Digital Asset for Unpacking `AvalonID` from alembic file

Created @chordee
Modified @davidlatwe

"""

import hou
import _alembic_hom_extensions as abc

target_attrs = ["AvalonID"]

node = hou.pwd()
geo = node.geometry()
abc_file_attr = geo.findGlobalAttrib("abcFileName")

if abc_file_attr is not None:
    abc_file = geo.attribValue(abc_file_attr)
    on_time = hou.frame() / hou.fps()

    # Add attribute if not in primitive
    for t_attr in target_attrs:
        if geo.findPrimAttrib(t_attr) is None:
            geo.addAttrib(hou.attribType.Prim, t_attr, "")

    # Read attribute from alembic by `path` and set to primitive
    prims = iter(geo.prims())

    def set_attr(prim, attr, from_path):
        """Try reading attribute from path in Alembic file and set to primitive
        Return `True` if operation sucess or `False`
        """
        result = abc.alembicArbGeometry(abc_file, from_path, attr, on_time)
        if result is not None:
            value, is_constane, scope = result
            if value:
                prim.setAttribValue(attr, value[0])
                return True
        return False

    def best_guess(prim):

        def _set_abc_from_houdini(prim, attr, path):
            return_code = set_attr(prim, attr, path)
            return return_code

        def _set_abc_from_maya(prim, attr, path):
            hierarchy = abc.alembicGetSceneHierarchy(abc_file, path)
            obj_name, obj_type, items = hierarchy

            if obj_type == "polymesh":
                # abc exported from Maya, the attribute is imprinted on
                # transform node.
                transform_path = "/".join(path.split("/")[:-1])
                return_code = set_attr(prim, attr, transform_path)
                return return_code
            return None

        def _try_both(prim, attr, path):
            if not _set_abc_from_houdini(prim, attr, path):
                _set_abc_from_maya(prim, attr, path)

        flags = set()

        path = prim.attribValue("path")
        for t_attr in target_attrs:
            return_code = _set_abc_from_houdini(prim, t_attr, path)
            if return_code:
                # This abc possible exported from Houdini
                flags.add("houdini")
            else:
                return_code = _set_abc_from_maya(prim, t_attr, path)
                if return_code:
                    # This abc possible exported from Maya
                    flags.add("maya")
                elif return_code is None:
                    # The `path` of this primitive is Not pointing to a
                    # "polymesh" type object in alembic.
                    pass
                else:
                    # Attribute not exists in that `path`
                    pass

        if len(flags) == 1:
            return {
                "houdini": _set_abc_from_houdini,
                "maya": _set_abc_from_maya,
            }[flags.pop()]

        elif len(flags) > 1:
            return _try_both

        else:
            # Try next primitive
            return None

    def set_on_guess():
        for prim in prims:
            action = best_guess(prim)
            if action is not None:
                yield action

    action = next(set_on_guess())
    for prim in prims:
        path = prim.attribValue("path")
        for t_attr in target_attrs:
            action(prim, t_attr, path)
