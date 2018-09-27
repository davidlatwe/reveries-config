
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
        subsets = list()

        for instance in context:
            subset = instance.data["subset"]
            if subset in subsets:
                invalid.append(instance.data["name"])

            subsets.append(subset)

        return invalid
