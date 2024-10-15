from pymusicxml import *
from collections import namedtuple
from music21 import converter
import subprocess
import os

Noted = namedtuple("Noted", ["name", "sharp", "octave", "hand", "start", "end", "duration"])

def split_duration_into_tied_notes(duration):
    # Define the note values for common durations
    note_values = [4, 2, 1, 0.5, 0.25]  # Whole, half, quarter, eighth, sixteenth notes
    tied_notes = []

    while duration > 0:
        for value in note_values:
            # Ensure we only take note values that fit into the remaining duration
            if value <= duration + 1e-9:  # Adding a small epsilon to avoid floating point issues
                tied_notes.append(value)
                duration -= value
                break
        else:
            # This happens if none of the note values fit the remaining duration
            raise ValueError(f"Cannot split duration {duration} into standard note values")

    return tied_notes

def process_notes(part, notes, clef, tempo, no_tempo=False):
    m_number = 1
    max_length = 4
    measure = Measure(number=m_number)
    current_time = 0
    tempo = MetronomeMark(beat_length=1.0, bpm=tempo)
    added_tempo = no_tempo

    # Add the clef to the first measure
    measure.clef = clef
    measure.time_signature = (4,4)

    # Group notes by start time
    notes_by_start = {}
    for note in notes:
        if note.start not in notes_by_start:
            notes_by_start[note.start] = []
        notes_by_start[note.start].append(note)

    # Sort start times
    start_times = sorted(notes_by_start.keys())

    for start_time in start_times:
        current_notes = notes_by_start[start_time]

        # Check if there are multiple notes at the same start time (create chord)
        if len(current_notes) > 1:
            pitches = []
            duration = min(note.duration for note in current_notes)  # Use minimum duration

            for note in current_notes:
                if note.name == "rest":
                    continue  # Skip rest for chords
                alteration = 1 if note.sharp else 0
                pitch = Pitch(step=note.name, octave=note.octave, alteration=alteration)
                pitches.append(pitch)

            # Create chord if we have valid pitches
            if pitches:
                # Consider durations too (split into tied notes)
                tied_durations = split_duration_into_tied_notes(duration)
                for tied_duration in tied_durations:
                    if not added_tempo:
                        chord_to_add = Chord(pitches=pitches, duration=tied_duration, directions=tempo)
                        added_tempo = True
                    else:
                        chord_to_add = Chord(pitches=pitches, duration=tied_duration)

                    if current_time + tied_duration > max_length:
                        part.append(measure)
                        m_number += 1
                        measure = Measure(number=m_number)
                        current_time = 0

                    measure.append(chord_to_add)
                    current_time += tied_duration

        else:
            # Single note or rest
            note = current_notes[0]

            if note.name == "rest":
                # Add a rest for the given duration
                tied_durations = split_duration_into_tied_notes(note.duration)

                for tied_duration in tied_durations:
                    rest_to_add = Rest(duration=tied_duration)

                    if current_time + tied_duration > max_length:
                        part.append(measure)
                        m_number += 1
                        measure = Measure(number=m_number)
                        current_time = 0

                    measure.append(rest_to_add)
                    current_time += tied_duration

            else:
                # Handle regular notes
                alteration = 1 if note.sharp else 0
                pitch = Pitch(step=note.name, octave=note.octave, alteration=alteration)

                # Split the duration into tied notes if necessary
                tied_durations = split_duration_into_tied_notes(note.duration)

                for tied_duration in tied_durations:
                    if not added_tempo:
                        note_to_add = Note(
                            pitch=pitch,
                            duration=tied_duration,
                            directions=tempo
                        )
                        added_tempo = True
                    else:
                        note_to_add = Note(
                            pitch=pitch,
                            duration=tied_duration
                        )

                    if current_time + tied_duration > max_length:
                        part.append(measure)
                        m_number += 1
                        measure = Measure(number=m_number)
                        current_time = 0

                    measure.append(note_to_add)
                    current_time += tied_duration

        # Check if we need to start a new measure
        if current_time >= max_length:
            part.append(measure)
            m_number += 1
            measure = Measure(number=m_number)
            current_time = 0

    # Append the last measure if it's not empty
    if len(measure) > 0:
        part.append(measure)

# Function to add whole rests to the part with fewer measures
def add_whole_rests_to_equalize_measures(part_with_fewer_measures, part_with_more_measures):
    measures_fewer = len(part_with_fewer_measures)
    measures_more = len(part_with_more_measures)

    # Calculate how many whole rests are needed
    rests_needed = measures_more - measures_fewer

    # Add whole rests to the part with fewer measures
    for _ in range(rests_needed):
        new_measure = Measure(number=len(part_with_fewer_measures) + 1)
        new_rest = Rest(duration=4)  # Whole rest
        new_measure.append(new_rest)
        part_with_fewer_measures.append(new_measure)


def convert_musicxml_to_pdf(musicxml_path, pdf_path, lilypond_path):
    if not os.path.exists(musicxml_path):
        raise FileNotFoundError(f"MusicXML file not found: {musicxml_path}")
    
    if not os.path.exists(lilypond_path):
        raise FileNotFoundError(f"LilyPond executable not found: {lilypond_path}")

    # Convert MusicXML to LilyPond format
    lilypond_file = os.path.splitext(musicxml_path)[0] + ".ly"
    try:
        subprocess.run(['musicxml2ly', musicxml_path, '-o', lilypond_file], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error converting MusicXML to LilyPond format: {e}")

    # Use LilyPond to generate the PDF
    try:
        subprocess.run(['lilypond', lilypond_file], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error generating PDF from LilyPond file: {e}")

    print(f"PDF generated: {pdf_path}")
    return pdf_path
    
    try:
        subprocess.run([lilypond_path, "-N", "-o", pdf_path, musicxml_path], check=True)
        print(f"Successfully converted {musicxml_path} to {pdf_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting MusicXML file to PDF: {e}")


def export_score(Notes, tempo, title):
    # Create a score
    score = Score(title=title.replace(" - Piano Tutorial", ""), composer="Generated by ScoreSnag")

    # Create two parts
    part1 = Part(part_name='P1')
    part1.instrument_name = "Piano"
    part2 = Part(part_name='P2')
    part2.instrument_name = "Piano"

    # Create clefs for part1 and part2
    part1clef = Clef(sign="G", line=2)  # Treble clef for part1
    part2clef = Clef(sign="F", line=4)  # Bass clef for part2

    # Append the parts to the score
    score.append(part1)
    score.append(part2)

    # Separate notes for each hand
    right_hand_notes = [note for note in Notes if note.hand == "R"]
    left_hand_notes = [note for note in Notes if note.hand == "L"]
    
    # Process notes for each part, adding the clef to the first measure
    process_notes(part1, right_hand_notes, part1clef, tempo)
    process_notes(part2, left_hand_notes, part2clef, tempo, True)

    # Check the number of measures and equalize if necessary
    if len(part1) < len(part2):
        add_whole_rests_to_equalize_measures(part1, part2)
    elif len(part1) > len(part2):
        add_whole_rests_to_equalize_measures(part2, part1)

    # TODO: Save to somewhere and have like user things if possible
    musicxml_file = "sheet_music.xml"
    pdf_file = "sheet_music.pdf"
    musescore_executable = "/usr/bin/lilypond"

    # Export the score to a MusicXML file
    score.export_to_file(musicxml_file)

    convert_musicxml_to_pdf(musicxml_file, pdf_file, musescore_executable)
