#!/usr/bin/env python
"""
This tool provides functionality to:

 * Generate a content set directory that the High Fidelity domain server
   and assignment clients can process.
 * Package the generated content set into a releasable archive that the High
   Fidelity Sandbox can download and use.

The tool expects the following directory structure:

  assets/           # ATP server assets
      ...
  entities/         # Entity server assets, models.json in unzipped form
      models.json
  domain-server/    # Domain server assets
      config.json

Building the content set will process the above directory structure and produce
a directory with a High Fidelity server compatible structures, which includes a
gzipped models file and a map.json for the assets server.

Build directory structure:

  build/
      assignment-client/
          assets/
              map.json
              files/
                  ...
          entities/
              models.json.gz
      domain-server/
          config.json

Packaging the build will generate a gzipped tarball that can be downloaded and
extracted by the Sandbox.

"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tarfile


def create_assets_map(file_path_pairs):
    assets_map = {}
    for filename, path, filehash in file_path_pairs:
        path_parts = split(path)
        assets_path = '/' + '/'.join(path_parts)
        if assets_path in assets_map:
            print("**** Overwriting {}".format(assets_path))
        assets_map[assets_path] = filehash
    return assets_map


def split(path):
    """
    Return a list containing the individual directories and filename (if
    included) in `path`. This is in contract to os.path.split, which will only
    split the path into 2 parts - the beginning and the last component.
    """
    head, tail = os.path.split(path)
    if tail == '':
        if head == '':
            return []
        else:
            return [head]
    return split(head) + [tail]


def makedirs(path):
    """
    Create directory `path`, including its parent directories if they do
    not already exist. Return True if the directory did not exist and was
    created, or False if it already existed.
    """
    try:
        os.makedirs(path)
        return True
    except FileExistsError:
        return False


def generate_build(source_dir, output_dir, version=None):
    """
    Generate a build by processing the directories and files in source_dir
    and outputting the build to build_dir. if a version is specified, it will
    be written to a file in the assignment-client directory.
    """
    src_assets_dir = os.path.join(source_dir, 'assets')
    src_entities_dir = os.path.join(source_dir, 'entities')
    src_ds_dir = os.path.join(source_dir, 'domain-server')

    output_ac_dir = os.path.join(output_dir, 'assignment-client')
    output_assets_dir = os.path.join(output_ac_dir, 'assets')
    output_assets_files_dir = os.path.join(output_assets_dir, 'files')
    output_entities_dir = os.path.join(output_ac_dir, 'entities')
    output_ds_dir = os.path.join(output_dir, 'domain-server')

    makedirs(output_assets_dir)
    makedirs(output_assets_files_dir)
    makedirs(output_entities_dir)
    makedirs(output_ds_dir)

    # Build asset server files
    print("\tWriting assets")
    print("\t\tSource assets directory is: " + src_assets_dir)
    print("\t\tCopying assets to output directory")
    assets_files = []
    for dirpath, dirs, files in os.walk(src_assets_dir):
        prefix = '  ' * len(split(os.path.relpath(dirpath, src_assets_dir)))
        #print(prefix + os.path.relpath(dirpath, src_assets_dir) + '\\')
        for filename in files:
            abs_filepath = os.path.join(dirpath, filename)
            rel_filepath = os.path.relpath(abs_filepath, src_assets_dir)
            with open(abs_filepath, 'rb') as f:
                filehash = hashlib.sha256(f.read()).hexdigest()
            assets_files.append((abs_filepath, rel_filepath, filehash))
            output_filepath = os.path.join(output_assets_files_dir, filehash)
            #print("\t\t\tCopying {} to {}".format(abs_filepath, output_filepath))
            shutil.copy(abs_filepath, output_filepath)
            #print(prefix + '  ' + rel_path)
    print("\t\tCopied {} assets".format(len(assets_files)))

    assets_map = create_assets_map(assets_files)

    output_assets_map_file = os.path.join(output_assets_dir, 'map.json')
    with open(output_assets_map_file, 'w') as map_file:
        json.dump(assets_map, map_file, indent=4)

    # Generate models.json.gz if it doesn't exist
    print("\tWriting entities")
    models_filepath = os.path.join(src_entities_dir, 'models.json')
    output_models_filepath = os.path.join(output_entities_dir, 'models.json.gz')
    if os.path.exists(output_models_filepath):
        print("\t\tmodels.json.gz in build directory already exists, "
              + "not overwriting")
    else:
        print("\t\tCreating models.json.gz")
        with open(models_filepath, 'rb') as orig_file, \
                gzip.open(output_models_filepath, 'wb') as gz_file:
            shutil.copyfileobj(orig_file, gz_file)

    # Copy domain-server config
    print("\tWriting domain-server config")
    src_ds_config_filepath= os.path.join(src_ds_dir, 'config.json')
    output_ds_config_filepath= os.path.join(output_ds_dir, 'config.json')

    shutil.copy(src_ds_config_filepath, output_ds_config_filepath)

    # Write content version
    print("\tWriting content version")
    if version is None:
        print("\t\tSkipping, version not specified")
    else:
        print("\t\tWriting version {}".format(version))
        output_version_filepath = os.path.join(output_ac_dir, 'content-version.txt')
        with open(output_version_filepath, 'w') as f:
            f.write(str(version))

    print("\tComplete")


PATHS_TO_INCLUDE_IN_ARCHIVE = (
        'assignment-client/assets/files',
        'assignment-client/assets/map.json',
        'assignment-client/entities/models.json.gz',
        'assignment-client/content-version.txt',
        'domain-server/config.json',
        )


def generate_package(input_dir, output_filepath):
    print("# Generating release")

    if not output_filepath.endswith('.tar.gz'):
        print('\tSkipping, output must end in "tar.gz": {}'.format(output_filepath))
    else:
        def tarfilter(tarinfo):
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = 'hifi'
            return tarinfo

        print("\tWriting archive to {}".format(output_filepath))
        with tarfile.open(output_filepath, 'w:gz') as f:
            for path in PATHS_TO_INCLUDE_IN_ARCHIVE:
                full_path = os.path.join(input_dir, path)
                print("\t\tAdding to archive: {}".format(full_path))
                f.add(full_path, path, filter=tarfilter)

    print("\tComplete")


def handle_generate_build(args):
    output_dir = args.output_directory
    #source_dir = os.getcwd()
    source_dir = args.input_directory

    print("Generating build in `{}` from `{}`".format(output_dir, source_dir))

    generate_build(source_dir, output_dir, 35)


def handle_generate_package(args):
    archive_path = os.path.join(os.getcwd(), args.output_filename)
    generate_package(args.input_directory, archive_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=\
    """
    Content set generator and packager.
    """.format(cmd=sys.argv[0]))

    subparsers = parser.add_subparsers()

    parser_gen_build = subparsers.add_parser('build', help='generate build')
    parser_gen_build.set_defaults(func=handle_generate_build)
    parser_gen_build.add_argument('input_directory')
    parser_gen_build.add_argument('output_directory', default='build', nargs='?')

    parser_package = subparsers.add_parser('package', help='generate release package')
    parser_package.set_defaults(func=handle_generate_package)
    parser_package.add_argument('input_directory')
    parser_package.add_argument('output_filename')

    args = parser.parse_args(sys.argv[1:])
    if 'func' in args:
        args.func(args) 
    else:
        parser.print_help()
