"""Deadline custom scripts

Used for deleting deprecated intergration jobs

"""
from Deadline.Scripting import *


def __main__():

    for job in RepositoryUtils.GetJobs(False):
        if not job.GetJobEnvironmentKeyValue("AVALON_ASSET"):
            # Not a Avalon Job
            continue
        if not job.JobName.startswith("_intergrate "):
            # Not a Avalon Intergration Job
            continue

        all_dead = not any(RepositoryUtils.JobExists(id)
                           for id in job.JobDependencyIDs)
        if all_dead:
            print("Deleting job: %s  |  %s" % (job.JobName, job.JobId))
            RepositoryUtils.DeleteJob(job)
