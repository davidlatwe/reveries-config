
import os
import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


def tx_updated(source, tx):
    # TX map's modification time takes no decimal places.
    int_mtime = (lambda f: int(os.path.getmtime(f)))
    return int_mtime(source) == int_mtime(tx)


class ValidateTextureTxMapUpdated(pyblish.api.InstancePlugin):
    """Ensure all texture file have .tx map updated

    If you got error from this validation, please use Arnold's 'Tx Manager'
    to check missing .tx maps, or rendering with 'Auto-convert Textures to TX'
    option enabled.

    """

    order = pyblish.api.ValidatorOrder
    label = "Tx Map Updated"
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
            raise Exception("Not all texture have .tx map updated, "
                            "please use 'Tx Manager' or update them "
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
                    cls.log.error("<%s> has no existing TX map: %s"
                                  % (node, tx_path))
                    invalid.append(node)
                    break

                if not tx_updated(file_path, tx_path):
                    cls.log.error("<%s> has no modification time matched "
                                  "TX map: %s" % (node, tx_path))
                    invalid.append(node)
                    break

        return invalid

    @classmethod
    def fix_invalid(cls, instance):
        # (TODO) maketx for sequence
        pass
