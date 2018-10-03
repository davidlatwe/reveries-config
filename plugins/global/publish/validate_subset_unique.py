
import pyblish.api


class ValidateSubsetUnique(pyblish.api.ContextPlugin):

    label = "Subset Unique"
    order = pyblish.api.ValidatorOrder - 0.44

    def process(self, context):
        invalid = self.get_invalid(context)

        if not len(invalid) == 0:
            msg = ("Instances has duplicated subset:\n    " +
                   "\n    ".join(invalid) +
                   "\n")

            self.log.error(msg)
            raise AssertionError(msg)

    @staticmethod
    def get_invalid(context):
        invalid = list()
        subsets = dict()

        for instance in context:
            asset = instance.data["asset"]
            subset = instance.data["subset"]
            if asset in subsets:
                if subset in subsets[asset]:
                    invalid.append(instance.data["name"])
                else:
                    subsets[asset].append(subset)
            else:
                subsets[asset] = [subset]

        return invalid
