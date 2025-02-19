import os
import requests
import whisper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import subprocess
from google.cloud import firestore
import tempfile  # Import tempfile module for cross-platform temp directory

# Initialize Firestore client
db = firestore.Client()

def scrape_voice_lines(character_url, collection_name):
    response = requests.get(character_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    voice_entries = soup.select("table.wikitable tr")
    print(f"Found {len(voice_entries)} voice lines. Starting download...")

    model = whisper.load_model("base")  
    temp_dir = tempfile.gettempdir()  # Get the system's temporary directory

    for i, row in enumerate(voice_entries, start=1):
        audio_elem = row.select_one("audio[src]")
        text_elem = row.find_previous("th")

        if not audio_elem or not text_elem:
            continue  

        text = text_elem.text.strip()
        audio_url = urljoin(character_url, audio_elem["src"])  
        audio_filename = f"{collection_name}{i:04d}.ogg"
        temp_audio_path = os.path.join(temp_dir, audio_filename)  # Use temp_dir

        # Download the audio file
        with requests.get(audio_url, stream=True) as r:
            with open(temp_audio_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)

        wav_filename = audio_filename.replace(".ogg", ".wav")
        wav_path = os.path.join(temp_dir, wav_filename)  # Use temp_dir
        subprocess.run(["ffmpeg", "-i", temp_audio_path, "-ar", "22050", wav_path, "-y"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(temp_audio_path)

        # Transcribe the audio
        transcription = model.transcribe(wav_path)["text"].strip()

        # Save metadata to Firestore
        doc_ref = db.collection("character_voice_lines").document(f"{collection_name}_{i}")
        doc_ref.set({
            "character": collection_name,
            "audio_url": audio_url,
            "wav_filename": wav_filename,
            "transcription": transcription
        })

        print(f"Processed {i}/{len(voice_entries)}: {wav_filename} and uploaded to Firestore.") 

    print("All voice lines processed and stored in Firestore.")

character_name = "MARCH_7TH"
character_url = "https://honkai-star-rail.fandom.com/wiki/March_7th/Voice-Overs"

scrape_voice_lines(character_url, character_name)
