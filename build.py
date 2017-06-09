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

Example usage:

    Generate build into default ac/ds directory. This is useful when
    ./build.py sync -o ~/AppData/Roaming/High\ Fidelity

"""

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tarfile
import subprocess


def create_assets_map(file_path_pairs):
    print("{} file path pairs".format(len(file_path_pairs)))
    assets_map = {}
    for filename, path, filehash in file_path_pairs:
        path_parts = split(path)
        assets_path = '/' + '/'.join(path_parts)
        if assets_path in assets_map:
            if assets_map[assets_path] == filehash:
                print("**** Found duplicate: {}".format(assets_path), flush=True)
            else:
                print("**** Overwriting: {}".format(assets_path), flush=True)
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

def basename_without_extension(filepath):
    basename = os.path.basename(filepath)
    dotpos = basename.find('.')
    if dotpos > -1:
        return basename[:dotpos]
    return basename


def bake_file(input_filepath, output_directory, bake_texture):
    """
    Bake a file and return a list of info about each generated files. If the input file
    can't be baked or the bake fails, None will be returned.

    The file info dict will contain:
      
      relative_path - relative path to the file. This will generally have a depth
                      of 0 (example: 'sphere.fbx')
      absolute_path - absolute path to the file

    """
    dotpos = input_filepath.rfind('.')
    if dotpos == -1:
        extension = None
    else:
        extension = input_filepath[dotpos + 1:]

    print("Extension", extension)
    is_texture = extension in ('jpg', 'png', 'tga')
    if extension == 'fbx' or (bake_texture and is_texture):
        print("Baking ", input_filepath, output_directory, flush=True)
        FNULL = open(os.devnull, 'w')
        if is_texture:
            output_directory = os.path.join(output_directory, basename_without_extension(input_filepath))
            makedirs(output_directory)
        print('output', output_directory)
        res = subprocess.call(
                ['../hifi/build12/tools/oven/RelWithDebInfo/oven.exe',
                 '-i', input_filepath, '-o', output_directory])#, #stdout=FNULL, stderr=subprocess.STDOUT)
        if res == 0:
            print("Successfully baked", input_filepath, flush=True)
            input_filename = os.path.basename(input_filepath)
            pos = input_filename.rfind('.')
            if pos > -1:
                input_filename_no_ext = input_filename[:pos]
            else:
                input_filename_no_ext = input_filename

            baked_file_info = []

            # If input_filepath is something.fbx, output folder will be
            #   output_filepath/something/baked/
            baked_directory = os.path.join(output_directory, input_filename_no_ext, 'baked')
            #print("Baked directory", baked_directory, flush=True)
            for dirpath, _dirs, baked_files in os.walk(baked_directory):
                relpath = os.path.relpath(dirpath, baked_directory)
                for baked_file in baked_files:
                    rel_baked_file = os.path.normpath(os.path.join(relpath, baked_file))
                    baked_file_info.append({
                        'relative_path': rel_baked_file,
                        'absolute_path': os.path.join(os.getcwd(), dirpath, baked_file)
                    })

            return baked_file_info

    return None


def generate_build(source_dir, output_dir, bake=False, version=None):
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

    temp_dir = os.path.join(os.getcwd(), '___temp___')
    temp_dir = '___temp___'
    makedirs(temp_dir)

    makedirs(output_assets_dir)
    makedirs(output_assets_files_dir)
    makedirs(output_entities_dir)
    makedirs(output_ds_dir)

    # Generate models.json.gz if it doesn't exist
    print("\tWriting entities")
    models_filepath = os.path.join(src_entities_dir, 'models.json')
    output_models_filepath = os.path.join(output_entities_dir, 'models.json.gz')
    if os.path.exists(output_models_filepath):
        print("\t\tmodels.json.gz in build directory already exists, "
              + "not overwriting")
        response = input("\t\tDo you want to copy the build models.json.gz to your source models.json? [Y/n] ")
        if response == 'Y':
            print("\t\tCopying build models.json.gz to src models.json")
            with open(models_filepath, 'wb') as orig_file, \
                    gzip.open(output_models_filepath, 'rb') as gz_file:
                shutil.copyfileobj(gz_file, orig_file)
    else:
        print("\t\tCreating models.json.gz")
        with open(models_filepath, 'rb') as orig_file, \
                gzip.open(output_models_filepath, 'wb') as gz_file:
            shutil.copyfileobj(orig_file, gz_file)

    # Find zone entities to determine which files are used as a skybox
    skybox_asset_files = []
    with open(models_filepath, 'r') as models_file:
        try:
            entities = json.load(models_file)
            for entity in entities['Entities']:
                if entity['type'] == 'Zone':
                    url = entity.get('skybox', {}).get('url', None)
                    if url is not None and url.startswith('atp:/'):
                            skybox_asset_files.append(url[len('atp:/'):])
        except:
            print("ERROR: Failed to load models file")
            raise
            sys.exit(1)

    print("Found skyboxes: ", ', '.join(skybox_asset_files))


    # Build asset server files
    print("\tWriting assets", flush=True)
    print("\t\tSource assets directory is: " + src_assets_dir)
    print("\t\tCopying assets to output directory")
    assets_files = []

    skyboxes_to_update = []

    for dirpath, _dirs, files in os.walk(os.path.join(src_assets_dir)):
    #for dirpath, _dirs, files in os.walk(os.path.join(src_assets_dir, 'firepit')):
        #prefix = '  ' * len(split(os.path.relpath(dirpath, src_assets_dir)))
        #print(prefix + os.path.relpath(dirpath, src_assets_dir) + '\\')
        for filename in files:
            abs_filepath = os.path.abspath(os.path.join(dirpath, filename))
            asset_dir = os.path.relpath(os.path.abspath(dirpath), src_assets_dir)
            asset_dir = os.path.relpath(os.path.abspath(dirpath), src_assets_dir)
            asset_path = os.path.normpath(os.path.join(asset_dir, filename)).replace('\\', '/')
            #print('asset path', asset_path)
            #print("Asset dir", asset_dir)

            asset_files_to_copy = []

            needs_copy = True
            if bake:
                is_texture = extension in ('jpg', 'png', 'tga')
                is_skybox_texture = (is_texture and asset_path in skybox_asset_files)
                if extension == 'fbx' or is_skybox_texture:
                    baked_files = bake_file(abs_filepath, temp_dir, asset_path in skybox_asset_files)
                    if baked_files is not None:
                        for baked_file_info in baked_files:
                            needs_copy = False
                            #print(baked_file_info)
                            rel_path = baked_file_info['relative_path']
                            abs_path = baked_file_info['absolute_path']
                            #print('got baked file: ', rel_path, abs_path)
                            #filename = os.path.basename(abs_path)

                            pos = rel_path.rfind('.baked.')
                            if pos > -1:
                                asset_path = rel_path[:pos] + rel_path[pos + len('.baked'):]
                            else:
                                asset_path = rel_path #os.path.join(asset_dir, filename)

                            with open(abs_path, 'rb') as f:
                                sha256 = hashlib.sha256()
                                for chunk in iter(lambda: f.read(4096), b''):
                                    sha256.update(chunk)
                                filehash = sha256.hexdigest()

                            asset_path = os.path.normpath(os.path.join(asset_dir, asset_path))

                            asset_files_to_copy.append( (filehash, abs_path, asset_path) )

                            #if is_skybox_texture:
                                #skyboxes_to_update.append(('atp:' + ))

                        else:
                            print("ERROR baking:", abs_filepath)

            if needs_copy:
                asset_path = os.path.normpath(os.path.join(asset_dir, filename))
                #print("Not baked: ", filename, abs_filepath, asset_path, asset_dir, filename)
                with open(abs_filepath, 'rb') as f:
                    filehash = hashlib.sha256(f.read()).hexdigest()
                asset_files_to_copy.append( (filehash, abs_filepath, asset_path) )

            for filehash, source_filepath, asset_path in asset_files_to_copy:
                assets_files.append((source_filepath, asset_path, filehash))
                output_filepath = os.path.join(output_assets_files_dir, filehash)
                #print("\t\t\tCopying {} to {}".format(source_filepath, output_filepath))
                shutil.copy(source_filepath, output_filepath)

    print("\t\tCopied {} assets".format(len(assets_files)))

    assets_map = create_assets_map(assets_files)

    output_assets_map_file = os.path.join(output_assets_dir, 'map.json')
    with open(output_assets_map_file, 'w') as map_file:
        json.dump(assets_map, map_file, indent=4)

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
    source_dir = args.input_directory
    output_dir = args.output_directory

    print("Generating build in `{}` from `{}`".format(output_dir, source_dir))

    generate_build(source_dir, output_dir, args.bake, 35)


def handle_generate_package(args):
    archive_path = os.path.join(os.getcwd(), args.output_filename)
    generate_package(args.input_directory, archive_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=\
    """
    Content set generator and packager.
    """.format(cmd=sys.argv[0]))

    subparsers = parser.add_subparsers()

    parser_gen_build = subparsers.add_parser('sync', help='Synchronize src\
            directory with build directory')
    parser_gen_build.set_defaults(func=handle_generate_build)
    parser_gen_build.add_argument('-i', '--input_directory', default='src',
        help='Directory to pull data from')
    parser_gen_build.add_argument('-o', '--output_directory', default='build')
    parser_gen_build.add_argument('--bake', action='store_true')

    parser_package = subparsers.add_parser('package', help='Generate release package')
    parser_package.set_defaults(func=handle_generate_package)
    parser_package.add_argument('input_directory')
    parser_package.add_argument('output_filename')

    args = parser.parse_args(sys.argv[1:])
    if 'func' in args:
        args.func(args) 
    else:
        parser.print_help()
