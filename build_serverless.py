#!/usr/bin/env python
# This tool generates a serverless content set from the `src` directory:
#  * Bakes all models
#  * Remaps the following URLs in properties in models.json.gz file from `atp:/` to `file:///~/serverless/`:
#    * modelURL
#    * script
#    * textures (JSON value with references to textures)
#    * skybox (?)
#    * serverScripts

# TODO Fix Script.resolvePath not properly resolving paths outside of the script directory
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
        if texture_type == 'cube':
            baked_output_filename = basename + '.ktx'
            extra_bake_args.append('--disable-texture-compression')
        else:
            baked_output_filename = basename + '.texmeta.json'
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
    urls = {
        'atp:/textures/advmove_Trigger_On.png': 'albedo'
    }
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
    
    # Ex: atp:/models/someFile.fbx => file:///~/baked/models/someFile.fbx/someFile.baked.fbx
    # Ex: atp:/script.js => file:///~/original/script.js
    atp_path_to_output_path = {}
    
    # Collect list of all assets and their abs path
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

    # Bake all assets
    for asset in assets:
        BAKED_SUBDIRECTORY = 'baked'
        UNBAKED_SUBDIRECTORY = 'unbaked'

        is_fbx = asset.filename.endswith('.fbx')
        is_texture_requiring_baking = asset.atp_path in textures_requiring_baking
        should_copy = True
        if is_fbx or is_texture_requiring_baking:
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
        json.dump(entities, models_file)

    print("\nErrors\n")
    if len(assets_not_found) > 0:
        print("  {} Assets not found:\n".format(len(assets_not_found)))
        for url in assets_not_found:
            print("    " + url)
    else:
        print("  No errors.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " output_dir")
        sys.exit(1)

    input_dir = os.path.abspath('src')
    output_dir = os.path.abspath(sys.argv[1])
    if '--verbose' in sys.argv:
        verbose_logging = True

    build_serverless_tutorial_content(input_dir, output_dir)
