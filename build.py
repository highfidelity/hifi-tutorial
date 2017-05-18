#!/usr/bin/env python

#  assets/
#      tutorial/...    // tutorial scripts, same path as it is now on assets server
#       ...              // other assets
#  entities/
#      models.json
#  domain-server/
#      config.json
#  build/
#      assignment-client/
#          assets/
#              map.json
#              files/
#                  ...
#          entities/
#              models.json.gz
#      domain-server/
#          config.json

import os
import json
import hashlib
import gzip
import shutil
import tarfile


def create_assets_map(file_path_pairs):
    assets_map = {}
    for filename, path, filehash in file_path_pairs:
        path_parts = split(path)
        assets_path = '/' + '/'.join(path_parts)
        assets_map[assets_path] = filehash
    return assets_map


def visit(root, dirs, files):
    print('> ', root)


def split(path):
    head, tail = os.path.split(path)
    if tail == '':
        if head == '':
            return []
        else:
            return [head]
    return split(head) + [tail]


def makedirs(path):
    try:
        os.makedirs(path)
        return True
    except FileExistsError:
        return False



def generate_build(source_dir, output_dir, version=None):
    print("# Generating release")

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

    # Generate assets map
    print("\tWriting assets")
    assets_files = []
    print("\t\tSource assets directory is: " + src_assets_dir)
    print("\t\tCopying assets to output directory")
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
            print("\t\t\tCopying {} to {}".format(abs_filepath, output_filepath))
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

    print("\tWriting content version")
    output_version_filepath = os.path.join(output_ac_dir, 'content-version.txt')
    if version is None:
        print("\t\tSkipping, version not specified")
    else:
        print("\t\tWriting version {}".format(version))
        with open(output_version_filepath, 'w') as f:
            f.write(str(version))

    print("\tComplete")


RELEASE_PATHS = (
        #'assignment-client/assets/files',
        'assignment-client/assets/map.json',
        'assignment-client/entities/models.json.gz',
        'domain-server/config.json',
        )
def generate_release(source_dir, output_filepath):
    print("# Generating release")

    if not output_filepath.endswith('.tar.gz'):
        print('\tSkipping, output must end in "tar.gz": {}'.format(output_filepath))
    else:
        def tarfilter(tarinfo):
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = 'hifi'

        print("\tWriting archive to {}".format(output_filepath))
        with tarfile.open(output_filepath, 'w:gz') as f:
            for path in RELEASE_PATHS:
                full_path = os.path.join(source_dir, path)
                print("\t\tAdding to archive: {}".format(full_path))
                f.add(full_path, filter=tarfilter)

    print("\tComplete")


if __name__ == '__main__':
    root_dir = os.getcwd()
    source_dir = root_dir
    output_dir = os.path.join(root_dir, 'build')
    generate_build(source_dir, output_dir, 35)
    archive_path = os.path.join(root_dir, 'home-content-{}.tar.gz'.format(35))
    generate_release(output_dir, archive_path)
