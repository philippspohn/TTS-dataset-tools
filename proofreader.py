import datetime
from pathlib import Path

import numpy
import simpleaudio as sa
from dearpygui.core import *
from pydub import AudioSegment
import time


def current_milli_time():
    return round(time.time() * 1000)


class Proofreader:
    def __init__(self):
        self.current = None
        self.current_point = None
        self.current_plot_point = None
        self.current_p = None
        self.next = None
        self.cut = None
        self.next_point = None
        self.next_plot_point = None
        self.next_p = None
        self.selected_row = 0
        self.num_items = 0
        self.activated = False
        self.fname = None
        self.drag_in_current = None
        self.drag_in_next = None
        self.drag_out_current = None
        self.drag_out_next = None
        self.selection_range_current = [None, None]
        self.selection_range_next = [None, None]

        self.started_playing = 0
        self.playing_current = True
        self.total_length = 0
        self.play_in = 0
        self.play_out = 0

    def is_playing(self):
        return self.started_playing + self.get_play_duration() > current_milli_time()

    def is_current_playing(self):
        return self.playing_current

    def set_current_playing(self, value):
        self.playing_current = value

    def get_playing_time(self):
        return current_milli_time() - self.started_playing

    def get_playing_total_time(self):
        return self.total_length

    def get_play_in(self):
        return self.play_in

    def get_play_out(self):
        return self.play_out

    def get_play_duration(self):
        return self.play_out - self.play_in

    def set_filename(self, fname):
        self.fname = fname

    def get_filename(self):
        return self.fname

    def set_activated(self, value):
        self.activated = value

    def is_activated(self):
        return self.activated

    def autosave(self):
        if self.get_current() == None:
            return

        newline = ""
        with open("{}/{}".format(self.get_project_path(), "autosave.csv"), 'w') as csv_file:
            table = get_table_data("table_proofread")
            for row in table:
                csv_file.write("{}{}|{}".format(newline, row[0], row[1]))
                newline = "\n"
        set_value("proofread_status", "{}/{} saved".format(self.get_project_path(), "autosave.csv"))

        with open("{}/logfile.txt".format(self.get_project_path()), 'a') as log_file:
            t = datetime.datetime.now()
            tt = t.strftime("%c")
            row = self.get_selected_row()
            last_wav = get_table_item("table_proofread", row, 0)
            log_file.write("\n{}: Saved {} Last item selected: {}".format(tt, "autosave.csv", last_wav))

            # save_csv_proofread_call("", "autosave")
        print("autosaving to {}".format(self.get_project_path() + "/autosave.csv"))

    def scroll_up(self):
        if is_item_active("current_input_text") or is_item_active("next_input_text"):
            return
        row = self.get_selected_row()
        if row == 0:
            return
        if self.get_current() == None:
            return

        # update playhead
        if not self.is_current_playing():
            self.stop()
        else:
            self.set_current_playing(False)

        # save lost row wav
        self.save_next()

        row = row - 1
        self.set_selected_row(row)
        current_path = get_table_item("table_proofread", row, 0)
        next_path = get_table_item("table_proofread", row + 1, 0)

        current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
        next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))

        set_value("current_input_text", get_table_item("table_proofread", row, 1))
        set_value("next_input_text", get_table_item("table_proofread", row + 1, 1))
        add_data("current_path", current_path)
        add_data("next_path", next_path)

        self.set_current(current_wav)
        self.set_next(next_wav)
        self.plot_wavs()

    def scroll_down(self):
        if is_item_active("current_input_text") or is_item_active("next_input_text"):
            return
        row = self.get_selected_row()
        if self.get_num_items() <= (row + 2):
            return
        if self.get_current() == None:
            return

        # update playhead
        if self.is_current_playing():
            self.stop()
        else:
            self.set_current_playing(True)

        # save lost row wav
        self.save_current()

        row = row + 1
        self.set_selected_row(row)
        current_path = get_table_item("table_proofread", row, 0)
        next_path = get_table_item("table_proofread", row + 1, 0)

        current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
        next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))

        set_value("current_input_text", get_table_item("table_proofread", row, 1))
        set_value("next_input_text", get_table_item("table_proofread", row + 1, 1))
        add_data("current_path", current_path)
        add_data("next_path", next_path)

        self.set_current(current_wav)
        self.set_next(next_wav)
        self.plot_wavs()

    def set_num_items(self, data):
        self.num_items = data

    def get_num_items(self):
        return self.num_items

    def play(self, data, playing_current, in_point=0, out_point=None):
        wav = data
        sa.play_buffer(
            wav.raw_data,
            num_channels=wav.channels,
            bytes_per_sample=wav.sample_width,
            sample_rate=wav.frame_rate
        )
        self.started_playing = current_milli_time()
        self.set_current_playing(playing_current)
        self.play_in = in_point
        self.play_out = in_point + len(wav) if out_point is None else out_point
        if playing_current:
            self.total_length = len(self.get_current())
        else:
            self.total_length = len(self.get_next())

    def stop(self):
        sa.stop_all()
        self.started_playing = 0

    def set_selected_row(self, row):
        self.selected_row = row

    def get_selected_row(self):
        return self.selected_row

    def set_rate(self, rate):
        self.rate = int(rate)

    def get_rate(self):
        return self.rate

    def set_current_point(self, point):
        self.current_point = point

    def get_current_point(self):
        return self.current_point

    def set_next_point(self, point):
        self.next_point = point

    def get_next_point(self):
        return self.next_point

    def set_current(self, wav):
        self.current = wav

    def set_next(self, wav):
        self.next = wav

    def get_current(self):
        return self.current

    def get_next(self):
        return self.next

    def set_project_path(self, path):
        self.project_path = path

    def get_project_path(self):
        return self.project_path

    def save_current(self):
        w = self.get_current()
        if w == None:
            return
        row = self.get_selected_row()
        path = Path(get_table_item("table_proofread", row, 0))
        w.export("{}/wavs/{}".format(self.get_project_path(), path.name), format="wav")
        set_value("proofread_status", "{} saved".format(path.name))

    def save_next(self):
        w = self.get_next()
        if w == None:
            return
        row = self.get_selected_row()
        path = Path(get_table_item("table_proofread", row + 1, 0))
        w.export("{}/wavs/{}".format(self.get_project_path(), path.name), format="wav")
        set_value("proofread_status", "{} saved".format(path.name))

    def plot_wavs(self):
        audio1 = self.current.get_array_of_samples()
        current_int16 = numpy.frombuffer(audio1, dtype=numpy.int16)
        current_float32 = list(current_int16.astype(numpy.float32))

        audio2 = self.next.get_array_of_samples()
        next_int16 = numpy.frombuffer(audio2, dtype=numpy.int16)
        next_float32 = list(next_int16.astype(numpy.float32))

        next_polyline = []

        clear_drawing("current_plot_drawing_new")
        clear_drawing("next_plot_drawing_new")

        x_step = float(len(current_float32) / 1200)
        y_max = max(current_float32)
        x_step_count = 0
        c = 0

        for i in range(0, len(current_float32)):
            if (i >= x_step_count):
                # Draw vertical bars method
                y_axis_val = (current_float32[i] / y_max) * 100
                draw_line("current_plot_drawing_new", [c, 100], [c, y_axis_val + 100], [222, 44, 255, 255], 2)
                c += 1
                x_step_count += x_step

        x_step = float(len(next_float32) / 1200)
        y_max = max(next_float32)
        x_step_count = 0
        c = 0
        for i in range(0, len(next_float32)):
            if (i >= x_step_count):
                y_axis_val = (next_float32[i] / y_max) * 100
                draw_line("next_plot_drawing_new", [c, 100], [c, y_axis_val + 100], [222, 44, 255, 255], 2)
                c += 1
                x_step_count += x_step

        draw_text("current_plot_drawing_new", [10, 175], get_data("current_path"), size=20)
        draw_polyline("next_plot_drawing_new", next_polyline, [255, 255, 0, 255], thickness=3)
        draw_text("next_plot_drawing_new", [10, 175], get_data("next_path"), size=20)

    def draw_selector(self, drawing_name, x_axis):
        delete_draw_command("current_plot_drawing_new", 'selector')
        delete_draw_command("next_plot_drawing_new", 'selector')

        draw_line(drawing_name, [x_axis, 0], [x_axis, 200], [0, 0, 255, 255], 3, tag='selector')

    def clear_playerhead(self):
        delete_draw_command("current_plot_drawing_new", 'playhead')
        delete_draw_command("next_plot_drawing_new", 'playhead')

    def draw_playhead(self, drawing_name, x_axis):
        delete_draw_command("current_plot_drawing_new", 'playhead')
        delete_draw_command("next_plot_drawing_new", 'playhead')

        draw_line(drawing_name, [x_axis, 0], [x_axis, 200], [0xFF, 0x88, 0, 80], 3, tag='playhead')

    def draw_dragbox(self, drawing_name, x_axis):
        self.set_next_p(None)
        self.set_current_p(None)
        delete_draw_command("current_plot_drawing_new", 'selector')
        delete_draw_command("current_plot_drawing_new", 'dragbox')
        delete_draw_command("current_plot_drawing_new", 'p_selector')
        delete_draw_command("next_plot_drawing_new", 'selector')
        delete_draw_command("next_plot_drawing_new", 'dragbox')
        delete_draw_command("next_plot_drawing_new", 'p_selector')
        if drawing_name == "current_plot_drawing_new":
            draw_rectangle(drawing_name, [self.drag_in_current, 0], [x_axis, 200], [125, 50, 50, 255],
                           fill=[204, 229, 255, 80], rounding=0, thickness=2.0, tag='dragbox')
        elif drawing_name == "next_plot_drawing_new":
            draw_rectangle(drawing_name, [self.drag_in_next, 0], [x_axis, 200], [125, 50, 50, 255],
                           fill=[204, 229, 255, 80], rounding=0, thickness=2.0, tag='dragbox')

    def draw_p_selection(self, drawing_name, x_axis):
        self.set_selection_range_current(None, None)
        self.set_selection_range_next(None, None)
        delete_draw_command("current_plot_drawing_new", 'selector')
        delete_draw_command("current_plot_drawing_new", 'dragbox')
        delete_draw_command("current_plot_drawing_new", 'p_selector')
        delete_draw_command("next_plot_drawing_new", 'selector')
        delete_draw_command("next_plot_drawing_new", 'dragbox')
        delete_draw_command("next_plot_drawing_new", 'p_selector')
        draw_line(drawing_name, [x_axis, 0], [x_axis, 200], [255, 0, 0, 255], 5, tag='p_selector')

    def play_selection(self):
        self.stop()
        c = self.get_selection_range_current()
        n = self.get_selection_range_next()
        # print(f"play c,n {c}   {n}")
        if c[0] != None:
            w_current = self.get_current()
            num_samples = len(w_current.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_current()
            if abs(drag_in - drag_out) < 5:
                drag_out = num_samples
            if abs(drag_in - drag_out) < 5:
                return
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)
            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000
                wav = w_current[in_point:out_point]

                self.play(wav, True, in_point)

        elif n[0] != None:
            w_next = self.get_next()
            num_samples = len(w_next.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_next()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)
            if out_point - in_point < 5:
                out_point = num_samples
            if out_point - in_point < 5:
                return
            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000
                wav = w_next[in_point:out_point]
                self.play(wav, False, in_point)


    def cut_outside_selction(self):
        c = self.get_selection_range_current()
        n = self.get_selection_range_next()
        # print(f"cut selection {c}  {n}")
        if c[0] != None:
            w_current = self.get_current()
            num_samples = len(w_current.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_current()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_cut = w_current[:in_point] + w_current[out_point:]
                self.set_cut(wav_cut)
                w_current = w_current[in_point:out_point]

                self.set_current(w_current)
                self.set_current_p(None)
                self.set_selection_range_current(None, None)
                self.plot_wavs()
        elif n[0] != None:
            w_next = self.get_next()
            num_samples = len(w_next.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_next()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_cut = w_next[:in_point] + w_next[out_point:]
                self.set_cut(wav_cut)
                w_next = w_next[in_point:out_point]

                self.set_next(w_next)
                self.set_next_p(None)
                self.set_selection_range_next(None, None)
                self.plot_wavs()



    def cut_selection(self):
        c = self.get_selection_range_current()
        n = self.get_selection_range_next()
        # print(f"cut selection {c}  {n}")
        if c[0] != None:
            w_current = self.get_current()
            num_samples = len(w_current.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_current()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_cut = w_current[in_point:out_point]
                self.set_cut(wav_cut)
                w_current = w_current[:in_point] + w_current[out_point:]

                self.set_current(w_current)
                self.set_current_p(None)
                self.set_selection_range_current(None, None)
                self.plot_wavs()
        elif n[0] != None:
            w_next = self.get_next()
            num_samples = len(w_next.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_next()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_cut = w_next[in_point:out_point]
                self.set_cut(wav_cut)
                w_next = w_next[:in_point] + w_next[out_point:]

                self.set_next(w_next)
                self.set_next_p(None)
                self.set_selection_range_next(None, None)
                self.plot_wavs()

    def paste_selection(self):
        c = self.get_current_p()
        n = self.get_next_p()
        if c:
            cut = self.get_cut()
            if not cut:
                return
            w_current = self.get_current()
            if w_current == None:
                return
            num_samples = len(w_current.get_array_of_samples())
            in_point = (c / 1200) * (num_samples / self.get_rate()) * 1000
            w_current = w_current[:in_point] + cut + w_current[in_point:]
            self.set_current(w_current)
            self.set_current_p(None)
            self.set_cut(None)
            self.plot_wavs()

        elif n:
            cut = self.get_cut()
            if not cut:
                return
            w_next = self.get_next()
            if w_next == None:
                return
            num_samples = len(w_next.get_array_of_samples())
            in_point = (n / 1200) * (num_samples / self.get_rate()) * 1000
            w_next = w_next[:in_point] + cut + w_next[in_point:]
            self.set_next(w_next)
            self.set_next_p(None)
            self.set_cut(None)
            self.plot_wavs()

    def current_play(self):
        self.stop()
        wav = self.get_current()
        if wav == None:
            return
        self.play(wav, True)

    def next_play(self):
        self.stop()
        wav = self.get_next()
        if wav == None:
            return
        self.play(wav, False)

    def current_remove(self):
        if self.get_current() == None:
            return
        row = self.get_selected_row()
        current_path = get_table_item("table_proofread", row, 0)
        delete_row("table_proofread", row)
        set_value("proofread_status", "Removed entry {}".format(current_path))
        num_items = self.get_num_items() - 1
        self.set_num_items(num_items)

        if num_items == row + 1:
            # end of data
            current_path = get_table_item("table_proofread", row - 1, 0)
            next_path = get_table_item("table_proofread", row, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row - 1, 1))
            set_value("next_input_text", get_table_item("table_proofread", row, 1))
            self.set_selected_row(row - 1)
        else:
            current_path = get_table_item("table_proofread", row, 0)
            next_path = get_table_item("table_proofread", row + 1, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row, 1))
            set_value("next_input_text", get_table_item("table_proofread", row + 1, 1))

        add_data("current_path", current_path)
        add_data("next_path", next_path)
        self.set_current(current_wav)
        self.set_next(next_wav)
        self.plot_wavs()

    def next_remove(self):
        if self.get_next() == None:
            return
        row = self.get_selected_row()
        next_path = get_table_item("table_proofread", row + 1, 0)
        delete_row("table_proofread", row + 1)
        set_value("proofread_status", "Removed entry {}".format(next_path))
        num_items = self.get_num_items() - 1
        self.set_num_items(num_items)

        if num_items == row + 1:
            # end of data
            current_path = get_table_item("table_proofread", row - 1, 0)
            next_path = get_table_item("table_proofread", row, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row - 1, 1))
            set_value("next_input_text", get_table_item("table_proofread", row, 1))
            self.set_selected_row(row - 1)
        else:
            current_path = get_table_item("table_proofread", row, 0)
            next_path = get_table_item("table_proofread", row + 1, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row, 1))
            set_value("next_input_text", get_table_item("table_proofread", row + 1, 1))

        add_data("current_path", current_path)
        add_data("next_path", next_path)
        self.set_current(current_wav)
        self.set_next(next_wav)
        self.plot_wavs()

    def table_row_selected(self):
        index = get_table_selections("table_proofread")
        row = index[0][0]
        col = index[0][1]
        set_table_selection("table_proofread", row, col, False)

        if self.get_num_items() == row + 1:
            # clicked end of data
            current_path = get_table_item("table_proofread", row - 1, 0)
            next_path = get_table_item("table_proofread", row, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row - 1, 1))
            set_value("next_input_text", get_table_item("table_proofread", row, 1))
            self.set_selected_row(row - 1)

        else:
            current_path = get_table_item("table_proofread", row, 0)
            next_path = get_table_item("table_proofread", row + 1, 0)
            current_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), current_path))
            next_wav = AudioSegment.from_wav("{}/{}".format(self.get_project_path(), next_path))
            set_value("current_input_text", get_table_item("table_proofread", row, 1))
            set_value("next_input_text", get_table_item("table_proofread", row + 1, 1))
            self.set_selected_row(row)

        add_data("current_path", current_path)
        add_data("next_path", next_path)
        self.set_current(current_wav)
        self.set_next(next_wav)
        self.plot_wavs()

    def save_csv_proofread(self):
        if self.get_current() == None:
            return
        name = self.get_filename()
        if name:
            newline = ""
            with open("{}/{}".format(self.get_project_path(), name), 'w') as csv_file:
                table = get_table_data("table_proofread")
                for row in table:
                    csv_file.write("{}{}|{}".format(newline, row[0], row[1]))
                    newline = "\n"
            set_value("proofread_status", "{}/{} saved".format(self.get_project_path(), name))
            # logging
            with open("{}/logfile.txt".format(self.get_project_path()), 'a') as log_file:
                t = datetime.datetime.now()
                tt = t.strftime("%c")
                row = self.get_selected_row()
                last_wav = get_table_item("table_proofread", row, 0)
                log_file.write("\n{}: Saved {} Last item selected: {}".format(tt, name, last_wav))

    def silence_selection(self):
        c = self.get_selection_range_current()
        n = self.get_selection_range_next()
        if c[0] != None:
            w_current = self.get_current()
            num_samples = len(w_current.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_current()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_silent_region = w_current[in_point:out_point]
                w_current = w_current[:in_point] + AudioSegment.silent(
                    duration=(wav_silent_region.duration_seconds * 1000)) + w_current[out_point:]

                self.set_current(w_current)
                self.set_current_p(None)
                self.set_selection_range_current(None, None)
                self.plot_wavs()
        elif n[0] != None:
            w_next = self.get_next()
            num_samples = len(w_next.get_array_of_samples())
            drag_in, drag_out = self.get_selection_range_next()
            points = [drag_in, drag_out]
            in_point = min(points)
            out_point = max(points)

            if in_point != None and out_point != None:
                in_point = (in_point / 1200) * (num_samples / self.get_rate()) * 1000
                out_point = (out_point / 1200) * (num_samples / self.get_rate()) * 1000

                wav_silent_region = w_next[in_point:out_point]
                w_next = w_next[:in_point] + AudioSegment.silent(
                    duration=(wav_silent_region.duration_seconds * 1000)) + w_next[out_point:]

                self.set_next(w_next)
                self.set_next_p(None)
                self.set_selection_range_next(None, None)
                self.plot_wavs()

    def set_drag_in_current(self, x_axis):
        self.drag_in_current = x_axis

    def get_drag_in_current(self):
        return self.drag_in_current

    def set_drag_in_next(self, x_axis):
        self.drag_in_next = x_axis

    def get_drag_in_next(self):
        return self.drag_in_next

    def set_drag_out_current(self, x_axis):
        self.drag_out_current = x_axis

    def get_drag_out_current(self):
        return self.drag_out_current

    def set_drag_out_next(self, x_axis):
        self.drag_out_next = x_axis

    def get_drag_out_next(self):
        return self.drag_out_next

    def set_selection_range_current(self, x, y):
        self.selection_range_current[0] = x
        self.selection_range_current[1] = y

    def get_selection_range_current(self):
        return self.selection_range_current[0], self.selection_range_current[1]

    def set_selection_range_next(self, x, y):
        self.selection_range_next[0] = x
        self.selection_range_next[1] = y

    def get_selection_range_next(self):
        return self.selection_range_next[0], self.selection_range_next[1]

    def set_cut(self, cut):
        self.cut = cut

    def get_cut(self):
        return self.cut

    def set_current_p(self, p):
        self.current_p = p

    def get_current_p(self):
        return self.current_p

    def set_next_p(self, p):
        self.next_p = p

    def get_next_p(self):
        return self.next_p
