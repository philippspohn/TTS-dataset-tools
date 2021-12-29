import configparser
import os

config = configparser.ConfigParser()
config.read("configdefaults.ini")
if os.path.exists("config.ini"):
    config.read("config.ini")


def cfg_set(section, option, value=None):
    config.set(section, option, value)
    with open('config.ini', 'w') as f:
        config.write(f)


def cfg_get(section, option):
    return config.get(section, option)


def cfg_getint(section, option):
    return config.getint(section, option)


def cfg_getboolean(section, option):
    return config.getboolean(section, option)
