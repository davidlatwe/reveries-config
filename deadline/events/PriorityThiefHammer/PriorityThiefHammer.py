
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
        valid = self.GetIntegerConfigEntryWithDefault("ValidPriority", 80)
        penalty = self.GetIntegerConfigEntryWithDefault("Penalty", 70)

        if job.JobPriority > valid:
            job.JobPriority = penalty
            RepositoryUtils.SaveJob(job)
            print("Job submitted with priority over %d. Fall back to %d, Bam !"
                  % (valid, penalty))
