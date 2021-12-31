import errno
import os.path
import time

from pydub import AudioSegment
from yt_dlp import YoutubeDL
from dearpygui.core import get_value

from dataset_builder import Dataset_builder


def download_videos(video_ids, output_directory):
    print("Downloading videos...")
    output_wavs = []
    for id in video_ids:
        output_path = os.path.join(output_directory, id, id + ".wav")
        output_wavs.append(output_path)
        with YoutubeDL({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav'
            }],
            'outtmpl': output_path
        }) as ydl:
            ydl.download(f'https://www.youtube.com/watch?v={id}')
            sound = AudioSegment.from_wav(output_path)
            sound = sound.set_channels(1)
            sound = sound.set_frame_rate(22050)
            sound.export(output_path, format="wav")
    return output_wavs


def build_dataset_from_video(video_ids, video_directory, transcribe):
    print("Building datasets from videos...")
    for index, id in enumerate(video_ids):
        print(f"Building dataset for video: {id} ({index + 1}/{len(video_ids)})")
        video_dataset_dir = os.path.join(video_directory, id)
        video_wav_file = os.path.join(video_dataset_dir, id + ".wav")

        if not os.path.exists(video_wav_file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), video_wav_file)

        old_wavs_dir = os.path.join(video_dataset_dir, "wavs")
        old_output_file = os.path.join(video_dataset_dir, "output.csv")
        if os.path.exists(old_wavs_dir):
            print("Warning: " + old_wavs_dir + " already exists. Creating backup...")
            old_path = old_wavs_dir + "-old-" + str(round(time.time() * 1000))
            os.rename(os.path.join(video_dataset_dir, "wavs"), old_path)
        if os.path.exists(old_output_file):
            print("Warning: " + old_output_file + " already exists. Creating backup...")
            old_path = os.path.join(os.path.dirname(old_output_file),
                                    os.path.basename(old_output_file) + "." + str(round(time.time() * 1000)) + ".old")
            os.rename(old_output_file, old_path)

        builder = Dataset_builder()
        builder.set_values(video_dataset_dir, None, video_wav_file, None, get_value("input_cut_length"), 0, False,
                           get_value("label_credentials_file_path"), transcription=transcribe)
        builder.build_dataset()
