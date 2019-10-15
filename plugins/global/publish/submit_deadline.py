
import pyblish.api


class SubmitDeadlineJobs(pyblish.api.ContextPlugin):

    order = pyblish.api.IntegratorOrder
    label = "Submit To Deadline"

    targets = ["deadline"]

    def process(self, context):
        submitter = context.data["deadlineSubmitter"]
        submitter.submit()
