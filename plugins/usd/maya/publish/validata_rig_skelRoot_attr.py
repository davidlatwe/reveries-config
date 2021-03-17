import pyblish.api


class ValidateRigSkelRootAttribute(pyblish.api.InstancePlugin):
    """Check USD "USD_typeName" attribute exists.
    """

    label = "Validate Rig SkelRoot Attribute"
    order = pyblish.api.ValidatorOrder + 0.132
    hosts = ["maya"]

    families = ["reveries.rig.skeleton"]

    def process(self, instance):
        import maya.cmds as cmds

        skel_root = r'|ROOT|Group'

        if not cmds.objExists(skel_root):
            raise Exception(r'"|ROOT|Group" not exists.')

        # Check 'USD_typeName' attribute exists
        if not cmds.attributeQuery('USD_typeName', node=skel_root, ex=True):
            cmds.addAttr(skel_root, longName='USD_typeName', dt='string')
        cmds.setAttr(
            '{}.USD_typeName'.format(skel_root), 'SkelRoot', type='string')
