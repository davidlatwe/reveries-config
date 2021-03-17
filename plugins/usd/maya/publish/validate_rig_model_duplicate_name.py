import collections

import pyblish.api
from reveries import plugins


def remove_ns(child_list):
    from reveries.maya import lib

    new_list = []
    for _child in child_list:
        namespace = lib.get_ns(_child).replace(":", "")
        new_list.append(_child.replace("{}:".format(namespace), ""))

    return new_list


class ValidateRigModelDuplicateName(pyblish.api.InstancePlugin):
    """Check Model reference has different group name.
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

    label = "Validate Model Reference Name"
    order = pyblish.api.ValidatorOrder + 0.131
    hosts = ["maya"]

    families = ["reveries.rig.skeleton"]

    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
    ]

    # optional = True

    @classmethod
    def get_invalid(cls, instance):
        import maya.cmds as cmds

        invalid = list()
        geometry_path = "|ROOT|Group|Geometry"

        children = cmds.listRelatives(geometry_path, children=True)

        children_without_ns = remove_ns(children)

        duplicates = [item for item, count in
                      collections.Counter(children_without_ns).items() if
                      count > 1]

        for _dup_post in duplicates:
            for _group in children:
                if _group.endswith(_dup_post):
                    invalid.append(_group)

        return invalid

    def process(self, instance):
        import maya.cmds as cmds

        geometry_path = "|ROOT|Group|Geometry"
        if not cmds.objExists(geometry_path):
            raise Exception(
                "{}: Get geometry group failed. It should be {}".format(
                    instance, geometry_path))

        invalid = self.get_invalid(instance)

        if invalid:
            raise Exception(
                "Has duplicated model reference group in Geometry group.")
