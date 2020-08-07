"""
Batch Prioritize

Change job priority in batch

"""

from Deadline.Scripting import (
    MonitorUtils,
    RepositoryUtils,
)
from DeadlineUI.Controls.Scripting import DeadlineScriptDialog


def __main__():
    global scriptDialog

    scriptDialog = DeadlineScriptDialog.DeadlineScriptDialog()
    scriptDialog.SetSize(350, 100)
    scriptDialog.AllowResizingDialog(True)
    scriptDialog.SetTitle("Batch Prioritize - Change job priority in batch")

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid(
        "JobIdsLabel",
        "LabelControl",
        "Job Ids:",
        0, 0,
        expand=False,
    )
    scriptDialog.AddControlToGrid(
        "JobIdsMultiLineText",
        "MultiLineTextControl",
        "",
        1, 0,
        tooltip="A linebreak-separated collection of Job Ids",
        expand=False,
    )
    scriptDialog.AddControlToGrid(
        "PriorityLabel",
        "LabelControl",
        "Set Priority:",
        2, 0,
        tooltip="Set priority to change to",
        expand=False,
    )
    scriptDialog.AddRangeControlToGrid(
        "PriorityBox",
        "RangeControl",
        80,  # default value
        0, 100,  # min, max
        0, 1,
        2, 1,
    )
    OkButton = scriptDialog.AddControlToGrid(
        "OkButton",
        "ButtonControl",
        "Apply",
        3, 0,
        expand=False,
    )
    closeButton = scriptDialog.AddControlToGrid(
        "CloseButton",
        "ButtonControl",
        "Cancel",
        3, 1,
        expand=False
    )
    scriptDialog.EndGrid()

    OkButton.ValueModified.connect(OkButtonPressed)
    closeButton.ValueModified.connect(scriptDialog.CloseDialog)

    scriptDialog.ShowDialog(True)


def OkButtonPressed(*args):
    global scriptDialog

    job_ids = str(scriptDialog.GetValue("JobIdsMultiLineText"))
    priority = str(scriptDialog.GetValue("PriorityBox"))
    if process(job_ids, priority):
        scriptDialog.CloseDialog()


def process(job_ids, priority):

    jobIds = parse_job_ids(job_ids)
    if not jobIds:
        scriptDialog.ShowMessageBox("Empty Job List!", "Error")
        return

    jobs = list()
    for jobId in jobIds:
        job = RepositoryUtils.GetJob(jobId, True)
        if job is None:
            scriptDialog.ShowMessageBox("Job not found: %s" % jobId,
                                        "Error")
            return
        jobs.append(job)

    for job in jobs:
        job.JobPriority = priority
        RepositoryUtils.SaveJob(job)

    return True


def parse_job_ids(job_ids):
    if not job_ids:
        return
    return [id_str.strip() for id_str in job_ids.strip().split(";")]
