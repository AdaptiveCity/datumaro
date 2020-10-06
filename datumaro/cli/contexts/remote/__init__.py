# Copyright (C) 2020 Intel Corporation
#
# SPDX-License-Identifier: MIT

from enum import Enum
import argparse
import json
import logging as log
import os
import os.path as osp
import shutil

from datumaro.components.cli_plugin import CliPlugin
from datumaro.components.project import \
    PROJECT_DEFAULT_CONFIG as DEFAULT_CONFIG
from datumaro.components.project import Environment, Project

from ...util import (CliException, MultilineFormatter, add_subparser,
    make_file_name)
from ...util.project import generate_next_file_name, load_project


RemoteTypes = Enum('RemoteTypes', ['local', 'git'])

def build_add_parser(parser_ctor=argparse.ArgumentParser):
    builtins = sorted(Environment().extractors.items)

    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument('-n', '--name', default=None,
        help="Name of the new source")
    base_parser.add_argument('-f', '--format', required=True,
        help="Source dataset format")
    base_parser.add_argument('--skip-check', action='store_true',
        help="Skip source checking")
    base_parser.add_argument('-p', '--project', dest='project_dir', default='.',
        help="Directory of the project to operate on (default: current dir)")

    parser = parser_ctor(help="Add data source to project",
        description="""
            Adds a data source to a project. The source can be:|n
            - a dataset in a supported format (check 'formats' section below)|n
            - a Datumaro project|n
            |n
            The source can be a local path or a remote link.
            Each source type has its own parameters, which can be checked by:|n
            '%s'.|n
            |n
            Formats:|n
            Datasets come in a wide variety of formats. Each dataset
            format defines its own data structure and rules on how to
            interpret the data. For example, the following data structure
            is used in COCO format:|n
            /dataset/|n
            - /images/<id>.jpg|n
            - /annotations/|n
            |n
            In Datumaro dataset formats are supported by Extractor-s.
            An Extractor produces a list of dataset items corresponding
            to the dataset. It is possible to add a custom Extractor.
            To do this, you need to put an Extractor
            definition script to <project_dir>/.datumaro/extractors.|n
            |n
            List of builtin source formats: %s|n
            |n
            Examples:|n
            - Add a local directory with VOC-like dataset:|n
            |s|sadd local path/to/voc -f voc|n
            - Add a local file with CVAT annotations, call it 'mysource'|n
            |s|s|s|sto the project somewhere else:|n
            |s|sadd local path/to/cvat.xml -f cvat -n mysource -p somewhere/|n
            - Add a remote link to a COCO-like dataset:|n
            |s|sadd git git://example.net/repo/path/to/coco/dir -f coco|n
        """ % ('%(prog)s SOURCE_TYPE --help', ', '.join(builtins)),
        formatter_class=MultilineFormatter,
        add_help=False)
    parser.set_defaults(command=add_command)

    sp = parser.add_subparsers(dest='source_type', metavar='SOURCE_TYPE',
        help="The type of the data source "
            "(call '%s SOURCE_TYPE --help' for more info)" % parser.prog)

    dir_parser = sp.add_parser(RemoteTypes.local.name,
        help="Add local path as source", parents=[base_parser])
    dir_parser.add_argument('url',
        help="Path to the source")
    dir_parser.add_argument('--copy', action='store_true',
        help="Copy the dataset instead of saving source links")

    repo_parser = sp.add_parser(RemoteTypes.git.name,
        help="Add git repository as source", parents=[base_parser])
    repo_parser.add_argument('url',
        help="URL of the source git repository")
    repo_parser.add_argument('-b', '--branch',
        help="Branch of the source repository")
    repo_parser.add_argument('--checkout', action='store_true',
        help="Checkout the branch")

    # NOTE: add common parameters to the parent help output
    # the other way could be to use parse_known_args()
    display_parser = argparse.ArgumentParser(
        parents=[base_parser, parser],
        prog=parser.prog, usage="%(prog)s [-h] SOURCE_TYPE ...",
        description=parser.description, formatter_class=MultilineFormatter)
    class HelpAction(argparse._HelpAction):
        def __call__(self, parser, namespace, values, option_string=None):
            display_parser.print_help()
            parser.exit()

    parser.add_argument('-h', '--help', action=HelpAction,
        help='show this help message and exit')

    return parser

