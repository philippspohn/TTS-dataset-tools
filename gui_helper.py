from dearpygui.core import *
from config_helper import cfg_set
import os

def open_file_dialogue_and_set_label(label_name, save_to_config=False):
    return lambda: open_file_dialog(lambda sender, data: set_label(label_name, os.path.join(data[0], data[1]), save_to_config))


def open_directory_dialogue_and_set_label(label_name, save_to_config=False):
    return lambda: select_directory_dialog(lambda sender, data: set_label(label_name, os.path.join(data[0], data[1]), save_to_config))

def set_label(label_name, value, save_to_config):
    set_value(label_name, value)
    if save_to_config:
        cfg_set("general", label_name, value)

def table_contains(table_name, col, value):
    for row in get_table_data(table_name):
        if row[col] == value:
            return True
    return False