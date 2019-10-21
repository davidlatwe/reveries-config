
import pyblish.api


class ValidateSubsetUnique(pyblish.api.ContextPlugin):
    """確認正在發佈的所有物件 (Subset Instance) 沒有重複名稱

    同時間不能發佈相同 Subset 名稱的內容。

    """

    """No duplicated subset

    You can not publish multiple subsets with the same subset name.

    """

    label = "無重複 Subset"
    order = pyblish.api.ValidatorOrder - 0.44

    def process(self, context):
        invalid = self.get_invalid(context)

        if not len(invalid) == 0:
            msg = ("Instances has duplicated subset:\n    " +
                   "\n    ".join(invalid) +
                   "\n")

            self.log.error(msg)
            raise AssertionError(msg)

    @classmethod
    def get_invalid(cls, context):
        invalid = list()
        subsets = dict()

        for instance in context:
            # Same subset but different 'extractType' (representation)
            # will be processed as different thing.
            asset = instance.data["asset"]
            extract_type = "@" + instance.data.get("extractType", "*")
            subset = instance.data["subset"] + extract_type
            if asset in subsets:
                if subset in subsets[asset]:
                    invalid.append(instance.data["objectName"])
                else:
                    subsets[asset].append(subset)
            else:
                subsets[asset] = [subset]

        return invalid
