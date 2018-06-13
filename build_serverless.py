#!/usr/bin/env python
# This tool generates a serverless content set from the `src` directory:
#  * Bakes all models
#  * Remaps the following URLs in properties in models.json.gz file from `atp:/` to `file:///~/serverless/`:
#    * modelURL
#    * script
#    * textures (JSON value with references to textures)
#    * skybox (?)
#    * serverScripts

# TODO Output diagnostics about external references in scripts

from __future__ import print_function
import collections
import errno
import gzip
import json
import os
import shutil
import subprocess
import sys
import hashlib

if 'HIFI_OVEN' not in os.environ:
    print("ERROR: Environment variable `HIFI_OVEN` is not specified.")
    print("""
          The hifi `oven` is included with client+server installs of High Fidelity, and will be located in
          the root directory that you installed High Fidelity in. Example: C:\Program Files\High Fidelity\oven.exe
          """)
    sys.exit(1)

oven_path = os.environ['HIFI_OVEN']
verbose_logging = False

def log(prefix, *args):
    print(prefix, *args)
    sys.stdout.flush()

def debug(*args):
    if verbose_logging:
        log('[DEBUG]', *args)

def info(*args):
    log('[INFO]', *args)

def error(*args):
    log('[ERROR]', *args)


def makedirs(path):
    """
    Create directory `path`, including its parent directories if they do
    not already exist. Return True if the directory did not exist and was
    created, or False if it already existed.
    """
    try:
        os.makedirs(path)
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise

def get_extension(path):
    """Return the extension after the last '.' in a path. """
    idx = path.rfind('.')
    if idx >= 0:
        return path[idx + 1:]
    return ''

def remove_extension_from_filename(filename):
    idx = filename.find('.')
    if idx == -1:
        return filename
    return filename[:idx]

def pathresolve(root, path):
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(root, path))

class BakeException(Exception):
    pass

def bake_asset(abs_asset_path, baked_asset_output_dir, texture_type=None):
    makedirs(baked_asset_output_dir)
    ext = get_extension(abs_asset_path).lower()
    filetype = ''
    abs_baked_path = ''

    directory, filename = os.path.split(abs_asset_path)
    basename = remove_extension_from_filename(filename)
    baked_output_filename = ''

    extra_bake_args = []

    if ext == 'fbx':
        filetype = 'fbx'
        baked_output_filename = basename + '.baked.fbx'
    elif ext in ('png', 'jpg'):
        filetype = texture_type
        baked_output_filename = basename + '.texmeta.json'
    elif abs_asset_path.endswith('.texmeta.json'):
        with open(abs_asset_path) as f:
            original_path = json.load(f)['original']
            abs_asset_path = pathresolve(os.path.dirname(abs_asset_path), original_path)
        baked_output_filename = basename + '.texmeta.json'
        filetype = 'albedo'
    else:
        error("Unkown bake extension:", ext)
        return None

    with open(os.devnull, 'w') as devnull:
        if verbose_logging:
            devnull = None
        args = [oven_path,
                '-i', abs_asset_path,
                '-o', baked_asset_output_dir,
                '-t', filetype] + extra_bake_args
        debug('  Running oven: ' + ' '.join(args))
        returncode = subprocess.call(args, stdout=devnull, stderr=devnull)
        if returncode != 0:
            raise BakeException()

    return os.path.join(baked_asset_output_dir, baked_output_filename)

Asset = collections.namedtuple('Asset', [
    'filename',       # Original asset filename. Baked assets might have a different output filename
    'rel_dirpath',    # Relative path to asset dir, relative to `src/assets/`, starting with a `/`
    'atp_path',       # Path to asset, as it would appear on the asset server
    'input_abs_path', # Absolute path to file on file system
])

def joinpath(*args):
    return '/'.join((el for el in args if el != ''))

def canonicalize_url(url):
    idx = url.find('?')
    if idx >= 0:
        url = url[:idx]
    return url

def get_textures_requiring_baking_from_entity_data(entities):
    """
    Go through entities and pull out the referenced URLs that need to be baked, and the usage type
    that they need to be baked for. Returns the dictionary of values.
    """
    urls = {}
    for entity in entities['Entities']:
        for prop, value in entity.iteritems():
            if prop in ('ambientLight', 'skybox'):
                for url in value.itervalues():
                    urls[canonicalize_url(url)] = 'cube'
            elif prop == 'textures':
                try:
                    textures = json.loads(value)
                    for url in textures.itervalues():
                        urls[canonicalize_url(url)] = 'albedo'
                except ValueError:
                    urls[canonicalize_url(value)] = 'albedo'
    return urls

