import audioop
import math

from pydub.utils import ratio_to_db


def _generate_loudness_segments(wav, segment_size):
    length = len(wav)
    search_index = 0
    segment_loudnesses = []
    while search_index + segment_size < length:
        segment = wav[search_index:search_index + segment_size]
        rms = audioop.rms(segment.raw_data, segment.sample_width)

        # rms = db_to_float(loudness) * wav.max_possible_amplitude
        loudness = ratio_to_db(rms / wav.max_possible_amplitude)
        loudness = max(loudness, -1000)  # avoid negative infinity values

        segment_loudnesses.append(loudness)
        search_index += segment_size
    return segment_loudnesses


def _is_silent_slice(segs, silent_threshold):
    for seg_loudness in segs:
        if seg_loudness > silent_threshold:
            return False
    return True


def _find_next_silence(loudnesses, start_index, end_index, preferred_silent_segments, min_silent_segments,
                       silent_threshold):
    if preferred_silent_segments < min_silent_segments:
        return None

    # print(silent_threshold)
    while True:
        # find next silence with preferred_silent_segments
        silence_start_index = start_index
        while silence_start_index + preferred_silent_segments <= end_index:
            current_seg = loudnesses[silence_start_index:silence_start_index + preferred_silent_segments]
            # print(preferred_silent_segments, len(current_seg))
            if _is_silent_slice(current_seg, silent_threshold):
                break
            silence_start_index += 1
        else:
            # if no silence_start_index was found -> recursively reduce preferred_silent_segments until one is found
            return _find_next_silence(loudnesses, start_index, end_index, preferred_silent_segments - 1,
                                      min_silent_segments, silent_threshold)
        return silence_start_index


def _find_slice_end(loudnesses, start_index, end_index, preferred_silent_segments, min_silent_segments,
                    silent_threshold):
    # increase silence_threshold until silence could be found
    while True:
        silence_start_index = _find_next_silence(loudnesses, start_index, end_index, preferred_silent_segments,
                                                 min_silent_segments, silent_threshold)
        if silence_start_index:
            return silence_start_index
        silent_threshold += 5


def speed_slice(wav, segment_size=25, min_segments_in_slice=round(1000/25), max_segments_in_slice=round(12000/25), preferred_silent_segments=10,
                min_silent_segments=1, silent_threshold=-45, padding_start=0, padding_end=0):

    print("Slicing audio...")
    # generate list with loudnesses of segments
    segment_loudnesses = _generate_loudness_segments(wav, segment_size)
    number_segments = len(segment_loudnesses)

    # slice segments
    slices = []
    search_index = 0
    while search_index + min_segments_in_slice < number_segments:
        segment_start_index = search_index
        search_index += min_segments_in_slice
        silence_start_index = _find_slice_end(segment_loudnesses, search_index,
                                              search_index + max_segments_in_slice - min_segments_in_slice,
                                              preferred_silent_segments, min_silent_segments, silent_threshold)
        new_slice_start = segment_start_index * segment_size - padding_start
        new_slice_end = silence_start_index * segment_size + padding_end
        new_slice = wav[new_slice_start:new_slice_end]
        slices.append(new_slice)
        # slices.append((segment_start_index * segment_size, silence_start_index * segment_size))

        # set next search_index to next non-silent index
        while silence_start_index < number_segments and segment_loudnesses[silence_start_index] < silent_threshold:
            silence_start_index += 1
        search_index = silence_start_index
    print(f"Generated {len(slices)} wavs")
    total_length = sum(len(s) for s in slices) / 1000
    total_min = math.floor(total_length / 60)
    total_sec = round(total_length - total_min * 60)
    print(f"Total length: {total_min}min {total_sec}sec")
    original_length = len(wav) / 1000
    original_min = math.floor(original_length / 60)
    original_sec = round(original_length - original_min * 60)
    print(f"Original length: {original_min}min {original_sec}sec")
    return slices
