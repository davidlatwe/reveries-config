from avalon import io
import pyblish.api


class ValidateMODGroup(pyblish.api.InstancePlugin):
    """Validate MOD group exists"""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Validate MOD group"
    hosts = ["maya"]
    families = [
        "reveries.model",
        "reveries.look"
    ]

    def process(self, instance):
        import maya.cmds as cmds
        from reveries.maya import utils

        _root_children = cmds.listRelatives('ROOT')
        if 'MOD' not in _root_children:
            cmds.group(_root_children, n='MOD')

            # Add avalon uuid
            node = r'|ROOT|MOD'
            asset_name = instance.data['asset']
            # Get asset id
            _filter = {"type": "asset", "name": asset_name}
            asset_id = str(io.find_one(_filter)['_id'])

            with utils.id_namespace(asset_id):
                if utils.get_id_status(node) == utils.Identifier.Clean:
                    utils.upsert_id(node, namespace_only=True)
                else:
                    utils.upsert_id(node)

        cmds.select(cl=True)
