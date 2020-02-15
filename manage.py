import argparse
import sys
import os
import fabric
import random
import json
import io
import yaml
import shutil
import subprocess
from github import Github

import validators
from invoke import UnexpectedExit

from configparser import ConfigParser

LOC_INSTALLER = {
    'python3.6': {
        'installer': 'pip',
        'filename': 'requirements.txt',
        'packages': 'ipython pip'
    },
    'nodejs': {
        'installer': 'npm',
        'filename': 'package.json',
        'packages': 'ipython pip'
    }
}


# from sqlalchemy.orm import sessionmaker
# from sqlalchemy import create_engine

# export LOC_CONTAINERS=/Users/$(whoami)/Documents/lmokto/containers
# LOC_CONTAINERS = os.environ.get('LOC_CONTAINERS')

# export LOC_REPOSITORIES=/Users/$(whoami)/Documents/lmokto/repositories
# LOC_REPOSITORIES = os.environ.get('LOC_REPOSITORIES')

# export LOC_PROFILES=/Users/$(whoami)/Documents/lmokto/profiles
# LOC_PROFILES = os.environ.get('LOC_PROFILES')

# export LOC_ENVIRONMENTS=/Users/$(whoami)/Documents/lmokto/environments
# LOC_CONTAINERS = os.environ.get('LOC_ENVIRONMENTS')

# export LOC_CONDA=/Users/$(whoami)/opt/anaconda3/bin/conda
# LOC_CONDA = os.environ.get('LOC_CONDA')

# export LOC_SETTINGS=<PATH>/settings.ini
# LOC_SETTINGS = os.environ.get('LOC_SETTINGS')

# https://ipython.readthedocs.io/en/stable/interactive/magics.html
# https://jupyter-client.readthedocs.io/en/stable/wrapperkernels.html
# https://virtualenvwrapper.readthedocs.io/en/latest/install.html#basic-installation
# https://github.com/yunabe/tslab


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Box(object):
    attrs = [
        'name', 'profile', 'environment', 'repository',
        'location', 'version', 'language'
    ]
    _id = random.randint(1000, 9999)

    def __init__(self, instance={}):
        super().__init__()
        if instance:
            self.assignment(instance)
        else:
            [setattr(self, k, '') for k in self.attrs if k]

    def retrieve(self):
        return {
            'sandbox': self.__dict__,
            '_id': self._id
        }

    def update(self, response):
        self.environment = response['environment']
        self.profile = response['profile']
        self.repository = response['repository']
        self.location = response['location']
        self.version = "1.0.0"

    def assignment(self, instance):
        sandbox = instance.get('sandbox', None)
        self._id = instance.get('_id', 0)
        if sandbox and self._id:
            for k in self.attrs:
                assert k in sandbox.keys()
                box_attr = sandbox.get(k)
                setattr(self, k, box_attr)
            return True
        raise ValueError('instance without id and sandbox')


class Sandboxes(Box):
    pass


class ManagerContext(object):

    def __init__(self, env):
        super().__init__()
        self.settings = self.get_settings(env)
        self.boxes = []

    def registry(self, box):
        ids = [_b['_id'] for _b in self.boxes if _b]
        if box['_id'] not in ids:
            self.boxes.append(box)
            return {'status': 'successful'}
        return {'status': 'failed'}

    def retrieve_sandboxes(self):
        retrieves = {
            'containers': []
        }
        loc_boxes = os.path.join(
            self.settings.contexts.location,
            self.settings.containers.boxes
        )
        boxes = os.listdir(loc_boxes)
        for box in boxes:
            name = box.replace('.json', '')
            sandbox = self.import_sandbox(name)
            retrieves['containers'].append(sandbox)
        return retrieves

    def import_sandbox(self, name):
        try:
            loc_boxes = os.path.join(
                self.settings.contexts.location,
                self.settings.containers.boxes
            )
            boxes = os.listdir(loc_boxes)
            box_name = name + '.json'
            if box_name in boxes:
                loc_sandbox = os.path.join(
                    loc_boxes,
                    box_name
                )
                sandbox = json.load(open(loc_sandbox, 'r'))
                return sandbox
            return {'status': 'failed'}
        except Exception as Error:
            raise Error

    def export_sandbox(self, box):
        try:
            box = self.get_sandbox('_id', box.get('_id'))
            loc_file = os.path.join(
                os.path.join(
                    self.settings.contexts.location,
                    self.settings.containers.boxes
                ),
                '{filename}.json'.format(
                    filename=box['sandbox']['name']
                )
            )
            with io.open(loc_file, 'w', encoding='utf8') as out:
                str_ = json.dumps(
                    box, indent=4, sort_keys=True,
                    separators=(',', ': '), ensure_ascii=False
                )
                out.write(str(str_))
            return {'status': 'successful'}
        except Exception as Error:
            return {'status': Error}

    def get_sandbox(self, attr, value):
        for box in self.boxes:
            sandbox = box['sandbox']
            if attr == '_id' and box['_id'] == value:
                return box
            elif sandbox[attr] == value:
                return box
        return {}

    def get_settings(self, env):
        try:
            settings = ConfigParser(dict_type=AttrDict)
            settings.read(env)
            if settings._sections:
                return settings._sections
            raise TypeError
        except TypeError:
            raise ValueError('settings was not found')


