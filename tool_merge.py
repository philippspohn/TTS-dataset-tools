import os
import shutil

from dearpygui.core import set_value


def merge_datasets(input_csv_files, output_dataset_dir):
    output_wavs_dir = os.path.join(output_dataset_dir, "wavs")
    output_csv = os.path.join(output_dataset_dir, "output.csv")

    if not os.path.exists(output_dataset_dir):
        os.mkdir(output_dataset_dir)
    if not os.path.exists(output_wavs_dir):
        os.mkdir(output_wavs_dir)
    else:
        shutil.rmtree(output_wavs_dir)
        os.mkdir(output_wavs_dir)

    with open(output_csv, 'w') as f:
        newline = ''
        count = 0
        for file in input_csv_files:
            input_csv_dir = os.path.dirname(file)
            with open(file) as p:
                lines = p.readlines()
                for line in lines:
                    wav_path, text = line.split('|')
                    text = text.strip()
                    f.write(newline + 'wavs/' + str(count).zfill(4) + '.wav' + '|' + text)
                    newline = '\n'
                    input_wav_file = os.path.join(input_csv_dir, wav_path)
                    output_wav_file = os.path.join(output_wavs_dir, str(count).zfill(4) + '.wav')
                    shutil.copyfile(input_wav_file, output_wav_file)
                    count += 1
        print("Done merging!")
        set_value("tools_status", "Done merging projects. Output at " + output_dataset_dir)
        print('\a')  # system beep
