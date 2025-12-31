import whisper
import os
import datetime
import yt_dlp

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def download_youtube_audio(url):
    print(f"⬇️  Downloading audio from YouTube: {url}...")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return "temp_audio.mp3"

def group_segments(segments, chunk_duration=30):
    """
    Merges tiny Whisper segments into bigger blocks (default 30 seconds).
    This gives the AI enough context to actually understand the topic.
    """
    grouped = []
    current_text = ""
    current_start = segments[0]["start"]
    
    for seg in segments:
        # Add text to current chunk
        current_text += seg["text"] + " "
        
 
        if seg["end"] - current_start >= chunk_duration:
            grouped.append({
                "start": format_timestamp(current_start),
                "end": format_timestamp(seg["end"]),
                "text": current_text.strip()
            })
            
            current_text = ""
            current_start = seg["end"]
            
  
    if current_text:
        grouped.append({
            "start": format_timestamp(current_start),
            "end": format_timestamp(segments[-1]["end"]),
            "text": current_text.strip()
        })
        
    return grouped

def process_source(source_path_or_url):
    if "youtube.com" in source_path_or_url or "youtu.be" in source_path_or_url:
        audio_file = download_youtube_audio(source_path_or_url)
    else:
        if not os.path.exists(source_path_or_url):
            print(f"❌ Error: File '{source_path_or_url}' not found.")
            return None
        audio_file = source_path_or_url

    print("🔄 Loading Whisper Model...")
    model = whisper.load_model("base") 
    
    print(f"🎧 Transcribing '{audio_file}'...")
    result = model.transcribe(audio_file)
    

    print("🧩 Grouping segments into 30-second chunks for better search...")
    raw_segments = result["segments"]
    cleaned_segments = group_segments(raw_segments)
    
    print(f"✅ Processing Complete! Created {len(cleaned_segments)} searchable chunks.\n")
    
  
    if cleaned_segments:
        print(f"Sample Chunk 1: [{cleaned_segments[0]['start']} -> {cleaned_segments[0]['end']}]")
        print(f"Text: {cleaned_segments[0]['text'][:100]}...") 

    if source_path_or_url.startswith("http") and os.path.exists("temp_audio.mp3"):
        os.remove("temp_audio.mp3")
        
    return cleaned_segments