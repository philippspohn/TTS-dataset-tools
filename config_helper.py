import configparser
import os
from dearpygui.core import get_value

config = configparser.ConfigParser()
config.read("configdefaults.ini")
if os.path.exists("config.ini"):
    config.read("config.ini")

def save_current_settings():
    cfg_set("general", "project_name", get_value("input_project_name"))
    cfg_set("general", "cloud_storage_bucket", get_value("input_storage_bucket"))
    cfg_set("general", "google_cloud_credentials_file",  get_value("label_credentials_file_path"))
    cfg_set("general", "diarization_project_directory",  get_value("diarization_project_directory"))
    cfg_set("general", "datasetbuilder_project_directory",  get_value("datasetbuilder_project_directory"))
    cfg_set("general", "save_proofreader_on_exit",  str(get_value("save_proofreader_on_exit")))
    cfg_set("general", "transcribe_dataset", "1" if get_value("input_transcribe_dataset") else "0")

    cfg_set("transcription", "use_google_api", str(get_value("input_split")))
    cfg_set("transcription", "use_enhanced_video_model", str(get_value("input_use_videomodel")))
    cfg_set("transcription", "language_code", get_value("input_language_code"))
    cfg_set("transcription", "min_segment_length", get_value("input_min_seg_length"))
    cfg_set("transcription", "max_segment_length", get_value("input_max_seg_length"))
    cfg_set("transcription", "padding_start", str(get_value("input_padding_start")))
    cfg_set("transcription", "padding_end", str(get_value("input_padding_end")))

    cfg_set("youtube-dl", "output", get_value("ytdl_output_label"))
    cfg_set("youtube-dl", "build_dataset", "1" if get_value("ytdl_option_build_dataset") else "0")
    cfg_set("youtube-dl", "transcribe", "1" if get_value("ytdl_option_transcribe") else "0")
    cfg_set("youtube-dl", "merge", "1" if get_value("ytdl_option_merge") else "0")

def cfg_set(section, option, value):
    config.set(section, option, value)
    with open('config.ini', 'w') as f:
        config.write(f)


def cfg_get(section, option):
    return config.get(section, option)


def cfg_getint(section, option):
    return config.getint(section, option)


def cfg_getboolean(section, option):
    return config.getboolean(section, option)
