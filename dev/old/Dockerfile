FROM python:3.13-bookworm
WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 lilypond -y

RUN pip install setuptools
RUN pip install -r requirements.txt

CMD ["python", "main.py"]
