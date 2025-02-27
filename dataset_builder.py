import math
from pydub import AudioSegment, silence
from pydub.utils import mediainfo
from dearpygui.core import *
import os
import csv
import re
import shutil
from google.cloud import storage
from google.cloud import speech_v1p1beta1 as speech
import config_helper
import time

import silence_cut


def to_millis(timestamp):
    timestamp = str(timestamp)
    hours, minutes, seconds = (["0", "0"] + timestamp.split(":"))[-3:]
    hours = int(hours)
    minutes = int(minutes)
    seconds = float(seconds)
    miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
    return miliseconds


class Dataset_builder:
    def __init__(self):
        self.project_dir = None
        self.speaker_text_path = None
        self.wav_file_path = None
        self.index_start = None
        self.cut_length = None
        self.split_method = None
        self.contains_punc = None
        self.google_cloud_credentials_path = None
        self.transcription = None

    def set_values(self, dataset_dir, speaker_text_path, wav_file_path, index_start, cut_length, split_method,
                   contains_punc, google_cloud_credentials_path, transcription=True):

        self.project_dir = dataset_dir
        self.speaker_text_path = speaker_text_path
        self.wav_file_path = wav_file_path
        self.index_start = index_start
        if cut_length:
            self.cut_length = float(cut_length)
        self.split_method = split_method
        self.contains_punc = contains_punc
        self.google_cloud_credentials_path = google_cloud_credentials_path
        self.transcription = transcription

    def build_dataset(self):
        print("running")
        output_wavs_path = os.path.join(self.project_dir, "wavs")

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        if not os.path.exists(output_wavs_path):
            os.mkdir(output_wavs_path)

        if self.split_method == 0:

            set_value("label_build_status", "Detecting silences. This may take several minutes...")
            audio_name = self.wav_file_path
            w = AudioSegment.from_wav(audio_name)

            # s_len = 1000
            #
            # silence_cuts = silence.split_on_silence(w, min_silence_len=s_len, silence_thresh=-45, keep_silence=True)
            #
            # cuts = []
            # final_cuts = []
            #
            # def split_wav(wav, l):
            #     if (wav.duration_seconds * 1000) < (self.cut_length * 1000):
            #         output = []
            #         output.append(wav)
            #         return output
            #
            #     too_long = False
            #     while True:
            #         l -= 50
            #         if l == 0:
            #             print("Error, could not find small enough silence period for split, giving up")
            #             output = []
            #             output.append(wav)
            #             return output
            #
            #         start = time.time_ns()
            #         splits = silence.split_on_silence(wav, min_silence_len=l, silence_thresh=-45, keep_silence=True)
            #         print("Splitting:", round((time.time_ns() - start) / 1000))
            #
            #         start = time.time_ns()
            #         silence.detect_silence(wav, min_silence_len=l, silence_thresh=-45)
            #         print("Detecting:", round((time.time_ns() - start) / 1000))
            #
            #         print(f"Trying resplit... (l={l})")
            #         for s in splits:
            #             if (s.duration_seconds * 1000) > (self.cut_length * 1000):
            #                 too_long = True
            #         if too_long == True:
            #             too_long = False
            #         else:
            #             return splits
            #
            # # Keep splitting until all cuts are under max len
            #
            # for i, c in enumerate(silence_cuts):
            #     print(f"Checking phrase {i}/{len(silence_cuts)}...")
            #     c_splits = split_wav(c, 1000)
            #     for s in c_splits:
            #         cuts.append(s)
            # # rebuild small cuts into larger, but below split len
            # temp_cuts = AudioSegment.empty()
            #
            # for i, c in enumerate(cuts):
            #     prev_cuts = temp_cuts
            #     temp_cuts = temp_cuts + c
            #
            #     if i == (len(cuts) - 1):
            #         #on final entry
            #         if (temp_cuts.duration_seconds * 1000) > (self.cut_length * 1000):
            #             final_cuts.append(prev_cuts)
            #             final_cuts.append(c)
            #         else:
            #             final_cuts.append(temp_cuts)
            #     else:
            #         if ((temp_cuts.duration_seconds * 1000) + (cuts[i+1].duration_seconds * 1000)) > (self.cut_length * 1000):
            #             # combine failed, too long, add what has already been concatenated
            #             final_cuts.append(temp_cuts)
            #             temp_cuts = AudioSegment.empty()
            segment_size = 25
            min_len = int(get_value("input_min_seg_length")) / segment_size
            max_len = int(get_value("input_max_seg_length")) / segment_size
            final_cuts = silence_cut.speed_slice(w, segment_size=25, min_segments_in_slice=int(min_len),
                                                 max_segments_in_slice=int(max_len),
                                                 padding_start=int(get_value("input_padding_start")),
                                                 padding_end=int(get_value("input_padding_end")))

            for i, w in enumerate(final_cuts):
                output_wav_file = os.path.join(output_wavs_path, str(i + 1) + ".wav")
                w.export(output_wav_file, format="wav")

            # Process each cut into google API and add result to csv
            output_csv_file = os.path.join(self.project_dir, "output.csv")



            print("writing to: " + output_csv_file)
            with open(output_csv_file, 'w') as f:
                bucket_name = get_value("input_storage_bucket")
                newline = ''
                for i, c in enumerate(final_cuts):
                    x = i + 1
                    if not self.transcription:
                        f.write("{}wavs/{}.wav|".format(newline, x))
                        newline = '\n'
                        continue

                    print(f"Transcribing entry {x}/{len(final_cuts)}")
                    self.upload_blob(bucket_name, os.path.join(output_wavs_path, str(x) + ".wav"), "temp_audio.wav",
                                     google_cloud_credentials_path=self.google_cloud_credentials_path)
                    gcs_uri = "gs://{}/temp_audio.wav".format(bucket_name)

                    client = speech.SpeechClient.from_service_account_json(filename=self.google_cloud_credentials_path)

                    audio = speech.RecognitionAudio(uri=gcs_uri)

                    info = mediainfo(os.path.join(output_wavs_path, str(x) + ".wav"))
                    sample_rate = info['sample_rate']

                    if get_value("input_use_videomodel") == 1:
                        print("Using enchanced google model...")
                        config = speech.RecognitionConfig(
                            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                            sample_rate_hertz=int(sample_rate),
                            language_code=config_helper.cfg_get("transcription", "language_code"),
                            enable_automatic_punctuation=True,
                            enable_word_time_offsets=False,
                            enable_speaker_diarization=False,
                            # enhanced model for better performance?
                            use_enhanced=True,
                            model="video",  # "phone_call or video"
                        )
                    else:
                        config = speech.RecognitionConfig(
                            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                            sample_rate_hertz=int(sample_rate),
                            language_code=config_helper.cfg_get("transcription", "language_code"),
                            enable_automatic_punctuation=True,
                            enable_word_time_offsets=False,
                            enable_speaker_diarization=False,
                        )

                    operation = client.long_running_recognize(config=config, audio=audio)
                    response = operation.result(timeout=28800)

                    for result in response.results:
                        text = result.alternatives[0].transcript

                        # replace some symbols and google API word choice
                        text = text.replace("%", " percent")
                        text = text.replace("cuz", "cause")
                        text = text.replace("-", " ")
                        text = text.replace("&", "and")
                        print(text)
                        set_value("label_build_status", text)
                        f.write("{}wavs/{}.wav|{}".format(newline, x, text))
                        newline = '\n'
            print('\a')  # system beep
            set_value("label_build_status", "Done!")
            print("Done running builder!")

        else:
            # Aeneas mode
            if not get_value("label_speaker_text_path") or not get_value("label_wav_file_path"):
                print("Error, please choose text and/or audio files.")
                return

            if not os.path.exists("aeneas_out"):
                os.mkdir("aeneas_out")
            else:
                shutil.rmtree("aeneas_out")
                os.mkdir("aeneas_out")

            if not os.path.exists("aeneas_prepped"):
                os.mkdir("aeneas_prepped")
            else:
                shutil.rmtree("aeneas_prepped")
                os.mkdir("aeneas_prepped")

            audio_name = self.wav_file_path

            with open(self.speaker_text_path, 'r', encoding="utf8") as f:
                text = f.read()
                text = text.replace(';', '.')
                text = text.replace(':', '.')
                text = text.replace('-', ' ')
                text = text.replace('”', '')
                text = text.replace('“', '')
                text = text.replace('"', '.')
                text = text.replace('—', ' ')
                text = text.replace('’', '\'')
                text = text.replace(' –', '.')
                text = text.strip('\n')

                if self.contains_punc:
                    # remove any duplicate whitespace between words
                    text = " ".join(text.split())
                    phrase_splits = re.split(r'(?<=[\.\!\?])\s*',
                                             text)  # split on white space between sentences
                    phrase_splits = list(filter(None, phrase_splits))  # remove empty splits
                else:
                    # no punctuation from speech to text, so we must divid text by word count
                    phrase_splits = []
                    temp_line = []
                    text_split = text.split()
                    word_count_limit = 16

                    while len(text_split) > 0:
                        while len(temp_line) < word_count_limit and len(text_split) > 0:
                            temp_line.append(text_split.pop(0))
                        phrase_splits.append(" ".join(temp_line))
                        temp_line = []

                with open('aeneas_prepped/split_text', 'w') as f:
                    newline = ''
                    for s in phrase_splits:
                        if s:
                            stripped = s.strip()  # remove whitespace
                            f.write(newline + stripped)
                            newline = '\n'
                            # os.system('python -m aeneas.tools.execute_task ' + audio_name  + ' aeneas_prepped/split_text "task_adjust_boundary_percent_value=50|task_adjust_boundary_algorithm=percent|task_language=en|is_text_type=plain|os_task_file_format=csv" ' + 'aeneas_out/' + audio_name_no_ext + '.csv')
                os.system(
                    'python -m aeneas.tools.execute_task ' + audio_name + ' aeneas_prepped/split_text "task_adjust_boundary_percent_value=50|task_adjust_boundary_algorithm=percent|task_language=en|is_text_type=plain|os_task_file_format=csv" ' + 'aeneas_out/' + os.path.basename(
                        self.project_dir) + '.csv')

                output_exists = False
                if os.path.exists("{}/output.csv".format(os.path.basename(self.project_dir))):
                    # if file exists then prepare for append
                    output_exists = True

                new_csv_file = open("{}/output.csv".format(os.path.basename(self.project_dir)), 'a')
                if output_exists:
                    new_csv_file.write("\n")

                with open('aeneas_out/' + os.path.basename(self.project_dir) + '.csv', 'r') as csv_file:

                    index_count = int(self.index_start)
                    csv_reader = csv.reader(csv_file, delimiter=',')
                    csv_reader = list(csv_reader)  # convert to list
                    row_count = len(csv_reader)

                    newline = ""

                    for row in csv_reader:
                        beginning_cut = float(row[1])
                        end_cut = float(row[2])
                        text_out = row[3]
                        text_out = text_out.strip()
                        print("{} {} {} ".format(beginning_cut, end_cut, text_out))
                        c_length = end_cut - beginning_cut

                        # if cut is longer than cut length then split it even more
                        cut_length = float(self.cut_length)
                        if c_length > cut_length:

                            more_cuts = open("aeneas_prepped/temp.csv", 'w')

                            # save the current cut wav file to run on aeneas again
                            w = AudioSegment.from_wav(audio_name)
                            wav_cut = w[(beginning_cut * 1000):(end_cut * 1000)]
                            wav_cut.export("aeneas_prepped/tempcut.wav", format="wav")

                            split_list = []
                            num_cuts = math.ceil(c_length / cut_length)
                            text_list = text_out.split()
                            text_list_len = len(text_list)
                            split_len = math.ceil(text_list_len / num_cuts)
                            print("too long, making extra {} cuts. with length {}".format(num_cuts, split_len))
                            for i in range(1, num_cuts + 1):
                                words = []
                                for j in range(0, split_len):
                                    if not text_list:
                                        break
                                    words.append(text_list.pop(0))
                                split_list.append(" ".join(words))
                            print(split_list)
                            print()

                            newline_splits = ''
                            for phrase in split_list:
                                more_cuts.write(newline_splits + phrase)
                                newline_splits = '\n'
                            more_cuts.close()

                            os.system(
                                'python -m aeneas.tools.execute_task ' + "aeneas_prepped/tempcut.wav" + ' aeneas_prepped/temp.csv "task_adjust_boundary_percent_value=50|task_adjust_boundary_algorithm=percent|task_language=en|is_text_type=plain|os_task_file_format=csv" ' + 'aeneas_out/temp_out.csv')

                            csv_file_temp = open('aeneas_out/temp_out.csv', 'r')
                            csv_reader_temp = csv.reader(csv_file_temp, delimiter=',')
                            csv_reader_temp = list(csv_reader_temp)  # convert to list
                            row_count = len(csv_reader_temp)

                            w = AudioSegment.from_wav("aeneas_prepped/tempcut.wav")

                            for row in csv_reader_temp:
                                beginning_cut = float(row[1])
                                end_cut = float(row[2])
                                text_out = row[3]
                                text_out = text_out.strip()

                                wav_cut = w[(beginning_cut * 1000):(end_cut * 1000)]
                                new_wav_filename = "wavs/" + str(index_count) + ".wav"
                                new_csv_file.write("{}{}|{}".format(newline, new_wav_filename, text_out))
                                wav_cut.export("{}/{}".format(os.path.basename(self.project_dir), new_wav_filename),
                                               format="wav")
                                index_count += 1
                                newline = '\n'

                            csv_file_temp.close()

                        else:
                            w = AudioSegment.from_wav(audio_name)
                            wav_cut = w[(beginning_cut * 1000):(end_cut * 1000)]
                            new_wav_filename = "wavs/" + str(index_count) + ".wav"
                            new_csv_file.write("{}{}|{}".format(newline, new_wav_filename, text_out))
                            wav_cut.export("{}/{}".format(os.path.basename(self.project_dir), new_wav_filename),
                                           format="wav")
                            index_count += 1
                            newline = '\n'

                new_csv_file.close()
                set_value("label_build_status", "Building dataset done!")
                # Remove temporary directories
                shutil.rmtree("aeneas_prepped")
                shutil.rmtree("aeneas_out")
                print('\a')  # system beep
                print("Done with Aeneas!")

    def upload_blob(self, bucket_name, source_file_name, destination_blob_name, google_cloud_credentials_path=None):
        if not google_cloud_credentials_path:
            google_cloud_credentials_path = self.google_cloud_credentials_path
        storage_client = storage.Client.from_service_account_json(json_credentials_path=google_cloud_credentials_path)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        # print("File {} uploaded to {}.".format(source_file_name, destination_blob_name))

    def diarization(self, wavfile, bucket_name, project_dir, google_cloud_credentials_path, project_name=None):
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        if project_name:
            dianame = "diarization-" + project_name + "-" + str(round(time.time_ns() / 1000))
        else:
            dianame = "diarization-" + os.path.basename(wavfile) + "-" + str(round(time.time_ns() / 1000))
        output_dir = os.path.join(project_dir, dianame)
        os.mkdir(output_dir)

        print("Uploading {} to google cloud storage bucket".format(wavfile))
        set_value("label_diarization_run_info", "Uploading file to cloud storage bucket...")
        self.upload_blob(bucket_name, wavfile, "temp_audio.wav", google_cloud_credentials_path)
        gcs_uri = "gs://{}/temp_audio.wav".format(bucket_name)
        set_value("label_diarization_run_info", "Finished uploading.")

        client = speech.SpeechClient.from_service_account_json(filename=google_cloud_credentials_path)
        audio = speech.RecognitionAudio(uri=gcs_uri)
        info = mediainfo(wavfile)
        sample_rate = info['sample_rate']
        print("Transcribing {} with audio rate {}".format(wavfile, sample_rate))

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=int(sample_rate),
            language_code=config_helper.cfg_get("transcription", "language_code"),
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            enable_speaker_diarization=True,
            diarization_speaker_count=int(get_value("input_diarization_num")),
        )

        operation = client.long_running_recognize(config=config, audio=audio)
        print("Waiting for operation to complete, this may take several minutes...")
        set_value("label_diarization_run_info", "Waiting for operation to complete, this may take several minutes...")
        response = operation.result(timeout=28800)

        result = response.results[-1]
        words = result.alternatives[0].words

        active_speaker = 1
        transcript = []
        current_cut = 0
        previous_cut = 0
        speaker_wavs = []

        for x in range(int(get_value("input_diarization_num"))):
            speaker_wavs.append(AudioSegment.empty())
            transcript.append("")

        w = AudioSegment.from_wav(wavfile)

        for word in words:
            if word.speaker_tag == active_speaker:
                end_time = word.end_time
                current_cut = end_time.total_seconds() * 1e3
                # print(current_cut)
                transcript[active_speaker - 1] += word.word + ' '
            else:
                # speaker has changed
                transcript[active_speaker - 1] += word.word + ' '
                w_cut = w[(previous_cut):current_cut]
                previous_cut = current_cut
                speaker_wavs[active_speaker - 1] = speaker_wavs[active_speaker - 1] + w_cut
                active_speaker = word.speaker_tag

        # finish last wav cut
        w_cut = w[previous_cut:current_cut]
        speaker_wavs[active_speaker - 1] = speaker_wavs[active_speaker - 1] + w_cut

        for i, wave in enumerate(speaker_wavs):
            speaker_output = os.path.join(output_dir, "speaker_{}.wav".format(i + 1))
            speaker_wavs[i].export(speaker_output, format="wav")

        for i, text in enumerate(transcript):
            speaker_output = os.path.join(output_dir, "speaker_{}.txt".format(i + 1))
            f = open(speaker_output, 'w')
            f.write(transcript[i])
            f.close()

        set_value("label_diarization_run_info", "Done!")
        print("Done with diarization!")
        print('\a')  # system beep