def build_serverless_tutorial_content(input_dir, output_dir):
    """
    Process the input directory domain content and generates a baked, serverless domain.

    The input directory is expected to contain:

       assets/...
       entities/models.json
       paths.json

    Textures will not be blindly baked because context is needed to know how it will be used (albedo, normals, etc.)
    Textures that are used by models will be baked when the model itself is baked.
    Other textures that will be baked:
      * Textures referenced in the `ambientLight` and `skybox` properties of an entity in
        models.json will be baked as `cube`.
      * Textures referenced in the `textures` property of an entity will be baked as `albedo`.
      * Textures referenced in *.texmeta.json files will be baked as `albedo`.

    """
    info("Building serverless tutorial content")
    info("  Input directory: " + input_dir)
    info("  Output directory: " + output_dir)

    assets_not_found = set()

    input_assets_dir = os.path.join(input_dir, 'assets')
    input_models_filepath = os.path.join(input_dir, 'entities', 'models.json')
    input_paths_filepath = os.path.join(input_dir, 'paths.json')
    output_models_filepath = os.path.join(output_dir, 'tutorial.json')

    entities = None
    with open(input_models_filepath, 'r') as models_file:
        try:
            entities = json.load(models_file)
        except:
            error("ERROR: Failed to load models file")
            raise

    textures_requiring_baking = get_textures_requiring_baking_from_entity_data(entities)

    # This is used to translate ATP references in the input models file to their final serverless URL
    # Ex: atp:/models/someFile.fbx => file:///~/serverless/baked/models/someFile.fbx/someFile.baked.fbx
    # Ex: atp:/script.js => file:///~/serverless/unbaked/scripts/script.js
    atp_path_to_output_path = {}

    # Collect list of all assets in the /src/assets dir.
    # For each asset, store:
    #   Filename                ("src/assets/models/pieces/bridge.fbx" would be "bridge.fbx")
    #   Relative directory path ("src/assets/models/pieces/bridge.fbx" would be "models/pieces")
    #   ATP Path                ("src/assets/models/pieces/bridge.fbx" would be "atp:/models/pieces/bridge.fbx")
    #   Absolute file path      ("src/assets/models/pieces/bridge.fbx" would be be expanded to the
    #                                                                  full absolute path on disk)
    assets = []
    for dirpath, _dirs, files in os.walk(input_assets_dir):
        for filename in files:
            asset_rel_dir = os.path.relpath(dirpath, input_assets_dir).replace('\\', '/')
            if asset_rel_dir == '.':
                asset_rel_dir = ''
            else:
                asset_rel_dir = asset_rel_dir

            abs_asset_path = os.path.normpath(
                    os.path.join(input_assets_dir, dirpath, filename))

            atp_path = '/'.join((el for el in ('atp:', asset_rel_dir, filename) if el != ''))

            assets.append(Asset(filename, asset_rel_dir, atp_path, abs_asset_path))


    # Process all assets. Bakeable assets will be baked and moved to the output directory, and the
    # rest will be copied over to the output directory.t
    BAKED_SUBDIRECTORY = 'baked'
    UNBAKED_SUBDIRECTORY = 'unbaked'
    for asset in assets:
        is_fbx = asset.filename.endswith('.fbx')
        is_texmeta = asset.filename.endswith('.texmeta.json')
        is_texture_requiring_baking = asset.atp_path in textures_requiring_baking
        should_copy = True
        if is_fbx or is_texture_requiring_baking or is_texmeta:
            texture_type = None
            if is_texture_requiring_baking:
                texture_type = textures_requiring_baking[asset.atp_path]
            info("Baking", '/' + joinpath(asset.rel_dirpath, asset.filename))
            baked_asset_output_dir = os.path.abspath(os.path.join(output_dir, BAKED_SUBDIRECTORY, asset.rel_dirpath, asset.filename))
            try:
                output_abs_path = bake_asset(asset.input_abs_path, baked_asset_output_dir, texture_type)
                debug("  Baked path is at:", output_abs_path)
                system_local_path = 'file:///~/serverless/' + os.path.relpath(output_abs_path, output_dir).replace('\\', '/')
                debug("  Baked: " + asset.atp_path + " => " + system_local_path)
                atp_path_to_output_path[asset.atp_path] = system_local_path
                if is_texmeta:
                    # If a script wants to reference "../textures/sky.texmeta.json", we want
                    # to make sure that file is still accessible in the output directory at the same
                    # relative location. To make that happen, we create a .texmeta.json that references
                    # the baked textures, and is at the same relative location to scripts in the
                    # unbaked subdirectory.
                    unbaked_texmeta_abs_dir = os.path.join(output_dir, UNBAKED_SUBDIRECTORY, asset.rel_dirpath)
                    unbaked_texmeta_abs_path = os.path.join(unbaked_texmeta_abs_dir, asset.filename)
                    debug("  Creating texmeta at original location for script use:", '/' + joinpath(asset.rel_dirpath, asset.filename))
                    makedirs(unbaked_texmeta_abs_dir)
                    with open(output_abs_path) as f:
                        data = json.load(f)
                        new_data = {}
                        def baked_relpath_to_unbaked_relpath(path):
                            abs_path = os.path.join(os.path.dirname(output_abs_path), path)
                            return os.path.relpath(abs_path, unbaked_texmeta_abs_dir).replace('\\', '/')
                        if data['original'] != '':
                            new_data['original'] = baked_relpath_to_unbaked_relpath(data['original'])
                        if data['uncompressed'] != '':
                            new_data['uncompressed'] = baked_relpath_to_unbaked_relpath(data['uncompressed'])
                        if data['compressed'] is not None:
                            new_data['compressed'] = {}
                            compressed = data['compressed']
                            for compression_type in compressed:
                                new_data['compressed'][compression_type] = baked_relpath_to_unbaked_relpath(compressed[compression_type])
                        with open(unbaked_texmeta_abs_path, 'w') as fw:
                            json.dump(new_data, fw)

                should_copy = False
            except BakeException:
                error("Error while baking: " + asset.input_abs_path)

        if should_copy:
            output_abs_dir = os.path.join(output_dir, UNBAKED_SUBDIRECTORY, asset.rel_dirpath)
            output_abs_path = os.path.join(output_abs_dir, asset.filename)
            info("Copying", '/' + joinpath(asset.rel_dirpath, asset.filename))
            debug("  Copying", asset.input_abs_path, 'to', output_abs_path)
            makedirs(output_abs_dir)
            shutil.copyfile(asset.input_abs_path, output_abs_path)
            system_local_path = joinpath('file:///~/serverless', UNBAKED_SUBDIRECTORY, asset.rel_dirpath, asset.filename)
            atp_path_to_output_path[asset.atp_path] = system_local_path

    def to_system_local_url(url):
        clean_url = canonicalize_url(url)
        if clean_url not in atp_path_to_output_path:
            if clean_url.endswith('.fst'):
                info("FST not found in local list of assets, but this is likely expected and OK: " + url)
            else:
                assets_not_found.add(url)
                error("Not found in local list of assets: " + url)
        else:
            return atp_path_to_output_path[clean_url]
        return url

    # Update URLs
    debug("Found " + str(len(entities['Entities'])) + " entities")
    for entity in entities['Entities']:
        for prop, value in entity.iteritems():
            if 'URL' in prop or prop in ('script', 'serverScripts'):
                entity[prop] = to_system_local_url(value)
            elif prop in ('ambientLight', 'skybox'):
                for key in value:
                    value[key] = to_system_local_url(value[key])
            elif prop == 'textures':
                try:
                    textures = json.loads(value)
                    for key in textures:
                        textures[key] = to_system_local_url(textures[key])
                    entity['textures'] = json.dumps(textures)
                except ValueError:
                    entity['textures'] = to_system_local_url(value)

    with open(input_paths_filepath, 'r') as paths_file:
        paths = json.load(paths_file)
        entities['Paths'] = paths['Paths']

    with open(output_models_filepath, 'w') as models_file:
        json.dump(entities, models_file, indent=4)

    if len(assets_not_found) > 0:
        info("Errors:")
        info("  {} Assets not found:".format(len(assets_not_found)))
        for url in assets_not_found:
            info("    " + url)
    else:
        info("Success: No errors building serverless tutorial")

