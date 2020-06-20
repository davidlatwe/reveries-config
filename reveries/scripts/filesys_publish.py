
import sys
import argparse
import avalon.api
import pyblish.api
import pyblish.util
from reveries import filesys, lib


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="Pyblish [host:filesys]",
                                     description="Run publish on file system")

    parser.add_argument("-d", "--dump",
                        type=str,
                        default="",
                        help="Context or Instance dump file path.")
    parser.add_argument("-p", "--progress",
                        type=int,
                        default=-1,
                        help="Instance progressive publish frame count.")
    parser.add_argument("-u", "--update",
                        type=str,
                        nargs="*",
                        help="Instance progressive publish output file path.")
    parser.add_argument("-j", "--jobid",
                        type=str,
                        default="",
                        help="Deadline job id to be registered with.")

    data = dict()
    args = parser.parse_args(sys.argv[1:])

    if args.dump:
        data["_pyblishDumpFile"] = args.dump

    if args.progress:
        data["_progressivePublishing"] = True
        data["_progressiveStep"] = args.progress

    if args.update:
        data["_progressivePublishing"] = True
        data["_progressiveOutput"] = args.update

    if args.jobid:
        data["deadlineJobId"] = args.jobid

    # Run

    avalon.api.install(filesys)
    pyblish.api.register_target("localhost")

    context = pyblish.api.Context()
    context.data.update(data)

    if lib.publish_remote(context) != 0:
        raise Exception("FileSys publish failed.")
