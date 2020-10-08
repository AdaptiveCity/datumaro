# Copyright (C) 2020 Intel Corporation
#
# SPDX-License-Identifier: MIT

import argparse

from ..util.project import load_project


def build_parser(parser_ctor=argparse.ArgumentParser):
    parser = parser_ctor()

    parser.add_argument('paths', nargs='+',
        help="Files or directories to start track")
    parser.add_argument('-p', '--project', dest='project_dir', default='.',
        help="Directory of the project to operate on (default: current dir)")
    parser.set_defaults(command=commit_command)

    return parser

def add_command(args):
    project = load_project(args.project_dir)

    project.vcs.add(args.paths)

    return 0
