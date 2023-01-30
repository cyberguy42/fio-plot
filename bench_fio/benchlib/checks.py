#!/usr/bin/env python3
import shutil
import sys
import os
from pathlib import Path
from . import runfio

def check_if_fio_exists():
    command = "fio"
    if shutil.which(command) is None:
        print("Fio executable not found in path. Is Fio installed?")
        print()
        sys.exit(1)


def check_fio_version():
    """The 3.x series .json format is different from the 2.x series format.
    This breaks fio-plot, thus this older version is not supported.
    """

    command = ["fio", "--version"]
    result = runfio.run_raw_command(command).stdout
    result = result.decode("UTF-8").strip()
    if "fio-3" in result:
        return True
    elif "fio-2" in result:
        print(f"Your Fio version ({result}) is not compatible. Please use Fio-3.x")
        sys.exit(1)
    else:
        print("Could not detect Fio version.")
        sys.exit(1)

def check_encoding():
    try:
        print("\u3000")  # blank space
    except UnicodeEncodeError:
        print()
        print(
            "It seems your default encoding is not UTF-8. This script requires UTF-8."
        )
        print(
            "You can change the default encoding with 'export PYTHONIOENCODING=UTF-8'"
        )
        print("Or you can run the script like: PYTHONIOENCODING=utf-8 ./bench_fio")
        print("Changing the default encoding could affect other applications, beware.")
        print()
        exit(90)

def check_target_type(target, settings):
    """Validate path and file / directory type.
    It also returns the appropritate fio command line parameter based on the
    file type.

    NEEDS OVERHAUL
    """
    filetype = settings["type"]
    keys = ["file", "device", "directory", "rbd"]

    test = {keys[0]: Path.is_file, keys[1]: Path.is_block_device, keys[2]: Path.is_dir}

    parameter = {keys[0]: "filename", keys[1]: "filename", keys[2]: "directory"}

    if not filetype == "rbd":

        if not os.path.exists(target) and not settings["remote"]:
            print(f"Benchmark target {filetype} {target} does not exist.")
            sys.exit(10)

        if filetype not in keys:
            print(f"Error, filetype {filetype} is an unknown option.")
            exit(123)

        check = test[filetype]

        path_target = Path(target)  # path library needs to operate on path object

        if not settings["remote"]:
            if check(path_target):
                return parameter[filetype]
            else:
                print(f"Target {filetype} {target} is not {filetype}.")
                sys.exit(10)
        else:
            return parameter[filetype]
    else:
        return None

def check_settings(settings):
    """Some basic error handling."""

    check_fio_version()

    if not os.path.exists(settings["template"]):
        print()
        print(f"The specified template {settings['template']} does not exist.")
        print()
        sys.exit(6)

    if settings["type"] not in ["device", "rbd"] and not settings["size"]:
        print()
        print("When the target is a file or directory, --size must be specified.")
        print()
        sys.exit(4)

    if settings["type"] == "directory" and not settings["remote"]:
        for item in settings["target"]:
            if not os.path.exists(item):
                print(f"\nThe target directory ({item}) doesn't seem to exist.\n")
                sys.exit(5)

    if settings["type"] == "rbd":
        if not settings["ceph_pool"]:
            print(
                "\nCeph pool (--ceph-pool) must be specified when target type is rbd.\n"
            )
            sys.exit(6)

    if settings["type"] == "rbd" and settings["ceph_pool"]:
        if settings["template"] == "./fio-job-template.fio":
            print(
                "Please specify the appropriate Fio template (--template).\n\
                    The example fio-job-template-ceph.fio can be used."
            )
            sys.exit(7)

    if not settings["output"]:
        print()
        print("Must specify mandatory --output parameter (name of benchmark output folder)")
        print()
        sys.exit(9)

    mixed_count = 0
    for mode in settings["mode"]:
        writemodes = ['write', 'randwrite', 'rw', 'readwrite', 'trimwrite']
        if mode in writemodes and not settings["destructive"]:
            print(f"\n Mode {mode} will overwrite data on {settings['target']} but destructive flag not set.\n")
            sys.exit(1)
        if mode in settings["mixed"]:
            mixed_count+=1
            if not settings["rwmixread"]:
                print(
                    "\nIf a mixed (read/write) mode is specified, please specify --rwmixread\n"
                )
                sys.exit(8)
        if mixed_count > 0:
            settings["loop_items"].append("rwmixread")
   
    if settings["remote"]:
        hostlist = settings["remote"]
        if not os.path.exists(hostlist):
                print(f"The list of remote hosts ({hostlist}) doesn't seem to exist.\n")
                sys.exit(5)