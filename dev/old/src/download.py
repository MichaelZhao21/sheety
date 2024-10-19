import yt_dlp
import requests
import re

def download_video(url: str) -> str:
    ydl_opts = {
        'format': '(bv*[height=1080][fps=60]+ba)/bv*[height=1080][fps=60]+ba/b',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video information
            info_dict = ydl.extract_info(url, download=False)
            
            # Get the title and description
            title = info_dict.get('title', 'Unknown Title')
            description = info_dict.get('description', 'No Description')
            
            # Prepare the file path
            file_path = ydl.prepare_filename(info_dict)
            
            # Download the video
            ydl.download([url])

            # Get the tempo
            mnotes_url = extract_mnotes_url(description)
            print("mnotes_url: ", mnotes_url)
            tempo = 100
            if mnotes_url:
                mnotes_page = get_webpage('https://' + mnotes_url)
                tempo = extract_number(mnotes_page)
                if not tempo:
                    tempo = 100
            
            
            # Return the title, description, and file path
            return {
                'title': title,
                'tempo': tempo,
                'file_path': file_path
            }
    except Exception as e:
        raise Exception(f"An error occurred: {e}")


def extract_number(s):
    match = re.search(r'q.*= (\d+)', s)
    if match:
        return int(match.group(1))
    return None


def extract_mnotes_url(s):
    match = re.search(r'mnot\.es/\w+', s)
    if match:
        return match.group(0)  # Return the full matched string
    return None


def get_webpage(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        return response.text  # Return the content of the response as a string
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None