def get_language(lang):
    """
    :param lang:
    return {}
    """
    version = ''.join([s for s in lang if s.isnumeric() or s == '.'])
    language = ''.join([s for s in lang if s.isalpha()])
    return {
        'name': language,
        'version': version
    }


def generate_yml(name, language, packages=[], install={}):
    # https://github.com/conda/conda/blob/54e4a91d0da4d659a67e3097040764d3a2f6aa16/tests/conda_env/support/advanced-pip/environment.yml
    try:
        _lang = get_language(language)
        language = '{0}={1}'.format(_lang['name'], _lang['version'])
        installer = install.get('installer')
        requirements = os.path.join(
            install.get('dirname'),
            install.get('filename')
        )
        if os.path.isfile(requirements):
            file_install = '-r file:{filename}'.format(filename=requirements)
        else:
            file_install = 'ipython'
        dependencies = [language, installer, {installer: [file_install]}]
        dependencies.append(packages) if packages else None
        filename = os.path.join(
            LOC_ENVIRONMENTS,
            '{env}.yml'.format(env=name)
        )
        if not os.path.isfile(filename):
            with open(filename, 'w') as outfile:
                yaml.dump({
                    'name': name,
                    'dependencies': dependencies
                }, outfile, default_flow_style=False)
        return filename
    except Exception as Error:
        raise Error


def conda_sync(repository, args):
    """
    :param env:
    :param pyversion:
    :return: response
    """
    try:
        environment = repository['output']['repository']
        installer = {
            'dirname': repository['output']['export'],
            'filename': LOC_INSTALLER[args.language]['filename'],
            'installer': LOC_INSTALLER[args.language]['installer']
        }
        filename = generate_yml(
            environment, args.language, args.packages, installer
        )
        output = terminal.local(
            '{conda} env create -f {environment}'.format(
                conda=LOC_CONDA,  #  location of context
                environment=filename
            )
        )
        response = generate_response(output, {
            'environment': args.environment,
            'export': LOC_ENVIRONMENTS,
            'filename': filename
        })
        return response
    except UnexpectedExit as Error:
        raise Error


def conda_remove(name):
    try:
        output = terminal.local(
            '{conda} remove --name {environment} --all --yes'.format(
                conda=LOC_CONDA,  #  location of context
                environment=name
            )
        )
        response = generate_response(output, {'environment': name})
        return response
    except UnexpectedExit as Error:
        raise Error


def conda_build(name, language, packages):
    try:
        language = get_language(language)
        output = terminal.local(
            '{conda} create -yn {env} {language}={version} {packages} --no-default-packages'.format(
                conda=LOC_CONDA,  #  location of context
                env=name,  # name of environment
                language=language['name'],  #  name of language
                version=language['version'],  # version of language
                packages=packages  # packages to install by default
            )
        )
        response = generate_response(output, {
            'environment': name,
            'language': language,
            'packages': packages
        })
        return response
    except UnexpectedExit as Error:
        raise Error


def conda_export(name):
    """
    :param envname:
    :return: response
    """
    try:
        loc_export = os.path.join(
            manager.settings.contexts.location,
            LOC_ENVIRONMENTS
        )
        filename = '{loc}/{env}.yml'.format(
            env=name,  # name of environment
            loc=loc_export  # destiny for export the environment.yml
        )
        output = terminal.local(
            '{conda} env export -n {env} | grep -v "^prefix: " > {filename}'.format(
                conda=LOC_CONDA,  # path absolute the conda
                env=name,
                filename=filename  # export filename
            )
        )
        response = generate_response(output, {
            'environment': name,
            'export': loc_export,
            'filename': filename
        })
        return response
    except UnexpectedExit as Error:
        raise Error


