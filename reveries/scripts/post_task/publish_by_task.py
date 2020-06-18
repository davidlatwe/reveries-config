
import os
import logging
import subprocess

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
    frames = task.TaskFrameList

    files = get_output_files(job, frames)

    log.info("%d output files collected from %d frames."
             % (len(files), len(frames)))

    python = os.getenv("PYBLISH_FILESYS_EXECUTABLE")
    script = os.getenv("PYBLISH_FILESYS_SCRIPT")
    dumpfile = os.getenv("PYBLISH_DUMP_FILE")

    log.info("Publish executable:  %s" % python)
    log.info("Publish script:      %s" % script)
    log.info("Publish dump file:   %s" % dumpfile)

    args = [
        python,
        script,
        "--dump",
        dumpfile,
        "--progress",
        str(len(frames)),
        "--update",
        " ".join(files),
    ]
    popen = subprocess.Popen(args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output, _ = popen.communicate()
    print(output)
    if popen.returncode != 0:
        raise Exception("Publish failed, see log..")


def get_output_files(job, frames):
    files = list()

    output_directories = job.OutputDirectories
    output_filenames = job.OutputFileNames

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
