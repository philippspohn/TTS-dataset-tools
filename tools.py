import os.path
from shutil import copyfile
from threading import Timer
import webbrowser

from dearpygui.simple import *

import sox
from pydub import effects

from dataset_builder import *
from proofreader import *
from config_helper import cfg_get, cfg_set, cfg_getboolean, cfg_getint


def save_current_settings():
    cfg_set("general", "project_name", get_value("input_project_name"))
    cfg_set("general", "cloud_storage_bucket", get_value("input_storage_bucket"))
    cfg_set("general", "use_google_api", str(get_value("input_split")))
    cfg_set("general", "use_enhanced_video_model", str(get_value("input_use_videomodel")))
    cfg_set("general", "language_code", get_value("input_language_code"))
    cfg_set("general", "google_cloud_credentials_file",  get_value("label_credentials_file_path"))
    cfg_set("general", "diarization_project_directory",  get_value("diarization_project_directory"))
    cfg_set("general", "datasetbuilder_project_directory",  get_value("datasetbuilder_project_directory"))
    cfg_set("general", "save_proofreader_on_exit",  str(get_value("save_proofreader_on_exit")))


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.daemon = True
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


# Functions / callbacks for Google Speech
def open_wav_file_transcribe_call(sender, data):
    open_file_dialog(add_wav_file_transcribe)


def add_wav_file_transcribe(sender, data):
    # open working wav for transcribing
    set_value("label_wav_file_transcribe", "{}/{}".format(data[0], data[1]))


def open_credentials_file_call(sender, data):
    open_file_dialog(add_credentials_file)


def add_credentials_file(sender, data):
    # open working wav for transcribing
    set_value("label_credentials_file_path", "{}/{}".format(data[0], data[1]))

def run_google_speech_call(sender, data):
    # run transcription
    if get_value("label_wav_file_transcribe") == "":
        return
    builder.diarization(get_value("label_wav_file_transcribe"), get_value("input_storage_bucket"),
                        get_value("diarization_project_directory"), get_value("label_credentials_file_path"))


# Functions / callbacks for Dataset Builder
def run_dataset_builder_call(sender, data):
    # check to see if txt and wav file was selected
    set_value("label_build_status", "Running builder...")

    builder.set_values(get_value("datasetbuilder_project_directory"), get_value("label_speaker_text_path")
                       , get_value("label_wav_file_path"), get_value("input_starting_index"),
                       get_value("input_cut_length"), get_value("input_split"), get_value("input_contains_punc"), get_value("label_credentials_file_path"),
                       get_value("input_project_name"))
    builder.build_dataset()


def add_speaker_txt_file(sender, data):
    # open working speaker text
    set_value("label_speaker_text_path", "{}/{}".format(data[0], data[1]))


def add_speaker_wav_file(sender, data):
    # open working speaker text
    wav_file_path = "{}/{}".format(data[0], data[1])
    set_value("label_wav_file_path", wav_file_path)
    duration = AudioSegment.from_wav(wav_file_path).duration_seconds
    duration_min = math.floor(duration/60)
    duration_sec = round(duration - duration_min * 60)
    set_value("label_wav_duration", f'{str(duration_min).zfill(2)}m {str(duration_sec).zfill(2)}s -')


def open_speaker_txt_file_call(sender, data):
    open_file_dialog(add_speaker_txt_file)


def open_wav_file_call(sender, data):
    open_file_dialog(add_speaker_wav_file)


# Functions / callbacks for Proofreader
def save_csv_proofread_call():
    proofreader.save_csv_proofread()


def open_csv_proofread_call(sender, data):
    open_file_dialog(add_csv_file_proofread_call)


def open_last_csv_proofread_call(sender, data):
    path = cfg_get("general", "last_proofreader_file")
    if os.path.exists(path):
        add_csv_path_proofread(path)
    else:
        set_value("open_last_csv_proofread_info", "Not found!")

def add_csv_file_proofread_call(sender, data):
    proofreader.set_activated(True)
    path = "{}/{}".format(data[0], data[1])
    cfg_set("general", "last_proofreader_file", path)
    add_csv_path_proofread(path)


