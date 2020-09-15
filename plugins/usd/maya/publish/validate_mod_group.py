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

    def mod_ins_exists(self, context):
        _exists = False
        for instance in context:
            if instance.data["family"] == 'reveries.model':
                _exists = True
                break
        return _exists

    def process(self, instance):
        _family = str(instance.data["family"])
        context = instance.context

        if _family in ['reveries.model']:
            self._model_family_check(instance)

        elif _family in ['reveries.look'] and not self.mod_ins_exists(context):
            # Running when only publish look
            self._look_family_check(instance)

    def _look_family_check(self, instance):
        import pymel.core as pm
        from reveries.common.get_publish_files import get_files

        asset_name = instance.data['asset']

        all_ref = pm.listReferences()
        model_is_ref = False
        msg = ""
        is_invalid = False

        if all_ref:
            for ref in all_ref:
                _path = ref.unresolvedPath()
                if '/publish/modelDefault/' in _path:
                    model_is_ref = True
                    version = None

                    # Get current version from reference path
                    path_ver = re.findall("/publish/modelDefault/v(\S+)/", _path)
                    if path_ver:
                        version = int(path_ver[0].split('/')[0])

                    if not version:
                        is_invalid = True
                        msg = "Can't get version name from model reference. Please check below thing:<br>" \
                              "- Check your model reference from publish.<br>" \
                              "- Check the version used has already published model usd."
                        break
                        # self.log.error(msg)
                        # raise Exception("MOD group check failed.")

                    # Check current version already publish USD/geom.usda
                    _filter = {"type": "asset", "name": asset_name}
                    asset_data = io.find_one(_filter)

                    _filter = {"type": "subset", "name": 'modelDefault', "parent": asset_data['_id']}
                    subset_data = io.find_one(_filter)

                    pub_usd_files = get_files(subset_data['_id'], version=version).get('USD', [])
                    if not pub_usd_files:
                        is_invalid = True
                        msg = \
                            "The model version( you're using {version} ) didn't publish usd file.<br>" \
                            "Please update your reference after model usd publish.".format(
                                version="v{:03d}".format(int(version)))
                        break
                        # raise Exception("MOD group check failed.")

            if is_invalid:
                self.log.error(msg)
                raise Exception("MOD group check failed.")

        if not model_is_ref:
            self._model_family_check(instance)

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
