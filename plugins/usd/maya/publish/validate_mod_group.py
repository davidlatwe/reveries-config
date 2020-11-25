import re

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

    @staticmethod
    def mod_ins_exists(context):
        _exists = False
        for instance in context:
            if instance.data["family"] == 'reveries.model':
                _exists = True
                break
        return _exists

    def process(self, instance):
        import maya.cmds as cmds
        from reveries.common import skip_instance

        context = instance.context

        if not instance.data.get("publishUSD", True):
            return

        if skip_instance(context, ['reveries.xgen']):
            return

        # Get root node
        subset_name = instance.data["subset"]
        set_member = cmds.sets(subset_name, q=True)
        if not set_member:
            _msg = "Get set member failed for {}".format(instance)
            self.log.error(_msg)
            raise Exception(_msg)
        self.root_node = set_member[0]

        # Start check
        _family = str(instance.data["family"])
        if _family in ['reveries.model']:
            self._model_family_check(instance)

        elif _family in ['reveries.look'] and not self.mod_ins_exists(context):
            # Running when only publish look
            self._look_family_check(instance)

    def _look_family_check(self, instance):
        import maya.cmds as cmds
        import pymel.core as pm
        from reveries.common.get_publish_files import get_files
        from reveries.common.path_resolver import PathResolver

        asset_name = instance.data['asset']

        # all_ref = pm.listReferences()
        msg = "Can't get version name from model reference. " \
              "Please check below thing:<br>" \
              "- Check your model reference from publish.<br>" \
              "- Check the version used has already " \
              "published model usd."
        model_is_ref = cmds.referenceQuery(
            self.root_node, isNodeReferenced=True)
        is_invalid = False

        if not model_is_ref:
            self._model_family_check(instance)
            return

        # Model is reference
        print("Model is reference")
        root_ref_node = cmds.referenceQuery(self.root_node, referenceNode=True)
        for ref in pm.listReferences():
            ref_node = ref.refNode
            if str(root_ref_node) == str(ref_node):
                # _path = ref.unresolvedPath()
                _path_resolver = PathResolver(file_path=ref.unresolvedPath())

                if not _path_resolver.is_publish_file():
                    is_invalid = True
                    break

                ver_name = _path_resolver.get_current_version_name()
                version = int(ver_name.split('v')[1]) if ver_name else None

                if not version:
                    is_invalid = True
                    break

                # Check current version already publish USD/geom.usda
                _filter = {"type": "asset", "name": asset_name}
                asset_data = io.find_one(_filter)

                _filter = {
                    "type": "subset",
                    "name": 'modelDefault',
                    "parent": asset_data['_id']
                }
                subset_data = io.find_one(_filter)

                pub_usd_files = get_files(
                    subset_data['_id'], version=version).get('USD', [])
                if not pub_usd_files:
                    is_invalid = True
                    msg = "The model version( you're using {version} ) " \
                          "didn't publish usd file.<br>" \
                          "Please update your reference after " \
                          "model usd publish.".format(
                            version="v{:03d}".format(int(version)))
                    break
                break

        if is_invalid:
            self.log.error(msg)
            raise Exception("MOD group check failed.")

    def _model_family_check(self, instance):
        import maya.cmds as cmds
        from reveries.maya import utils

        if not cmds.objExists("|ROOT"):
            self.log.error("")
            raise Exception("MOD group check failed.")

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
