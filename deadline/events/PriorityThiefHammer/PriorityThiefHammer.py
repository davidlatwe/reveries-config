
import Deadline.Events
from Deadline.Scripting import RepositoryUtils


def GetDeadlineEventListener():
    return PriorityThiefHammerOnJobSubmitted()


def CleanupDeadlineEventListener(eventListener):
    eventListener.Cleanup()


class PriorityThiefHammerOnJobSubmitted(Deadline.Events.DeadlineEventListener):

    def __init__(self):
        self.OnJobSubmittedCallback += self.OnJobSubmitted

    def Cleanup(self):
        del self.OnJobSubmittedCallback

    def OnJobSubmitted(self, job):
        if job.JobPriority > 80:
            job.JobPriority = 70
            RepositoryUtils.SaveJob(job)
            print("Job submitted with priority over 80. Fall back to 70, Bam !")
