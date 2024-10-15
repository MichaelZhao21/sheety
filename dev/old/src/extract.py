import cv2
import numpy as np
import math
import colorsys
from collections import namedtuple

Note = namedtuple("Note", ["name", "sharp", "octave", "hand", "start", "end", "duration"])

fps = 60

def extract_notes(file_path, bpm=100, max_seconds=30):
    vidcap = cv2.VideoCapture(file_path) 

    limit = max_seconds * fps
    final = None

    # Video processing
    count = -1
    rgb_list = [0, 0, 0, 0, 0]

    while count < 1000:
        success, image = vidcap.read()
        if not success:
            raise Exception("Video processing failed")

        count += 1

        px = image[image.shape[0] - 30, 30]
        if np.mean(px) < 100:
            continue
        col = np.mean(px)
        if col == rgb_list[0] and col == rgb_list[1] and col == rgb_list[2] and col == rgb_list[3] and col == rgb_list[4]:
            print("FRAME VIDEO STARTS IS:", count)
            final = image
            break

        rgb_list[0] = rgb_list[1]
        rgb_list[1] = rgb_list[2]
        rgb_list[2] = rgb_list[3]
        rgb_list[3] = rgb_list[4]
        rgb_list[4] = col
    
    if final is None:
        raise Exception("Could not find the start of the video")
    
    # FIGURE OUT WHERE PIANO IS
    col = np.mean(final[10][10])
    i = image.shape[0] // 2
    while abs(np.mean(final[i][10]) - col) < 10:
        i += 1
    print("PIANO TOP AT:", i)

    # Figure out line 2
    off = (image.shape[0] - i) // 3
    y = i + off
    print("PIANO IS AT:", y)

    # Keyboard counting
    indexacross = 0
    trackchanges = []
    colortracker = 0
    indexofchange = 0

    while indexacross < 1920:
        bar = image[890, indexacross]
        indexacross += 1
        averagergbval = np.mean(bar)

        if averagergbval < 150:
            if colortracker != 0:
                indexofchange = indexacross
                trackchanges.append(indexofchange)
                colortracker = 0
        else:
            if colortracker != 1:
                indexofchange = indexacross
                trackchanges.append(indexofchange)
                colortracker = 1
                
    breaks = [(b, i % 2 == 0) for i, b in enumerate(trackchanges)]
    noteas = []
    start = 1

    # Black is False
    for b in breaks:
        if b[0] - start > 10:
            noteas.append(((start, b[0]), 'B' if b[1] else 'W'))
        start = b[0]

    jns = ''.join(map(lambda x: x[1], noteas))
    oct = jns.find('WBWBWWBWBWBW')
    octaves = [noteas[0:oct]]

    while oct < len(jns):
        octaves.append(noteas[oct:oct+12])
        oct += 12

    # Filter out empty octaves
    octaves = list(filter(lambda x: len(x) > 0, octaves))

    lens = list(map(lambda x: len(x), octaves))
    total_octaves = len(lens)
    if lens[0] < 12:
        total_octaves -= 1
    if lens[-1] < 12:
        total_octaves -= 1

    mid_c = math.ceil((total_octaves-1) / 2)
    if lens[0] < 12:
        mid_c += 1

    print("Lengths of octaves:", lens)
    print("Total octaves:", total_octaves)
    print("Middle C octave:", mid_c)

    Key = namedtuple('Key', ['x', 'name', 'sharp', 'octave', 'color'])

    note_map = [
        ('C', False),
        ('C', True),
        ('D', False),
        ('D', True),
        ('E', False),
        ('F', False),
        ('F', True),
        ('G', False),
        ('G', True),
        ('A', False),
        ('A', True),
        ('B', False),
    ]

    keys = []
    for i, o in enumerate(octaves):
        offset = 12 - len(o)
        for j, no in enumerate(o):
            n = note_map[j + offset]
            x = (no[0][0] + no[0][1]) // 2
            keys.append(Key(x, n[0], n[1], 4 - mid_c + i, np.mean(final[y][x])))

    print("Processing all the frames...")
    ColorNote = namedtuple("ColorNote", ["name", "sharp", "octave", "color", "start", "end"])

    cnotes = []
    curr_keys = dict()

    # Iterate through the rest of the frames
    while success and count < limit:
        success, image = vidcap.read()
        if not success:
            break
        count += 1

        # Extract the row from the frame
        # (Key, timeStart, color)
        # Store index of key in the curr_keys set
        new_keys = dict()
        for i, k in enumerate(keys):
            if abs(np.mean(image[y][k.x]) - k.color) > 5:
                new_keys[i] = (count, image[y][k.x])

        # Compute set differernce
        removed = set(curr_keys.keys()) - set(new_keys.keys())

        # Create output notes
        for r in removed:
            k = keys[r]
            cnotes.append(ColorNote(k.name, k.sharp, k.octave, curr_keys[r][1], curr_keys[r][0], count))
            del curr_keys[r]

        # Figure out new keys
        added = set(new_keys.keys()) - set(curr_keys.keys())
        for a in added:
            curr_keys[a] = new_keys[a]

    print("Done! Generating notes...")

    # Sort notes by start
    cnotes.sort(key=lambda x: x.start)

    # Calculate color centers (there should be 2)
    nc = cnotes[0].color
    center_a = colorsys.rgb_to_hsv(nc[2] / 255, nc[1] / 255, nc[0] / 255)[0] * 360

    # Iterate until we hit a different enough color
    for i, n in enumerate(cnotes[1:]):
        nc = n.color
        center_b = colorsys.rgb_to_hsv(nc[2] / 255, nc[1] / 255, nc[0] / 255)[0] * 360
        if abs(center_a - center_b) > 10:
            break

    # Figure out which is LH and RH
    if cnotes[0].octave != cnotes[i+1].octave:
        if cnotes[0].octave > cnotes[i+1].octave:
            center_a, center_b = center_b, center_a
    elif ord(cnotes[0].name) > ord(cnotes[i+1].name):
        center_a, center_b = center_b, center_a

    print("Color Centers:", center_a, center_b)

    def get_hand(col):
        hsv = colorsys.rgb_to_hsv(col[2] / 255, col[1] / 255, col[0] / 255)[0] * 360
        if abs(hsv - center_a) > 10:
            return 'R'
        else:
            return 'L'

    # Map color notes to notes based on the centers
    notes = list(map(lambda x: Note(x.name, x.sharp, x.octave, get_hand(x.color), x.start, x.end, x.end - x.start), cnotes))

    # Figure out where rests go
    left_hands = list(map(lambda x: (x.start, x.end), filter(lambda x: x.hand == 'L', notes)))
    right_hands = list(map(lambda x: (x.start, x.end), filter(lambda x: x.hand == 'R', notes)))

    first = notes[0].start
    last = sorted(notes, key=lambda x: x.end, reverse=True)[0].end

    def merge_ranges(busy_ranges):
        # Step 1: Sort busy ranges by start time
        busy_ranges.sort(key=lambda x: x[0])

        merged = []
        for start, end in busy_ranges:
            if not merged or merged[-1][1] < start:
                # No overlap
                merged.append((start, end))
            else:
                # Merge overlapping or adjacent ranges
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))

        return merged

    def find_available_ranges(busy_ranges, total_start, total_end):
        # Merge the busy ranges
        merged_busy = merge_ranges(busy_ranges)

        available_ranges = []

        # Step 3: Find gaps between merged busy times
        # Start from the beginning of the total time range
        current_time = total_start

        for busy_start, busy_end in merged_busy:
            if current_time < busy_start:
                # If there's a gap, add the available range
                available_ranges.append((current_time, busy_start))
            # Move the current time to the end of the busy range
            current_time = max(current_time, busy_end)

        # Check for a gap after the last busy range
        if current_time < total_end:
            available_ranges.append((current_time, total_end))

        return available_ranges

    # Find ranges
    left_range = find_available_ranges(left_hands, first, last)
    right_range = find_available_ranges(right_hands, first, last)

    # Add all rests
    for lr in left_range:
        notes.append(Note('rest', False, 0, 'L', lr[0], lr[1], lr[1] - lr[0]))

    for rr in right_range:
        notes.append(Note('rest', False, 0, 'R', rr[0], rr[1], rr[1] - rr[0]))

    # Sort notes again
    notes.sort(key=lambda x: x.start)

    MIN_REST_TIME = (fps / (bpm / 60)) / 2
    print("Minimum rest time:", MIN_REST_TIME)

    # AAAAAAA
    # COMBINE THE MOTHER FUCKIN RESTS BRUH
    left_list = list(filter(lambda x: x.hand == 'L', notes))
    right_list = list(filter(lambda x: x.hand == 'R', notes))

    new_left_list = []
    new_right_list = []

    # Remove all rests and increase duration of previous note to extend to the rest
    def combine_rests(note_list):
        new_note_list = []
        prev_note = None

        for note in note_list:
            if note.name == 'rest' and note.duration < MIN_REST_TIME:
                # If it's a rest and shorter than the MIN_REST_TIME, extend the previous note's end
                if prev_note is not None:
                    prev_note = Note(prev_note.name, prev_note.sharp, prev_note.octave, prev_note.hand, prev_note.start, note.end, prev_note.duration + (note.end - prev_note.end))
            else:
                # If the previous note exists (and wasn't a rest), add it to the new list
                if prev_note:
                    new_note_list.append(prev_note)
                prev_note = note  # Update the previous note to the current one

        # Append the last remaining note (which was not added inside the loop)
        if prev_note:
            new_note_list.append(prev_note)

        return new_note_list

    # Process left and right hand note lists
    new_left_list = combine_rests(left_list)
    new_right_list = combine_rests(right_list)

    # Create a new notes list
    notes = new_left_list + new_right_list

    # Sort for another damn time
    notes.sort(key=lambda x: x.start)

    def to_beats(x):
        frame_duration = x.duration / fps
        bps = bpm / 60
        duration_in_beats = frame_duration * bps
        rounded_duration_in_beats = max(round(duration_in_beats * 4) / 4, 0.25)
        return Note(x.name, x.sharp, x.octave, x.hand, x.start, x.end, rounded_duration_in_beats)

    notes = list(map(to_beats, notes))

    print("We have this many notes:", len(notes))

    return notes
