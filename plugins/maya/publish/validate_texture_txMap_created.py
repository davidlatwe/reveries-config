
import os
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateTextureTxMapCreated(pyblish.api.InstancePlugin):
    """Ensure all texture file have .tx map created

    If you got error from this validation, please use Arnold's 'Tx Manager'
    to check missing .tx maps, or rendering with 'Auto-convert Textures to TX'
    option enabled.

    (NOTE): This could not 100% sure that all .tx maps were update-to-date, but
            at least we could ensure each of them has a .tx version of itself.

            To really ensure all .tx map updated, we have a pluging called "En-
            sure Tx Updated" at extraction phase to do this task. This design
            should be able to give more chances for human eyes checking and
            reduce the chances that blindly creating .tx files at extracting.

    """

    order = pyblish.api.ValidatorOrder
    label = "Tx Map Created"
    hosts = ["maya"]
    families = [
        "reveries.texture",
        "reveries.standin",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    def process(self, instance):
        if not instance.data.get("useTxMaps"):
            self.log.debug("No .tx map needed.")
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Not all texture have .tx map created, "
                            "please use 'Tx Manager' or create them "
                            "with a render.")

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()
        for data in instance.data.get("fileData", []):
            node = data["node"]
            for file in data["fnames"]:
                file_path = os.path.join(data["dir"], file)
                if not os.path.isfile(file_path):
                    cls.log.warning("File node '%s' map not exists, "
                                    "TX validation skip." % node)
                    continue

                tx_path = os.path.splitext(file_path)[0] + ".tx"
                if not os.path.isfile(tx_path):
                    cls.log.error(file_path)
                    invalid.append(node)
                    break

        return invalid

    @classmethod
    def fix_invalid(cls, instance):
        # (TODO) maketx for sequence
        pass
