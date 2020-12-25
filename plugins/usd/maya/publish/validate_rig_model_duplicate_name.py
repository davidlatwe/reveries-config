
import pyblish.api


class ValidateRigModelDuplicateName(pyblish.api.InstancePlugin):
    """Check Model Reference has different group name
    In USD file we remove all namespace, so please make sure your
    reference group are not duplicated in your hierarchy after remove namespace

    For example:
    - ROOT
        L Group
        L Geometry
            L Robot_model_01_grp
                L Robot_model_01_:modelDefault
            L Robot_model_02_grp
                L Robot_model_02_:modelDefault
    """

    label = "Rig Check Model Reference Name"
    order = pyblish.api.ValidatorOrder + 0.131
    hosts = ["maya"]

    families = ["reveries.rig"]

    # optional = True

    def process(self, instance):
        import maya.cmds as cmds

        if not instance.data.get("publishUSD", True):
            return

        geometry_path = "|ROOT|Group|Geometry"
        if not cmds.objExists(geometry_path):
            raise RuntimeError(
                "{}: Get geometry group failed. It should be {}".format(
                    instance, geometry_path))

        children = cmds.listRelatives(geometry_path, children=True)

        children_without_ns = self._remove_ns(children)
        new_children_without_ns = set(children_without_ns)

        if len(children_without_ns) != len(new_children_without_ns):
            raise RuntimeError(
                "Has duplicated model reference group in Geometry group.")

    def _remove_ns(self, child_list):
        from reveries.maya import lib

        new_list = []
        for _child in child_list:
            namespace = lib.get_ns(_child).replace(":", "")

            new_list.append(_child.replace("{}:".format(namespace), ""))
        return new_list
