import os

import constructs
import yaml
from importlib import resources

from constructs import Construct
from multipledispatch import dispatch
from aws_cdk import (
    Tags,
    aws_ecs as ecs
)

def get_base_directory() -> str:
    BASEDIR = os.path.dirname(os.path.abspath(__file__))
    last_index = BASEDIR.rfind('/')

    # If '/' is found, trim the string
    if last_index != -1:
        trimmed_path = BASEDIR[:last_index]
        return trimmed_path
    else:
        # If '/' is not found, return the original path
        return BASEDIR

# read env variable if it's set, set nill otherwise
@dispatch(str)
def env_variable(name):
    if name in os.environ:
        return os.environ[name]
    else:
        return None

CONFIG_FILE = env_variable('CONFIG_FILE')

# load config file
@dispatch()
def load_config():
    if CONFIG_FILE is None:
        config_file = "config"  # default config file
    else:
        config_file = CONFIG_FILE
    with resources.open_text(f"configs", f"{config_file}.yml") as file:
        return yaml.safe_load(file)


# add tags to a construct given a list of tags
# @dispatch(object, object)
def add_standard_tags(construct, tags=None):
    config = load_config()
    if tags is None:
        tags = config["tags"]
    for tag in tags:
        Tags.of(construct).add(tag["key"], tag["value"])


# get rails master key from file
@dispatch(str)
def get_rails_key_from_env(env):
    root_dir = os.path.dirname(os.path.abspath(os.curdir))
    with open(os.path.join(root_dir, f"rails-api/config/credentials/{env}.key")) as file:
        return file.read()


def strict_env(string, capitalize=False):
    string.lower()
    strict_string = string[:3] if string == "development" else string[:4]
    return strict_string.capitalize() if capitalize else strict_string

def merge_dicts(*dicts: list[dict]) -> dict:
    z = {}
    for d in dicts:
        x = d.copy()
        z.update(x)

    return z