def profile_build(name):
    """
    :param envname:
    :return: response
    """
    try:
        loc_export = os.path.join(
            manager.settings.contexts.location,
            manager.settings.profiles.location
        )
        iprofile = '[{name}]'.format(name=name)
        output = terminal.local(
            '{conda} run -n {env} ipython profile create {profile} --ipython-dir {export}'.format(
                conda=LOC_CONDA,  # path absolute the conda
                env=name,  # name of environment
                profile=iprofile,  # name of profile
                export=loc_export  # location for save profile
            )
        )
        response = generate_response(output, {
            'env': name,
            'profile': iprofile,
            'export': loc_export
        })
        return response
    except UnexpectedExit as Error:
        raise Error


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def start_repository(folder, start_git):
    """
    :param folder:
    :return: response
    """
    try:
        loc_folder = os.path.join(
            os.path.join(
                manager.settings.contexts.location,
                manager.settings.repositories.location
            ),
            folder
        )
        mkdir_resp = mkdir_folder(loc_folder)
        if start_git:
            output = terminal.local('cd {folder} && git init'.format(
                folder=loc_folder
            ))
        else:
            output = {'command': '', 'ok': True}
        response = generate_response(output, {
            'mkdir': mkdir_resp,
            'export': loc_folder
        })
        return response
    except UnexpectedExit as Error:
        raise Error


def git_create(name):
    try:
        git = Github(manager.settings.repositories.token)
        user = git.get_user()
        repo = user.create_repo(name)
        response = git_clone(repo.clone_url)
        response['output']['url'] = repo.clone_url
        return response
    except Exception as Error:
        return False


def git_clone(repository):
    """
    :param repository:
    :return: response
    """
    try:
        location = repository
        repository = repository.split('/')[-1].replace('.git', '')
        folder_path = os.path.join(
            LOC_REPOSITORIES,
            repository
        )
        if not os.path.isdir(folder_path):
            output = terminal.local(
                'git clone {url} {location}'.format(
                    url=location,
                    location=folder_path
                )
            )
            response = generate_response(output, {
                'url': repository,
                'repository': repository,
                'export': folder_path
            })
            return response
        return 'Existing repository'
    except UnexpectedExit as Error:
        raise Error


def mkdir_folder(name):
    """
    :param name:
    :return: response
    """
    try:
        if not os.path.isdir(name):
            output = terminal.local('mkdir {folder}'.format(folder=name))
            response = generate_response(output, {
                'export': name
            })
            return response
        return 'Existing folder'
    except UnexpectedExit as Error:
        raise Error


def generate_response(response, output):
    """
    :param response:
    :return dictionary
    """
    status, command = None, None

    if isinstance(response, dict):
        status = response.get('ok', None) 
        response.get('command', None)
    elif isinstance(response, object):
        status = getattr(response, 'ok', None)
        command = getattr(response, 'command', None)
    
    return {
        'status': 'successful' if status else 'failed',
        'command': command,
        'output': output
    }


def clean_response(response):
    """
    :param response:
    :return {}
    """
    location = response['repository']['output']['export']
    repository = response['repository']['output']['url']
    environment = os.path.join(
        response['environment']['output']['export'],
        response['environment']['output']['environment']
    )
    profile = os.path.join(
        response['profile']['output']['export'],
        'profile_{0}'.format(response['profile']['output']['profile'])
    )
    response = {
        'location': location,
        'environment': environment + '.yml',
        'profile': profile,
        'repository': repository
    }
    loc_contexts = manager.settings.contexts.location
    for k, v in response.items():
        response[k] = v.replace(loc_contexts + '/', '')
    return response


def languages(astring):
    """

    @type astring: object
    """
    _language = get_language(astring)
    if not _language['name'] in ['python', 'nodejs']:
        raise argparse.ArgumentTypeError('Language cannot soported')
    return astring


class Args:
    pass

