
import pyblish.api


class SubmitDeadlineJobs(pyblish.api.ContextPlugin):

    order = pyblish.api.IntegratorOrder
    label = "Submit To Deadline"

    targets = ["deadline"]

    def process(self, context):
        if not all(result["success"] for result in context.data["results"]):
            self.log.warning("Atomicity not held, aborting.")
            return

        submitter = context.data["deadlineSubmitter"]
        submitter.submit()