def add_csv_path_proofread(path):
    proofreader.set_filename(os.path.basename(path))
    # set_value("proofread_project_name", data[1])
    # clear table
    clear_table("table_proofread")
    # populate table with entries
    with open(path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        num_items = 0
        for row in csv_reader:
            # wav_filename should include path to wav file
            wav_filename_with_path = row[0]
            text = row[1]
            # Check if row is blank!
            if text:
                add_row("table_proofread", [wav_filename_with_path, text])
                num_items += 1

        proofreader.set_num_items(num_items)

    # get values from first 2 rows
    current_path = get_table_item("table_proofread", 0, 0)
    next_path = get_table_item("table_proofread", 1, 0)

    current_wav = AudioSegment.from_wav("{}/{}".format(os.path.dirname(path), current_path))
    next_wav = AudioSegment.from_wav("{}/{}".format(os.path.dirname(path), next_path))

    # set project sample rate
    wav_info = mediainfo("{}/{}".format(os.path.dirname(path), current_path))
    sample_rate = wav_info['sample_rate']
    proofreader.set_rate(sample_rate)
    set_value("current_input_text", get_table_item("table_proofread", 0, 1))
    set_value("next_input_text", get_table_item("table_proofread", 1, 1))
    add_data("current_path", current_path)
    add_data("next_path", next_path)

    proofreader.set_project_path(os.path.dirname(path))
    proofreader.set_current(current_wav)
    proofreader.set_next(next_wav)
    proofreader.plot_wavs()

    # set autosave timer on
    rt.start()

def save_current_text_call(sender, data):
    if proofreader.get_current() == None:
        return
    row = proofreader.get_selected_row()
    text = get_value("current_input_text")
    set_table_item("table_proofread", row, 1, text)


def save_next_text_call(sender, data):
    if proofreader.get_next() == None:
        return
    row = proofreader.get_selected_row()
    text = get_value("next_input_text")
    set_table_item("table_proofread", row + 1, 1, text)


def current_save_call():
    proofreader.save_current()


def next_save_call():
    proofreader.save_next()


def save_all_call(sender, data):
    save_current_text_call("", "")
    save_next_text_call("", "")
    current_save_call("", "")
    next_save_call("", "")


def play_selection_call(sender, data):
    proofreader.play_selection()


def cut_selection_call(sender, data):
    proofreader.cut_selection()


def paste_selection_call(sender, data):
    proofreader.paste_selection()


def current_play_call(sender, data):
    proofreader.current_play()


def next_play_call(sender, data):
    proofreader.next_play()


def current_remove_call(sender, data):
    proofreader.current_remove()


def next_remove_call(sender, data):
    proofreader.next_remove()


def stop_playing_call(sender, data):
    proofreader.stop()


def table_row_selected_call(sender, data):
    proofreader.table_row_selected()

def reset_current_call():
    w = proofreader.get_current()
    if w == None:
        return
    row = proofreader.get_selected_row()
    path = Path(get_table_item("table_proofread", row, 0))
    proofreader.set_current(AudioSegment.from_wav(os.path.join(proofreader.get_project_path(), "wavs", path.name)))
    proofreader.set_current_p(None)
    proofreader.set_selection_range_current(None, None)
    proofreader.plot_wavs()

def reset_next_call():
    w = proofreader.get_next()
    if w == None:
        return
    row = proofreader.get_selected_row() + 1
    path = Path(get_table_item("table_proofread", row, 0))
    proofreader.set_next(AudioSegment.from_wav(os.path.join(proofreader.get_project_path(), "wavs", path.name)))
    proofreader.plot_wavs()

def duplicate_selection():
    c = proofreader.get_selection_range_current()
    n = proofreader.get_selection_range_next()
    if c[0]:
        duplicate_current_call()
    elif n[0]:
        duplicate_next_call()

def duplicate_current_call():
    w = proofreader.get_current()
    if w == None:
        return

    w_current = proofreader.get_current()
    num_samples = len(w_current.get_array_of_samples())
    drag_in, drag_out = proofreader.get_selection_range_current()
    points = [drag_in, drag_out]
    in_point = min(points)
    out_point = max(points)

    if in_point is None or out_point is None:
        return

    in_point = (in_point / 1200) * (num_samples / proofreader.get_rate()) * 1000
    out_point = (out_point / 1200) * (num_samples / proofreader.get_rate()) * 1000
    w_new = w_current[in_point:out_point]

    # Add to table
    row = proofreader.get_selected_row()
    old_path = Path(get_table_item("table_proofread", row, 0))
    text = get_table_item("table_proofread", row, 1)
    new_path = os.path.join(proofreader.get_project_path(), old_path)
    new_path = os.path.dirname(new_path)
    name = str(current_milli_time())
    new_path = os.path.join(new_path, name + ".wav")
    add_row("table_proofread", [os.path.join(os.path.dirname(old_path), name) + ".wav", text])

    proofreader.set_num_items(proofreader.get_num_items() + 1)

    # Update files
    w_new.export(new_path, format="wav")
    set_value("proofread_status", f"Created duplicate {name} and appened at the end. Saved csv.")

    save_csv_proofread_call()


def duplicate_next_call():
    w = proofreader.get_next()
    if w == None:
        return

    w_next = proofreader.get_next()
    num_samples = len(w_next.get_array_of_samples())
    drag_in, drag_out = proofreader.get_selection_range_next()
    points = [drag_in, drag_out]
    in_point = min(points)
    out_point = max(points)

    if in_point is None or out_point is None:
        return

    in_point = (in_point / 1200) * (num_samples / proofreader.get_rate()) * 1000
    out_point = (out_point / 1200) * (num_samples / proofreader.get_rate()) * 1000
    w_new = w_next[in_point:out_point]

    # Add to table
    row = proofreader.get_selected_row() + 1
    old_path = Path(get_table_item("table_proofread", row, 0))
    text = get_table_item("table_proofread", row, 1)
    new_path = os.path.join(proofreader.get_project_path(), old_path)
    new_path = os.path.dirname(new_path)
    name = str(current_milli_time())
    new_path = os.path.join(new_path, name + ".wav")
    add_row("table_proofread", [os.path.join(os.path.dirname(old_path), name) + ".wav", text])

    proofreader.set_num_items(proofreader.get_num_items() + 1)

    # Update files
    w_new.export(new_path, format="wav")
    set_value("proofread_status", f"Created duplicate {name} and appened at the end. Saved csv.")

    save_csv_proofread_call()

def on_current_input_text_change():
    if proofreader.get_num_items() == 0:
        return
    row = proofreader.get_selected_row()
    set_table_item("table_proofread", row, 1, get_value("current_input_text"))

def on_next_input_text_change():
    if proofreader.get_num_items() == 0 or proofreader.get_num_items() == 1:
        return
    row = proofreader.get_selected_row() + 1
    set_table_item("table_proofread", row, 1, get_value("next_input_text"))

def exit_callback():
    if get_value("save_proofreader_on_exit"):
        save_csv_proofread_call()
        next_save_call()
        current_save_call()

set_exit_callback(exit_callback)

# Mouse Callbacks

def mouse_clicked_proofread_call(sender, data):
    if is_mouse_button_clicked(1):
        mouse_pos = get_drawing_mouse_pos()
        if is_item_hovered("current_plot_drawing_new"):
            proofreader.set_current_p(mouse_pos[0])
            proofreader.set_next_p(None)
            proofreader.draw_p_selection("current_plot_drawing_new", mouse_pos[0])
        elif is_item_hovered("next_plot_drawing_new"):
            proofreader.set_next_p(mouse_pos[0])
            proofreader.set_current_p(None)
            proofreader.draw_p_selection("next_plot_drawing_new", mouse_pos[0])

    elif is_mouse_button_clicked(2):
        proofreader.silence_selection()
    else:
        return


def mouse_wheel_proofread_call(sender, data):
    if not is_item_hovered("table_proofread") and proofreader.is_activated():
        if data > 0:
            proofreader.scroll_up()
        if data < 0:
            proofreader.scroll_down()


# def mouse_move_proofread_call(sender, data):


# callbacks for Other Tools
def tools_open_project_call(sender, data):
    select_directory_dialog(add_tools_project_call)


def add_tools_project_call(sender, data):
    pname = data[0] + '\\' + data[1]
    set_value("tools_project_name", pname)


def tools_process_wavs_call(sender, data):
    pname = get_value("tools_project_name")
    if not pname:
        return
    # creat sox transformer
    tfm = sox.Transformer()
    if get_value("tools_trimadd"):
        print("Trimming and padding with silence")
        set_value("tools_status", "Trimming and padding with silence")
        tfm.silence(1, .15, .1)
        tfm.silence(-1, .15, .1)
        tfm.pad(.25, .5)
    if get_value("tools_resample"):
        print("Resampling")
        set_value("tools_status", "Resampling")
        tfm.rate(22050)

    if not os.path.exists(pname + '\\processed'):
        os.mkdir(pname + '\\processed')
    if not os.path.exists(pname + '\\processed\\wavs'):
        os.mkdir(pname + '\\processed\\wavs')

    with open(pname + "\\output.csv", 'r') as f:
        lines = f.readlines()
        for line in lines:
            wav_path, text = line.split('|')
            processedpath = pname + '\\processed\\' + wav_path
            text = text.strip()  # remove \r\n
            tfm.build_file(pname + '\\' + wav_path, processedpath)
            print(f"Processing {wav_path}")
            set_value("tools_status", "Processing {}".format(wav_path))
            if get_value("tools_compress"):
                w = AudioSegment.from_wav(processedpath)
                w = effects.compress_dynamic_range(w, threshold=-10)
                w.export(processedpath, format='wav')

        print("Done processing wavs!")
        set_value("tools_status", "Done processing wavs. Output at {}/processed/wavs.".format(pname))
        print('\a')  # system beep


def open_file_dialogue_and_set_label(label_name, save_to_config=False):
    return lambda: open_file_dialog(lambda sender, data: set_label(label_name, os.path.join(data[0], data[1]), save_to_config))


def open_directory_dialogue_and_set_label(label_name, save_to_config=False):
    return lambda: select_directory_dialog(lambda sender, data: set_label(label_name, os.path.join(data[0], data[1]), save_to_config))


def set_label(label_name, value, save_to_config):
    set_value(label_name, value)
    if save_to_config:
        cfg_set("general", label_name, value)


def tools_open_project_merge_call(sender, data):
    open_file_dialog(add_tools_project_merge_call)


def tools_clear_merge_projects_call(sender, data):
    clear_table("tools_table_merge")


def add_tools_project_merge_call(sender, data):
    # add project to table list
    project_path = os.path.join(data[0], data[1])
    add_row("tools_table_merge", [project_path])


def tools_merge_projects_call(sender, data):
    table = get_table_data("tools_table_merge")
    if not table:
        print("Table is empty")
        return


    target_dir = get_value("label_tool_open_marge_target_dir")
    if not target_dir:
        target_dir = "merged"

    output_wavs_dir = os.path.join(target_dir, "wavs")
    output_csv = os.path.join(target_dir, "output.csv")

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    if not os.path.exists(output_wavs_dir):
        os.mkdir(output_wavs_dir)
    else:
        shutil.rmtree(output_wavs_dir)
        os.mkdir(output_wavs_dir)

    with open(output_csv, 'w') as f:
        newline = ''
        count = 0
        for row in table:
            input_csv_file = row[0]
            input_csv_dir = os.path.dirname(input_csv_file)
            with open(input_csv_file) as p:
                lines = p.readlines()
                for line in lines:
                    wav_path, text = line.split('|')
                    text = text.strip()
                    f.write(newline + 'wavs/' + str(count).zfill(4) + '.wav' + '|' + text)
                    newline = '\n'
                    input_wav_file = os.path.join(input_csv_dir, wav_path)
                    output_wav_file = os.path.join(output_wavs_dir, str(count).zfill(4) + '.wav')
                    copyfile(input_wav_file, output_wav_file)
                    count += 1
        print("Done merging!")
        set_value("tools_status", "Done merging projects. Output at " + target_dir)
        print('\a')  # system beep


def tools_table_merge_call(sender, data):
    pass


def tools_export_sets_call(sender, data):
    pname = get_value("tools_project_name")
    if not pname:
        return

    training_set = []
    val_set = []
    waveglow_set = []

    with open(pname + "\\output.csv", 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            wav_path, text = line.split('|')
            if i < 50:
                val_set.append(line)
                waveglow_set.append(wav_path)
            else:
                training_set.append(line)
                waveglow_set.append(wav_path)

    with open(pname + "\\training.csv", 'w') as f:
        for line in training_set:
            f.write(line)
    with open(pname + "\\validation.csv", 'w') as f:
        for line in val_set:
            f.write(line)
    with open(pname + "\\waveglow_training.csv", 'w') as f:
        newline = ''
        for line in waveglow_set:
            f.write(newline + line)
            newline = '\n'

        print("Done exporting sets!")
        set_value("tools_status", "Done exporting sets. Output at {}/.".format(pname))
        print('\a')  # system beep


def tools_format_text_call(sender, data):
    pname = get_value("tools_project_name")
    if not pname:
        return
    newcsv = []

    if not os.path.exists(pname + '\\processed'):
        os.mkdir(pname + '\\processed')
    with open(pname + "\\output.csv", 'r') as f:
        lines = f.readlines()
        newline = ''
        for line in lines:
            wav_path, text = line.split('|')
            text = text.strip() + '~'
            newcsv.append(newline + wav_path + '|' + text)
            newline = '\n'

    with open(pname + '\\processed\output.csv', 'w') as f:
        for line in newcsv:
            f.write(line)

        print("Done formatting text!")
        set_value("tools_status", "Done formatting text. Output at {}/processed/output.csv".format(pname))
        print('\a')  # system beep


def tools_reindex_project_call(sender, data):
    pname = get_value("tools_project_name")
    index = int(get_value("tools_input_reindex"))
    if not pname or not index:
        return

    newcsv = []

    if not os.path.exists(pname + '\\reindexed'):
        os.mkdir(pname + '\\reindexed')
    if not os.path.exists(pname + '\\reindexed\\wavs'):
        os.mkdir(pname + '\\reindexed\\wavs')
    with open(pname + "\\output.csv", 'r') as f:
        lines = f.readlines()
        newline = ''
        for line in lines:
            wav_path, text = line.split('|')
            text = text.strip()
            newcsv.append(newline + 'wavs/' + str(index) + '.wav' + '|' + text)
            copyfile(pname + '\\' + wav_path, pname + '\\reindexed\\wavs\\' + str(index) + '.wav')
            index += 1
            newline = '\n'
        with open(pname + '\\reindexed\\output.csv', 'w') as f:
            for line in newcsv:
                f.write(line)
        print("Done reindexing!")
        set_value("tools_status", "Done reindexing project. Output at {}/reindexed/".format(pname))
        print('\a')  # system beep


# Main functions
themes = ["Dark", "Light", "Classic", "Dark 2", "Grey", "Dark Grey", "Cherry", "Purple", "Gold", "Red"]


def apply_theme_call(sender, data):
    theme = get_value("Themes")
    set_theme(theme)


def apply_font_scale_call(sender, data):
    scale = .01 * float(get_value("Font Scale"))
    set_global_font_scale(scale)


def render_call(sender, data):

    if is_key_pressed(mvKey_K) and is_key_down(mvKey_LControl):
        proofreader.cut_selection()

    if is_key_pressed(mvKey_R) and is_key_down(mvKey_LControl):
        proofreader.cut_outside_selction()

    if is_key_pressed(mvKey_D) and is_key_down(mvKey_LWin):
        duplicate_selection()

    # mouse
    if is_mouse_button_released(0):
        # if drag values set, copy and then clear
        mouse_pos = get_drawing_mouse_pos()

        if proofreader.get_drag_in_current():
            din = proofreader.get_drag_in_current()
            dout = proofreader.get_drag_out_current()

            proofreader.set_selection_range_current(din, dout)
            proofreader.set_selection_range_next(None, None)
            proofreader.set_drag_in_current(None)
            proofreader.set_drag_out_current(None)
            # if drag values set, copy and then clear
        if proofreader.get_drag_in_next():
            din = proofreader.get_drag_in_next()
            dout = proofreader.get_drag_out_next()

            proofreader.set_selection_range_next(din, dout)
            proofreader.set_selection_range_current(None, None)
            proofreader.set_drag_in_next(None)
            proofreader.set_drag_out_next(None)
        # print(f"drag done: {proofreader.get_selection_range_current()}  {proofreader.get_selection_range_next()}")
    else:
        if proofreader.is_playing():
            # Draw playhead
            play_in = proofreader.get_play_in()
            total_time_playing = proofreader.get_playing_total_time()
            time_playing = proofreader.get_playing_time()

            playhead_percentage = (play_in + time_playing) / total_time_playing
            mouse_x_pos = playhead_percentage * 1200

            if proofreader.is_current_playing():
                proofreader.draw_playhead("current_plot_drawing_new", mouse_x_pos)
            else:
                proofreader.draw_playhead("next_plot_drawing_new", mouse_x_pos)
        else:
            proofreader.clear_playerhead()

        # Draw selector
        mouse_pos = get_drawing_mouse_pos()
        if is_item_hovered("current_plot_drawing_new"):
            proofreader.draw_selector("current_plot_drawing_new", mouse_pos[0])
        elif is_item_hovered("next_plot_drawing_new"):
            proofreader.draw_selector("next_plot_drawing_new", mouse_pos[0])



def handle_mouse_down():
    if is_mouse_button_down(0):
        mouse_pos = get_drawing_mouse_pos()
        if is_item_hovered("current_plot_drawing_new"):
            if proofreader.get_drag_in_current() == None:
                proofreader.set_drag_in_current(mouse_pos[0])
            dout = mouse_pos[0]
            if dout < 10:
                dout = 0
            if dout > 1190:
                dout = 1200
            proofreader.set_drag_out_current(dout)
            proofreader.draw_dragbox("current_plot_drawing_new", dout)
        elif is_item_hovered("next_plot_drawing_new"):
            if proofreader.get_drag_in_next() == None:
                proofreader.set_drag_in_next(mouse_pos[0])
            dout = mouse_pos[0]
            if dout < 10:
                dout = 0
            if dout > 1190:
                dout = 1200
            proofreader.set_drag_out_next(dout)
            proofreader.draw_dragbox("next_plot_drawing_new", dout)

def handle_key_down():
    # keyboard handling for proofreader
    if not is_key_down(mvKey_LControl) and not is_key_down(mvKey_LWin):
        if is_key_pressed(mvKey_F9):
            play_selection_call("", "")

        if is_key_pressed(mvKey_F11):
            cut_selection_call("", "")

        if is_key_pressed(mvKey_F12):
            paste_selection_call("", "")

        if is_key_pressed(mvKey_Up) or is_key_pressed(mvKey_A):
            # move to previous entries
            proofreader.scroll_up()

        if is_key_pressed(mvKey_Down) or is_key_pressed(mvKey_D):
            # move to next entries
            proofreader.scroll_down()

    if is_key_pressed(mvKey_Insert) or (is_key_pressed(mvKey_S) and is_key_down(mvKey_LWin)):
        if proofreader.get_current() == None:
            return
        save_current_text_call("", "")
        save_next_text_call("", "")
        current_save_call()
        next_save_call()
        proofreader.save_csv_proofread()
        set_value("proofread_status", "All saved")

    if is_key_pressed(mvKey_Prior):
        current_play_call("", "")

    if is_key_pressed(mvKey_Next):
        next_play_call("", "")


    if is_key_pressed(mvKey_Pause):
        proofreader.stop()

    if is_key_pressed(mvKey_Spacebar):
        if proofreader.is_playing():
            proofreader.stop()
        else:
            proofreader.play_selection()

    if is_key_pressed(mvKey_Control) and is_key_pressed(mvKey_S):
        save_csv_proofread_call()







set_key_down_callback(handle_key_down)
set_mouse_down_callback(handle_mouse_down)

set_main_window_size(1500, 1040)
set_main_window_title("DeepVoice Dataset Tools 1.0 by YouMeBangBang")
# set_global_font_scale(1.5)


set_theme("Grey")
# set_theme_item(mvGuiCol_WindowBg, 0, 0, 200, 200)

proofreader = Proofreader()
builder = Dataset_builder()
set_mouse_click_callback(mouse_clicked_proofread_call)
set_mouse_wheel_callback(mouse_wheel_proofread_call)
# set_mouse_move_callback(mouse_move_proofread_call)
# set_mouse_release_callback(mouse_release_proofread_call)

add_additional_font("CheyenneSans-Light.otf", 21)

set_render_callback(render_call)

# set autosave timer
rt = RepeatedTimer(180, proofreader.autosave)  # time in seconds per autosave
rt.stop()

with window("mainWin"):
    with tab_bar("tb1"):
        with tab("tab0", label="Dataset Tools"):
            add_spacing(count=5)
            add_text("Enter name of project: ")
            add_same_line(spacing=10)
            add_input_text("input_project_name", width=500, default_value=cfg_get("general", "project_name"), label="")
            add_spacing(count=5)
            add_text("Enter path to google cloud credentials json-file")
            add_same_line(spacing=5)
            add_button("open_credentials_file_path", callback=open_credentials_file_call, label="Open credentials file")
            add_same_line(spacing=5)
            add_button("open_credentials_file_path_info", label="[Learn more]",
                       callback=lambda: webbrowser.open("https://cloud.google.com/docs/authentication/getting-started"))
            add_same_line(spacing=10)
            add_label_text("label_credentials_file_path", label="", default_value=cfg_get("general", "google_cloud_credentials_file"))
            add_spacing(count=5)
            add_text("Enter name of your clould storage bucket: ")
            add_same_line(spacing=10)
            add_input_text("input_storage_bucket", width=500, default_value=cfg_get("general", "cloud_storage_bucket"),
                           label="")
            add_spacing(count=5)
            add_text("Language-Code: ")
            add_same_line(spacing=10)
            add_input_text("input_language_code", width=500, default_value=cfg_get("general", "language_code"),
                           label="")
            add_same_line(spacing=10)
            add_button("input_list_lang_codes", label="[List]",
                       callback=lambda: webbrowser.open("https://cloud.google.com/speech-to-text/docs/languages"))
            add_spacing(count=2)

            # Diarization
            add_drawing("hline1", width=800, height=1)
            draw_line("hline1", [0, 0], [800, 0], [255, 0, 0, 255], 1)
            add_spacing(count=2)
            add_text("DIARIZATION: ")
            add_spacing(count=5)
            add_text("How many speakers for diarization?: ")
            add_same_line(spacing=10)
            add_input_text("input_diarization_num", width=40, default_value="1", label="")
            add_spacing(count=5)
            add_text("Select the wav file to transcribe (must be mono)")
            add_spacing(count=5)
            add_button("open_wav_file_transcribe", callback=open_wav_file_transcribe_call, label="Open wav file")
            add_same_line(spacing=10)
            add_label_text("label_wav_file_transcribe", label="")
            add_spacing(count=5)
            add_button("button_diarization_project_directory", label="Open output dir",
                       callback=open_directory_dialogue_and_set_label("diarization_project_directory", True))
            add_same_line(spacing=10)
            add_label_text("diarization_project_directory", default_value=cfg_get("general", "diarization_project_directory"), label="")
            add_spacing(count=5)
            add_button("run_google_speech", callback=run_google_speech_call, label="Run Google Diarization")
            add_same_line(spacing=10)
            add_label_text("label_diarization_run_info", label="")
            add_spacing(count=2)

            # Transcription
            add_drawing("hline2", width=800, height=1)
            draw_line("hline2", [0, 0], [800, 0], [255, 0, 0, 255], 1)
            add_spacing(count=2)
            add_text("TRANSCRIBE AND BUILD DATASET: ")
            add_spacing(count=5)
            add_text("Enter starting index (default is 1): ")
            add_same_line(spacing=10)
            add_input_text("input_starting_index", width=200, default_value="1", label="")
            add_spacing(count=5)
            add_text("Enter max cut length in seconds (default is 11.0): ")
            add_same_line(spacing=10)
            add_input_text("input_cut_length", width=200, default_value="11.0", label="")
            add_spacing(count=5)
            add_text("Use Google API (recommended) or aeneas to build dataset?")
            add_same_line(spacing=10)
            add_text("\t")
            add_same_line(spacing=1)
            add_radio_button("input_split", items=["Google API (recommended)", "Aeneas"],
                             default_value=cfg_getint("general", "use_google_api"))
            add_spacing(count=3)
            add_text("Use Google API enhanced 'video' model? (slightly extra cost)")
            add_same_line(spacing=10)
            add_checkbox("input_use_videomodel", default_value=cfg_getboolean("general", "use_enhanced_video_model"),
                         label="")
            add_spacing(count=5)
            add_text("If using Aeneas, does the text have proper punctuation? ")
            add_same_line(spacing=10)
            add_checkbox("input_contains_punc", default_value=1, label="")
            add_spacing(count=5)
            add_text("Select speaker text file (Aeneas only): ")
            add_same_line(spacing=10)
            add_button("open_speaker_text", callback=open_speaker_txt_file_call, label="Open txt file")
            add_same_line(spacing=10)
            add_label_text("label_speaker_text_path", label="")
            add_spacing(count=5)
            add_text("Select speaker audio wav file: ")
            add_same_line(spacing=10)
            add_button("open_wav_file", callback=open_wav_file_call, label="Open wav file")
            add_same_line(spacing=10)
            add_label_text("label_wav_duration", label="")
            set_item_width("label_wav_duration", 80)
            add_same_line(spacing=3)
            add_label_text("label_wav_file_path", label="")

            add_button("button_datasetbuilder_open_project", label="Open project directory",
                       callback=open_directory_dialogue_and_set_label("datasetbuilder_project_directory", True))
            add_same_line(spacing=10)
            add_label_text("datasetbuilder_project_directory", label="",
                           default_value=cfg_get("general", "datasetbuilder_project_directory"))

            add_spacing(count=5)
            add_button("run_dataset_builder", callback=run_dataset_builder_call, label="Run dataset builder")
            add_label_text("label_build_status", label="")
            add_spacing(count=2)
            add_drawing("hline1_3", width=800, height=1)
            draw_line("hline1_3", [0, 0], [800, 0], [255, 0, 0, 255], 1)
            add_spacing(count=2)
            add_button("save_current_settings", callback=save_current_settings, label="Save config")

        with tab("tab2", label="Proofread Dataset"):
            tabledata = []
            with group("group3"):
                add_text(
                    "ALWAYS BACKUP PROJECT FOLDER BEFORE EDITING! \n\nChoose a csv file to proofread and edit wavs. \nYou can adjust the column width for better viewing.")
            add_same_line(spacing=100)
            with group("group4"):
                add_text("Keyboard shortcuts-")
                add_text(
                    "Up arrow: load previous entries. \nDown arrow: load next entries.  \n'Insert': save all wavs and text. \nUse mouse scroll wheel to navigate entries.\nMiddle mouse button to silence selection.\nRight mouse button to set paste position.")
                add_same_line(spacing=40)
                add_text(
                    "'PgUp': current play. \n'PgDwn': next play. \n'Pause-Break': stop playing.\n'F9': Play selection.\n'F11': cut selection region.\n'F12': paste cut selection.")
            add_button("open_csv_proofread", callback=open_csv_proofread_call, label="Open csv file")
            add_same_line(spacing=50)
            add_button("save_csv_proofread", callback=save_csv_proofread_call, label="Save csv file")
            add_same_line(spacing=50)
            add_button("open_last_csv_proofread", callback=open_last_csv_proofread_call, label="Open last file")
            add_same_line(spacing=10)
            add_label_text("proofread_status", default_value="", label="")
            # add_same_line(spacing=10)     
            # add_input_text("proofread_project_name", width=250, default_value="", label="" )
            add_spacing(count=3)
            add_table("table_proofread", ["Wav path", "Text"], callback=table_row_selected_call, height=200)
            add_spacing(count=2)
            add_input_text("current_input_text", width=1475, default_value="", label="",  callback=on_current_input_text_change)
            add_spacing(count=2)
            with group("group5"):
                add_drawing("current_plot_drawing_new", width=1200, height=200)
                # add_plot("current_plot", show=False, label="Current Wav", width=1200, height=200, xaxis_no_tick_labels=True,  
                #     yaxis_no_tick_labels=True, no_mouse_pos=True, crosshairs=True, xaxis_lock_min=True, xaxis_lock_max=True, yaxis_lock_min=True, yaxis_lock_max=True)
                # add_drawing("current_plot_drawing", show=False, width=1200, height=16)
            add_same_line(spacing=10)
            with group("group1"):
                add_button("save_all", callback=save_all_call, label="Save all")
                add_same_line(spacing=10)
                add_button("current_play", callback=current_play_call, label="Play")
                add_same_line(spacing=10)
                add_image_button("stop_playing", "stop.png", callback=stop_playing_call, height=20, width=20,
                                 background_color=[0, 0, 0, 255])
                # add_button("current_play_to_selection", callback=current_play_to_selection_call, label="Play to selection")       
                # add_button("current_play_from_selection", callback=current_play_from_selection_call, label="Play from selection")  
                add_button("play_selection_current", callback=play_selection_call, label="Play selection")
                add_button("cut_selection_current", callback=cut_selection_call, label="Cut selection")
                add_button("cut_selection_outside_current", callback=lambda: proofreader.cut_outside_selction(), label="Cut outside selection")
                add_button("paste_selection_current", callback=paste_selection_call, label="Paste selection")
                add_button("undo_current", callback=reset_current_call, label="Reset")
                add_same_line(spacing=5)
                add_button("duplicate_current", callback=duplicate_current_call, label="Duplicate Sel")

                # add_button("current_send", callback=current_send_call, label="Send end cut to Next")  
                # add_button("current_save", callback=current_save_call, label="Save wav")
                # add_spacing(count=5)   
                # add_button("current_delete_beginningcut", callback=current_delete_beginningcut_call, label="Cut and delete beginning")
                # add_button("current_delete_endcut", callback=current_delete_endcut_call, label="Cut and delete end")
                add_spacing(count=5)
                add_button("current_remove", callback=current_remove_call, label="Remove entry!")
            # proofreader.current_plot_drawing_set_point(0)
            add_spacing(count=5)
            add_input_text("next_input_text", width=1475, default_value="", label="", callback=on_next_input_text_change)
            add_spacing(count=3)
            with group("group6"):
                add_drawing("next_plot_drawing_new", width=1200, height=200)

                # add_plot("next_plot", label="Next Wav", width=1200, height=200, xaxis_no_tick_labels=True, 
                #     yaxis_no_tick_labels=True, no_mouse_pos=True, crosshairs=True, xaxis_lock_min=True, xaxis_lock_max=True, yaxis_lock_min=True, yaxis_lock_max=True)
                # add_drawing("next_plot_drawing", width=1200, height=10)  
            add_same_line(spacing=10)
            with group("group2"):
                add_button("save_all2", callback=save_all_call, label="Save all")
                add_same_line(spacing=10)
                add_button("next_play", callback=next_play_call, label="Play")
                add_same_line(spacing=10)
                add_image_button("stop_playing2", "stop.png", callback=stop_playing_call, height=20, width=20,
                                 background_color=[0, 0, 0, 255])
                add_button("play_selection_next", callback=play_selection_call, label="Play selection")
                add_button("cut_selection_next", callback=cut_selection_call, label="Cut selection")
                add_button("cut_selection_outside_next", callback=lambda: proofreader.cut_outside_selction(), label="Cut outside selection")
                add_button("paste_selection_next", callback=paste_selection_call, label="Paste selection")
                add_button("undo_next", callback=reset_next_call, label="Reset")
                add_same_line(spacing=5)
                add_button("duplicate_next", callback=duplicate_next_call, label="Duplicate Sel")
                # add_button("next_play_to_selection", callback=next_play_to_selection_call, label="Play to selection")  
                # add_button("next_play_from_selection", callback=next_play_from_selection_call, label="Play from selection")  
                # add_button("next_send", callback=next_send_call, label="Send beginning cut to Current")  
                # add_button("next_save", callback=next_save_call, label="Save wav")    
                # add_spacing(count=5)   
                # add_button("next_delete_beginningcut", callback=next_delete_beginningcut_call, label="Cut and delete beginning")                 
                # add_button("next_delete_endcut", callback=next_delete_endcut_call, label="Cut and delete end")
                add_spacing(count=5)
                add_button("next_remove", callback=next_remove_call, label="Remove entry!")
                # proofreader.next_plot_drawing_set_point(0)
            add_checkbox("save_proofreader_on_exit", default_value=cfg_getboolean("general", "save_proofreader_on_exit"),
                         label="Save on exit")
            add_same_line(spacing=10)
            add_button("save_current_settings_proofreader", callback=save_current_settings, label="Save config")
        # with tab("tab3", label="Increase Dataset"):
        #     add_spacing(count=5)           

        with tab("tab4", label="Other Tools"):
            add_spacing(count=5)
            add_drawing("hline3", width=800, height=1)
            draw_line("hline3", [0, 0], [800, 0], [255, 0, 0, 255], 1)
            add_text("MERGE PROJECT FOLDERS INTO SINGLE PROJECT:")
            add_spacing(count=5)
            add_button("tools_open_project_merge", callback=tools_open_project_merge_call, label="Add project")
            add_spacing(count=3)
            add_table("tools_table_merge", ["Projects to merge"], callback=tools_table_merge_call, height=150,
                      width=1000)
            add_spacing(count=3)
            add_button("tools_clear_merge_projects", callback=tools_clear_merge_projects_call, label="Clear table")
            add_spacing(count=3)
            add_button("tool_open_marge_target_dir", label="Output directory (default: ./merge)",
                       callback=open_directory_dialogue_and_set_label("label_tool_open_marge_target_dir"))
            add_same_line(spacing=3)
            add_label_text("label_tool_open_marge_target_dir", label="")
            add_spacing(count=3)
            add_button("tools_merge_projects", callback=tools_merge_projects_call, label="Merge projects")
            add_spacing(count=3)
            add_drawing("hline4", width=800, height=1)
            draw_line("hline4", [0, 0], [800, 0], [255, 0, 0, 255], 1)
            add_text("WAV AND TEXT FORMATTING\nChoose project directory:")
            add_spacing(count=3)
            add_button("tools_open_project", callback=tools_open_project_call, label="Open project")
            add_same_line(spacing=10)
            add_text("Current project: ")
            add_same_line(spacing=5)
            add_label_text("tools_project_name", label="")
            add_spacing(count=3)
            add_button("tools_reindex_project", callback=tools_reindex_project_call, label="Reindex wavs\nand text")
            add_same_line(spacing=10)
            add_input_text("tools_input_reindex", label="New starting index", width=75, default_value="1000")
            add_spacing(count=3)
            add_text("Text operations:")
            add_spacing(count=3)
            add_button("tools_format_text", callback=tools_format_text_call, label="Trim text and\nadd '~' endchar")
            add_spacing(count=3)
            add_button("tools_export_sets", callback=tools_export_sets_call,
                       label="Export training, validation,\nand waveglow csv files")
            add_spacing(count=3)
            add_text("Wav operations:")
            add_spacing(count=3)
            add_checkbox("tools_compress", default_value=0, label="Add compression with -10dB threshold?")
            add_checkbox("tools_resample", default_value=1, label="Resample to 22050 rate?")
            add_checkbox("tools_trimadd", default_value=1, label="Trim audio and pad with silences?")
            add_spacing(count=3)
            add_button("tools_process_wavs", callback=tools_process_wavs_call, label="Process wavs")
            add_spacing(count=3)
            add_label_text("tools_status", label="")
        with tab("tab5", label="Options"):
            add_spacing(count=5)
            add_combo("Themes", items=themes, width=100, default_value="Dark", callback=apply_theme_call)
            add_spacing(count=5)
            add_slider_int("Font Scale", default_value=100, min_value=50, max_value=300, width=200,
                           callback=apply_font_scale_call)

start_dearpygui(primary_window="mainWin")