def create_box(args, session=None):
    try:
        sandbox = Box()
        sandbox.name = args.name
        sandbox.language = args.language
        # 1. crear carpeta y repositorio inicial (git init <nombre repositorio>)
        starter = git_create(sandbox.name)
        # 2. crear environment con conda y exporta yml environments/conda (OK)
        build_env = conda_build(sandbox.name, sandbox.language, args.packages)
        export_env = conda_export(sandbox.name)
        # 3. crear profile en ipython en carpeta correspondiente (OK)
        build_profile = profile_build(sandbox.name)
        # 4. crear archivo <box>.json y guardarlo en carpeta containers/boxes (OK)
        response = clean_response({
            'repository': starter, 'environment': export_env, 'profile': build_profile
        })
        sandbox.update(response)
        # 5. Export metadata to json file in boxes folder
        box = sandbox.retrieve()
        response = manager.registry(box)
        manager.export_sandbox(box)
    except Exception as Error:
        raise (Error)


def remove_box(args, session=None):
    try:
        # search sandbox by name
        name = args.name
        box = manager.import_sandbox(name)
        # build a box
        sandbox = Box()
        # assigned attributes from sandbox to box
        sandbox.assignment(box)
        #  1. Remove conda environment
        response = conda_remove(sandbox.name)
        # 2. Remove <env>.json file in boxes
        os.remove(os.path.join(
            os.path.join(
                manager.settings.contexts.location,
                manager.settings.containers.boxes
            ),
            sandbox.name + '.json'
        ))
        # 3. Remove <env>.yml file in environments
        os.remove(os.path.join(
            manager.settings.contexts.location,
            sandbox.environment
        ))
        #  4. Remove profile__<[env]> folder in profiles/ipython
        shutil.rmtree(os.path.join(
            manager.settings.contexts.location,
            sandbox.profile
        ))
        #  5. Remove repositories/<folder>
        shutil.rmtree(os.path.join(
            manager.settings.contexts.location,
            sandbox.location
        ))
    except Exception as Error:
        raise Error


def setup_container(args=None, session=None):
    """
    :param args:
    :param session:
    :return:
    """
    try:
        git_clone(manager.settings.profiles.repository)
        git_clone(manager.settings.environments.repository)
        mkdir_folder(manager.settings.repositories.location)
    except Exception as Error:
        raise (Error)


def sync_box(args, session=None):
    try:
        if args.name and not args.repository and not args.environment:
            # Instanciamos sandbox
            instance = True
            sandboxes = manager.retrieve_sandboxes()
            box = [ box for box in sandboxes['containers'] if box['sandbox']['name'].lower() == args.name.lower() ]
            sandbox = Box(instance=box.pop())
        elif not args.name and args.repository and args.environment:
            # Creamos sandbox
            instance = False
            sandbox = Box()
            sandbox.name = args.environment
            sandbox.language = args.language
            sandbox.repository = args.repository
        # 1 clonamos repositorio
        clone = git_clone(sandbox.repository)
        # 2. crear environment con conda y exporta yml environments/conda (OK)
        sync_env = conda_sync(clone, args)
        # 3. crear profile en ipython en carpeta correspondiente (OK)
        build_profile = profile_build(sandbox.name)
        # 4. crear archivo <box>.json y guardarlo en carpeta containers/boxes (OK)
        if not instance:
            response = clean_response({
                'repository': clone, 'environment': sync_env, 'profile': build_profile
            })
            sandbox.update(response)
            # 5. Export metadata to json file in boxes folder
            box = sandbox.retrieve()
            response = manager.registry(box)
            status = manager.export_sandbox(box)
            print(status)
    except Exception as Error:
        raise Error


def run_subprocess(sandbox):
    response = subprocess.run("""
        osascript -e 'tell app "Terminal"' -e 'do script "cd {repositories} && conda activate {environment} && ipython --profile=[{profile}] --ipython-dir={loc_profiles}"' -e 'end tell'
    """.format(
        repositories=os.path.join(
            manager.settings.contexts.location,
            sandbox.location
        ),
        environment=sandbox.name,
        profile=sandbox.name,
        loc_profiles=os.path.join(
            manager.settings.contexts.location,
            manager.settings.profiles.location
        )
    ), shell=True)
    return response


def starter_box(args, session=None):
    try:
        name = args.name
        box = manager.import_sandbox(name)
        # build a box
        sandbox = Box()
        # assigned attributes from sandbox to box
        sandbox.assignment(box)
        # start sandbox
        response = run_subprocess(sandbox)
    except Exception as Error:
        raise Error


def retrieve_sandboxes(args=None, session=None):
    try:
        sandboxes = manager.retrieve_sandboxes()
        if args.name:
            sandbox = [
                c['sandbox'] for c in sandboxes['containers'] if c['sandbox']['name'] == args.name
            ]
            print(json.dumps(sandbox, indent=4, sort_keys=True))
        else:
            print(json.dumps(sandboxes, indent=4, sort_keys=True))
    except Exception as Error:
        raise Error


