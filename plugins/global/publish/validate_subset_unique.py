
import pyblish.api


class ValidateSubsetUnique(pyblish.api.InstancePlugin):
    """確認正在發佈的所有物件 (Subset Instance) 沒有重複名稱

    同時間不能發佈相同 Subset 名稱的內容。

    """

    """No duplicated subset

    You can not publish multiple subsets with the same subset name.

    """

    label = "無重複 Subset"
    order = pyblish.api.ValidatorOrder - 0.44

    def process(self, instance):
        invalid = self.get_invalid(instance)

        if not len(invalid) == 0:
            msg = ("Subset name is duplicated with:\n    " +
                   "\n    ".join(invalid) +
                   "\n")

            self.log.error(msg)
            raise AssertionError(msg)

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        this_asset = instance.data["asset"]
        this_subset = instance.data["subset"]

        others = [i for i in instance.context if i is not instance]

        for other in others:
            if not this_asset == other.data["asset"]:
                continue
            if this_subset == other.data["subset"]:
                invalid.append(other.data["objectName"])

        return invalid
