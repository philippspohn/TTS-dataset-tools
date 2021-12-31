import tool_merge
from config_helper import *
from gui_helper import *
import re
from youtube_downloader import *


def add_elements():
    add_text("DOWNLOAD YOUTUBE VIDEOS AND GENERATE DATASET")
    add_spacing(count=5)
    add_button("ytdl_add_button", callback=on_add_button, label="Add video")
    add_same_line(spacing=10)
    add_input_text("ytdl_add_text", label="")
    add_spacing(count=3)
    add_table("ytdl_videos", ["Video IDs"], height=150,
              width=1000)
    add_spacing(count=5)
    add_button("ytdl_clear", callback=lambda: clear_table("ytdl_videos"), label="Clear table")
    add_same_line(spacing=10)
    add_label_text("ytdl_info", default_value="", label="")
    add_spacing(count=5)
    add_button("ytdl_output_button", callback=open_directory_dialogue_and_set_label("ytdl_output_label"),
               label="Output directory")
    add_same_line(spacing=10)
    add_label_text("ytdl_output_label", default_value=cfg_get("youtube-dl", "output"), label="")

    add_spacing(count=5)
    add_checkbox("ytdl_option_build_dataset", default_value=cfg_getboolean("youtube-dl", "build_dataset"),
                 callback=lambda: set_enabled(["ytdl_option_merge", "ytdl_option_transcribe"],
                                              enabled=get_value("ytdl_option_build_dataset")),
                 label="Build dataset")
    add_spacing(count=5)
    add_checkbox("ytdl_option_transcribe", default_value=cfg_getboolean("youtube-dl", "transcribe"),
                 label="Transcribe dataset")
    add_spacing(count=5)
    add_checkbox("ytdl_option_merge", default_value=cfg_getboolean("youtube-dl", "merge"), label="Merge dataset")
    add_spacing(count=5)
    add_button("ytdl_start", callback=on_download_button, label="Start downloading")

    add_spacing(count=10)
    add_drawing("ytdl_config_hline", width=800, height=1)
    draw_line("ytdl_config_hline", [0, 0], [800, 0], [255, 0, 0, 255], 1)
    add_spacing(count=5)
    add_button("save_current_settings_ytdl", callback=save_current_settings, label="Save config")


def set_enabled(elments, enabled):
    for e in elments:
        configure_item(e, enabled=enabled)


def on_add_button():
    vid = get_value("ytdl_add_text")
    set_value("ytdl_info", "")
    mAlphanum = re.match("^[\\w]{11}$", vid)
    mYtUrl = re.match("^(https://www\\.youtube\\.com/watch\\?v=|https://youtu\\.be/)([\\w]{11}).*$", vid)

    if mAlphanum:
        vid_id = vid
    elif mYtUrl:
        vid_id = mYtUrl[2]
    else:
        set_value("ytdl_info", "Not a valid youtube video :(")
        return
    set_value("ytdl_add_text", "")

    if not table_contains("ytdl_videos", 0, vid_id):
        add_row("ytdl_videos", [vid_id])


def on_download_button():
    output_dir = get_value("ytdl_output_label")

    # Download videos
    table_data = get_table_data("ytdl_videos")
    video_ids = [row[0] for row in table_data]
    download_videos(video_ids, output_dir)

    # Build dataset
    if not get_value("ytdl_option_build_dataset"):
        print("Done!")
        return

    build_dataset_from_video(video_ids, output_dir, get_value("ytdl_option_transcribe"))

    # Merge dataest
    if not get_value("ytdl_option_build_dataset"):
        print("Done!")
        return

    csv_files = [os.path.join(output_dir, id, "output.csv") for id in video_ids]
    merge_dir = os.path.join(output_dir, "merge-" + str(round(time.time_ns()) / 1000))
    tool_merge.merge_datasets(csv_files, merge_dir)
    # todo s: no transcript
