
import os
import logging

log = logging.getLogger("APTS.publish_by_task")


def __main__(*args):
    """Run publish on task completed

    This script will run publish on any task completed, if the subset of this
    task already been published, run file integration.

    (NOTE) Post task script will not run if task has error.

    Args:
        (DeadlineRepository.Plugins): Plugin object
        (str): Script type name, e.g. "post task"

    """
    deadline_plugin = args[0]

    job = deadline_plugin.GetJob()
    task = deadline_plugin.GetCurrentTask()

    files = get_output_files(job, task)

    # (TODO) Run publish with collected file path


def get_output_files(job, task):
    files = list()

    output_directories = job.OutputDirectories
    output_filenames = job.OutputFileNames

    frames = task.TaskFrameList

    for dir in output_directories:
        for file in output_filenames:
            file = format_padding(file)
            for frame in frames:
                path = os.path.join(dir, file % frame).replace("\\", "/")
                files.append(path)

    return files


def format_padding(tail):
    padding = tail.count("#")
    if padding:
        frame_str = "%%0%dd" % padding
        tail = tail.replace("#" * padding, frame_str)

    return tail
