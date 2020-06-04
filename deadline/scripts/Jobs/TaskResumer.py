"""
Task Resumer

Resume suspended tasks from given frame ranges.

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
    scriptDialog.SetTitle("Task Resumer - Resume suspended tasks in batch")

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid(
        "FramesLabel",    
        "LabelControl",
        "Frames To Resume:",
        0, 0,
        expand=False,
    )
    scriptDialog.AddControlToGrid(
        "FramesMultiLineText",
        "MultiLineTextControl",
        "",
        1, 0,
        tooltip=("A comma-separated collection of single frames or "
                 "frame ranges. ex: 1-2, 3, 4-6, 10-20@3"),
        expand=False,
    )
    OkButton = scriptDialog.AddControlToGrid(
        "OkButton",
        "ButtonControl",
        "Apply",
        2, 0,
        expand=False,
    )
    closeButton = scriptDialog.AddControlToGrid(
        "CloseButton",
        "ButtonControl",
        "Cancel",
        2, 1,
        expand=False
    )
    scriptDialog.EndGrid()

    OkButton.ValueModified.connect(OkButtonPressed)
    closeButton.ValueModified.connect(scriptDialog.CloseDialog)

    scriptDialog.ShowDialog(True)


def OkButtonPressed(*args):
    global scriptDialog

    frames = str(scriptDialog.GetValue("FramesMultiLineText"))
    if process(frames):
        scriptDialog.CloseDialog()


def process(frames):

    frame_nums = parse_frames(frames)
    if not frame_nums:
        scriptDialog.ShowMessageBox("Empty Frame List!", "Error")
        return

    jobIds = MonitorUtils.GetSelectedJobIds()

    for jobId in jobIds:
        job = RepositoryUtils.GetJob(jobId, True)
        tasks = RepositoryUtils.GetJobTasks(job, True)

        resume = list()
        for task in tasks:
            if task.TaskStatus != "Suspended":
                continue
            task_frames = set(task.TaskFrameList)
            if frame_nums.intersection(task_frames):
                resume.append(task)

        RepositoryUtils.ResumeTasks(job, resume)

    return True


def parse_frames(frames):
    frames = "".join(c for c in frames if c in "1234567890,-@")
    if not frames:
        return

    frame_nums = set()
    for frame in frames.split(","):
        if "-" in frame:
            start, end = frame.split("-")
            if "@" in end:
                end, step = end.split("@")
                try:
                    frame_range = range(int(start), int(end), int(step))
                except ValueError:
                    continue
            else:
                try:
                    frame_range = range(int(start), int(end))
                except ValueError:
                    continue
            frame_nums.update(frame_range)
        else:
            try:
                frame = int(frame)
            except ValueError:
                continue
            frame_nums.add(frame)

    return frame_nums
