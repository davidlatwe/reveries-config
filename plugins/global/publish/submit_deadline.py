
import pyblish.api


class SubmitDeadlineJobs(pyblish.api.ContextPlugin):

    order = pyblish.api.IntegratorOrder
    label = "Submit To Deadline"

    targets = ["deadline"]

    def process(self, context):
        assert all(result["success"] for result in context.data["results"]), (
            "Atomicity not held, aborting.")

        submitter = context.data["deadlineSubmitter"]
        submitter.submit()