def add_command(args):
    project = load_project(args.project_dir)

    if args.source_type == RemoteTypes.git.name:
        name = args.name
        if name is None:
            name = osp.splitext(osp.basename(args.url))[0]

        project.sources.add(name, {
            'type': args.source_type,
            'url': args.url,
            'branch': args.branch,
        })

        if args.checkout:
            project.sources.pull(name)
    elif args.source_type == RemoteTypes.local.name:
        url = osp.abspath(args.url)
        if not osp.exists(url):
            raise CliException("Source path '%s' does not exist" % url)

        name = args.name
        if name is None:
            name = osp.splitext(osp.basename(url))[0]

        if name in project.sources:
            raise CliException("Source '%s' already exists" % name)

        rel_local_dir = project.local_source_dir(name)
        local_dir = osp.join(project.config.project_dir, rel_local_dir)

        if args.copy:
            log.info("Copying from '%s' to '%s'" % (url, local_dir))
            if osp.isdir(url):
                # copytree requires destination dir not to exist
                shutil.copytree(url, local_dir)
                url = rel_local_dir
            elif osp.isfile(url):
                os.makedirs(local_dir)
                shutil.copy2(url, local_dir)
                url = osp.join(rel_local_dir, osp.basename(url))
            else:
                raise Exception("Expected file or directory")
        else:
            os.makedirs(local_dir)

    project.add_source(name, { 'url': url, 'format': args.format })

    if not args.skip_check:
        log.info("Checking the source...")
        try:
            project.make_source_project(name).make_dataset()
        except Exception:
            shutil.rmtree(local_dir, ignore_errors=True)
            raise

    project.save()

    log.info("Source '%s' has been added to the project, location: '%s'" \
        % (name, rel_local_dir))

    return 0

def build_remove_parser(parser_ctor=argparse.ArgumentParser):
    parser = parser_ctor(help="Remove source from project",
        description="Remove a source from a project.")

    parser.add_argument('-n', '--name', required=True,
        help="Name of the source to be removed")
    parser.add_argument('--force', action='store_true',
        help="Ignore possible errors during removal")
    parser.add_argument('--keep-data', action='store_true',
        help="Do not remove source data")
    parser.add_argument('-p', '--project', dest='project_dir', default='.',
        help="Directory of the project to operate on (default: current dir)")
    parser.set_defaults(command=remove_command)

    return parser

def remove_command(args):
    project = load_project(args.project_dir)

    name = args.name
    if not name:
        raise CliException("Expected source name")
    try:
        project.get_source(name)
    except KeyError:
        if not args.force:
            raise CliException("Source '%s' does not exist" % name)

    if project.env.git.has_submodule(name):
        if args.force:
            log.warning("Forcefully removing the '%s' source..." % name)

        project.env.git.remove_submodule(name, force=args.force)

    source_dir = osp.join(project.config.project_dir,
        project.local_source_dir(name))
    project.remove_source(name)
    project.save()

    if not args.keep_data:
        shutil.rmtree(source_dir, ignore_errors=True)

    log.info("Source '%s' has been removed from the project" % name)

    return 0

def build_info_parser(parser_ctor=argparse.ArgumentParser):
    parser = parser_ctor()

    parser.add_argument('-n', '--name',
        help="Source name")
    parser.add_argument('-v', '--verbose', action='store_true',
        help="Show details")
    parser.add_argument('-p', '--project', dest='project_dir', default='.',
        help="Directory of the project to operate on (default: current dir)")
    parser.set_defaults(command=info_command)

    return parser

def info_command(args):
    project = load_project(args.project_dir)

    if args.name:
        source = project.get_source(args.name)
        print(source)
    else:
        for name, conf in project.config.sources.items():
            print(name)
            if args.verbose:
                print(dict(conf))

def build_parser(parser_ctor=argparse.ArgumentParser):
    parser = parser_ctor(description="""
            Manipulate data sources inside of a project.|n
            |n
            A data source is a source of data for a project.
            The project combines multiple data sources into one dataset.
            The role of a data source is to provide dataset items - images
            and/or annotations.|n
            |n
            By default, the project to be operated on is searched for
            in the current directory. An additional '-p' argument can be
            passed to specify project location.
        """,
        formatter_class=MultilineFormatter)

    subparsers = parser.add_subparsers()
    add_subparser(subparsers, 'add', build_add_parser)
    add_subparser(subparsers, 'remove', build_remove_parser)
    add_subparser(subparsers, 'info', build_info_parser)

    return parser