def get_containers():
    sandboxes = manager.retrieve_sandboxes()
    containers = [ c['sandbox']['name'] for c in sandboxes['containers'] if c ]
    return containers


def verify_available_sandbox(name):
    containers = get_containers()
    if name in containers:
        raise argparse.ArgumentTypeError(
            'The Container it was created, please introduce a new name.'
        )
    return name


def verify_name_sandbox(name):
    containers = get_containers()
    if name in containers:
        return name
    else:
        raise argparse.ArgumentTypeError(
            'The container it was not created, please introduce the correct name.'
        )


def verify_url(direction):
    response = validators.url(direction)
    if not response:
        raise argparse.ArgumentTypeError('The URL provided was not correct.')
    return direction


#  engine = create_engine(
#      manager.settings.contexts.connection,
#      echo=bool(manager.settings.contexts.echo)
#  )
#  Session = sessionmaker(bind=engine)
#  session = Session()

LOC_SETTINGS = '/Users/lurangar/Documents/lmokto/containers/settings.ini'
LOC_CONDA = '/Library/anaconda3/condabin/conda'

manager = ManagerContext(LOC_SETTINGS)
terminal = fabric.Connection(manager.settings.contexts.pipeline)

LOC_CONTEXT = manager.settings.contexts.location

LOC_CONTAINERS = os.path.join(
    LOC_CONTEXT,
    manager.settings.containers.location
)

LOC_REPOSITORIES = os.path.join(
    LOC_CONTEXT,
    manager.settings.repositories.location
)

LOC_PROFILES = os.path.join(
    LOC_CONTEXT,
    manager.settings.profiles.location
)

LOC_ENVIRONMENTS = os.path.join(
    LOC_CONTEXT,
    manager.settings.environments.location
)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

# 1.1 python manage.py starter_container
parser_active = subparsers.add_parser('setup', help='start container context')
parser_active.set_defaults(func=setup_container)

# 2.1 python manage.py create --name='test' --language='python3.6' --packages='ipython pip'
parser_registry = subparsers.add_parser('create', help='')
parser_registry.add_argument('-n', '--name', required=True, type=verify_available_sandbox, help='')
parser_registry.add_argument('-l', '--language', type=languages, required=True, help='')
parser_registry.add_argument('-g', '--git', required=False, type=str2bool, default=True, help='')
parser_registry.add_argument('-p', '--packages', required=False, help='', default='ipython pip')
parser_registry.set_defaults(func=create_box)

# 3.1 python manage.py remove --name=microdevices
parser_registry = subparsers.add_parser('remove', help='')
parser_registry.add_argument('-n', '--name', type=verify_name_sandbox, required=True, help='')
parser_registry.set_defaults(func=remove_box)

# 4.1 python manage.py sync --repository=https://github.com/lmokto/microdevices.git --environment=microdevices --language=python3.6
# 4.2 python manage.py sync --name=will --language=python3.6
# 4.3 python manage.py sync --repository=https://github.com/lmokto/microdevices.git --language=python3.6
parser_registry = subparsers.add_parser('sync', help='')
parser_registry.add_argument('-n', '--name', type=verify_name_sandbox, required=False, help='')
parser_registry.add_argument('-r', '--repository', type=verify_url, required=False, help='')
parser_registry.add_argument('-e', '--environment', type=verify_available_sandbox, required=False, help='')
parser_registry.add_argument('-l', '--language', type=languages, required=False, help='')
parser_registry.add_argument('-p', '--packages', required=False, help='')
parser_registry.set_defaults(func=sync_box)

# 5.1 python manage.py starter --name='test'
parser_registry = subparsers.add_parser('starter', help='')
parser_registry.add_argument('-n', '--name', type=verify_name_sandbox, required=True, help='')
parser_registry.set_defaults(func=starter_box)

# 6.1 python manage.py retrieve
# 6.2 python manage.py retrieve --name=will
parser_registry = subparsers.add_parser('retrieve', help='')
parser_registry.add_argument('-n', '--name', type=verify_name_sandbox, required=False, help='')
parser_registry.set_defaults(func=retrieve_sandboxes)


if len(sys.argv) <= 1:
    sys.argv.append('--help')

options = parser.parse_args()
options.func(options, session=None)
