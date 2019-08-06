"""Deadline custom event plugin

Used for deleting dependent intergration jobs

"""
import sys

from System.IO import *
from System.Text import *

from Deadline.Events import *
from Deadline.Scripting import *


def GetDeadlineEventListener():
    return AvalonGarbageJobCollector()


def CleanupDeadlineEventListener(deadlinePlugin):
    deadlinePlugin.Cleanup()


class AvalonGarbageJobCollector(DeadlineEventListener):
    """Remove dependent Avalon intergration jobs when dependency job gets deleted
    """

    def __init__(self):
        self.OnJobDeletedCallback += self.OnJobDeleted

    def Cleanup(self):
        del self.OnJobDeletedCallback

    def OnJobDeleted(self, job):
        if not job.GetJobEnvironmentKeyValue("AVALON_ASSET"):
            # Not a Avalon Job
            return

        if job.JobName.startswith("_intergrate "):
            # This is our target to remove, skip if it's getting deleted.
            return

        # Get PyMongo from job (Not a good way)
        sys.path += job.GetJobEnvironmentKeyValue("PYTHONPATH").split(";")
        try:
            import pymongo
        except ImportError:
            print("Could not import PyMongo.")
            return

        host = "Technic-Server"  # 192.168.1.3
        port = 27100
        db_name = "deadline10db"
        col_name = "Jobs"

        client = pymongo.MongoClient(host=host, port=port)
        db = client[db_name]
        col = db[col_name]

        id = job.JobId
        batch = job.GetJobInfoKeyValue("BatchName")

        dep_ids = set()
        for doc in col.find({"Props.Batch": batch, "Props.Dep.JobID": id}):
            dep_ids.add(doc["_id"])

        for id in dep_ids:
            if RepositoryUtils.JobExists(id):
                dep_job = RepositoryUtils.GetJob(id, False)

                print("Deleting job: %s  |  %s" % (dep_job.JobName, id))
                RepositoryUtils.DeleteJob(dep_job)