def create_serverless_tutorial_archive(dirpath):
    info("Creating tutorial archive")
    archive_path = shutil.make_archive('tutorial', 'zip', dirpath)
    with open(archive_path, 'rb') as f:
        md5 = hashlib.md5()
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
        archive_hash = md5.hexdigest()
    shutil.move(archive_path, dirpath)
    archive_path = os.path.join(dirpath, os.path.basename(archive_path))

    print('''
    The serverless tutorial archive has succesfully been created at: {filename}

    What's next?

    Steps to deploy a new tutorial:

      1. Rename the archive ({filename}) to include a version (example: serverless-tutorial-RC68.zip)
      2. Upload the archive to the S3 hifi-production bucket, into the "content-sets" directory
      3. Update "cmake/externals/serverless-content/CMakeLists.txt" inside of the hifi repository:
        a. Update the filename in URL with the filename you chose in step 1.
        b. Update URL_MD5 to be "{archive_md5}" (this is the md5 hash of the archive)
        c. Commit and open a PR for these changes on GitHub
    '''.format(filename=archive_path, archive_md5=archive_hash))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " output_dir")
        sys.exit(1)

    input_dir = os.path.abspath('src')
    output_dir = os.path.abspath(sys.argv[1])
    if '--verbose' in sys.argv:
        verbose_logging = True

    if os.path.exists(output_dir) and len(os.listdir(output_dir)) != 0:
        print('Output directory ' + output_dir + ' exists and is not empty.')
        print('Please delete the directory first, or choose a different output directory.')
        sys.exit(1)

    build_serverless_tutorial_content(input_dir, output_dir)
    create_serverless_tutorial_archive(output_dir)
