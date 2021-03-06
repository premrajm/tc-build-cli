import configparser

import click
import requests

from tc.configtypes import *
from tc.error import *

build_config = BuildConfig()
auth_config = AuthConfig()


@click.group()
def main():
    pass


@main.command()
def status():
    """get the build related info from team city server"""
    try:
        build_status = _build_status()
        click.echo(build_status)
    except BuildConfigNotFoundException:
        click.echo('Build config missing. Create with "config --init" command')
    except AuthNotFoundException as e:
        click.echo('Login config missing. Create with "login --server {0}" command'.format(str(e)))
    except RequestFailedException as e:
        click.echo('Request to team city server failed, returned error is - {0}'.format(str(e)))


@main.command()
@click.option('--server', prompt='Team city Server', help='team city server host name without port (e.g. localhost)')
@click.option('--username', prompt='Username', help='team city username')
@click.option('--password', prompt='Password', help='team city password', hide_input=True)
def login(server, username, password):
    """configure login credentials for tc server"""
    config_parser = configparser.ConfigParser()
    config_parser.add_section(auth_config.auth)
    config_parser.set(auth_config.auth, auth_config.auth_user, username)
    config_parser.set(auth_config.auth, auth_config.auth_pass, password)
    _write_config(auth_config.config_file.format(server), config_parser)


@main.command()
@click.option('--init', is_flag=True, help='create/overwrite config file')
def config(init):
    """configure or print build configuration"""
    if init:
        _create_build_configuration()
    else:
        _print_build_configuration()


def _print_build_configuration():
    try:
        server, build_type_id = _get_build_config()
        click.echo('Server = ' + server)
        click.echo('Build type id = ' + build_type_id)
    except BuildConfigNotFoundException:
        click.echo('No config exists. Create with --init flag')


def _create_build_configuration():
    config_parser = configparser.ConfigParser()
    config_parser.add_section(build_config.main)
    config_parser.set(build_config.main, build_config.main_server, click.prompt('Please enter server host:port'))
    config_parser.set(build_config.main, build_config.main_type_id, click.prompt('Please enter build type id'))
    _write_config(build_config.config_file, config_parser)


def _write_config(filename, config_parser):
    cfg_file = create_and_open(filename, 'w')
    config_parser.write(cfg_file)
    cfg_file.close()


def _get_config_parser(filename):
    config_parser = configparser.ConfigParser()
    file_read = config_parser.read(filename)
    if len(file_read) == 0:
        raise ConfigNotFoundException()
    return config_parser


def _get_build_config():
    try:
        config_parser = _get_config_parser(build_config.config_file)
        server = config_parser.get(build_config.main, build_config.main_server)
        build_type_id = config_parser.get(build_config.main, build_config.main_type_id)
        return server, build_type_id
    except ConfigNotFoundException:
        raise BuildConfigNotFoundException()


def _get_credentials(server):
    host = server.split(':')[0]
    try:
        config_parser = _get_config_parser(auth_config.config_file.format(host))
        username = config_parser.get(auth_config.auth, auth_config.auth_user)
        password = config_parser.get(auth_config.auth, auth_config.auth_pass)
        return username, password
    except ConfigNotFoundException:
        raise AuthNotFoundException(host)


def _build_status():
    server, build_type_id = _get_build_config()
    username, password = _get_credentials(server)
    build_url = 'http://{0}/httpAuth/app/rest/builds/buildType:{1}/status'.format(server, build_type_id)
    req = requests.get(build_url, auth=(username, password))
    if req.status_code is not 200:
        raise RequestFailedException(req.status_code)
    return req.text


def create_and_open(filename, mode):
    if "/" in filename:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
    return open(filename, mode)
