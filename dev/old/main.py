import os

from src.download import download_video
from src.extract import extract_notes
from src.score import export_score

url = os.getenv('URL')
print('URL:', url)
max_seconds = int(os.getenv('MAX_SECONDS'))
print('MAX_SECONDS:', max_seconds)
raw_tempo = os.getenv('TEMPO')

# tempo, maxSeconds
# Download the video
dl_res = download_video(url)

print('Downloaded video:', dl_res['title'])
print('Tempo:', dl_res['tempo'])
print('Max seconds:', max_seconds)

if raw_tempo:
    dl_res['tempo'] = int(raw_tempo)

# Extract the notes
notes = extract_notes(dl_res['file_path'], dl_res['tempo'], int(max_seconds))

# Export score
export_score(notes, dl_res['tempo'], dl_res['title'])
