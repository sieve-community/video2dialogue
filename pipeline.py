import sieve
import subprocess
from typing import Literal

def reencode_video(input_path, output_path):
    """
    Re-encode a video to normalize codec properties.
    """
    command = [
        "ffmpeg",
        "-loglevel", "warning", 
        "-y",  # Overwrite output files without asking
        "-i", input_path,
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        output_path
    ]

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Re-encoded: {input_path} -> {output_path}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error occurred while re-encoding video:")
        print(e.stderr)

def merge_videos(video_list, output_path):
    """
    Merge videos listed in the video_list into a single video.
    """
    # Write video list to a text file for concatenation
    with open('video_list_file.txt', 'w') as f:
        for video in video_list:
            f.write(f"file '{video}'\n")
    
    command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", "video_list_file.txt",
        "-loglevel", "warning",
        "-c", "copy",
        output_path     
    ]
    
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Videos merged successfully")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Error occurred while merging videos:")
        print(e.stderr)
        
@sieve.function(
    name="video2dialogue",
    python_packages=["numpy>=1.19.0"],
    system_packages=["ffmpeg"],
)
def video2dialogue(
    youtube_url: str,
    voice1: Literal["cartesia-commercial-man", "cartesia-sweet-lady"] = "cartesia-commercial-man",
    voice2: Literal["cartesia-commercial-man", "cartesia-sweet-lady"] = "cartesia-sweet-lady",
    image1: sieve.File = sieve.File(url="https://storage.googleapis.com/sieve-public-data/notebooklm-blog/boy_cropped.jpeg"),
    image2: sieve.File = sieve.File(url="https://storage.googleapis.com/sieve-public-data/notebooklm-blog/girl_cropped.jpeg")
):
    """
    Convert a YouTube video into a dialogue between two animated avatars.

    :param youtube_url: URL of the YouTube video
    :param voice1: Voice for speaker 1
    :param voice2: Voice for speaker 2
    :param image1: Input image for the avatar corresponding to speaker1
    :param image2: Input image for the avatar corresponding to speaker2
    :return: Video featuring two avatars conversing, providing a summary of the YouTube video
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Initialize remote Sieve functions
    youtube_to_mp4 = sieve.function.get("sieve/youtube_to_mp4")
    visual_summarizer = sieve.function.get("sieve/visual-qa")
    tts = sieve.function.get("sieve/tts")
    portrait_avatar = sieve.function.get("sieve/portrait-avatar")

    # Step 1: Download YouTube video
    print("Downloading YouTube video...")
    youtube_video = youtube_to_mp4.run(youtube_url, "highest-available", True)
    print("Download complete")
    
    # Step 2: Generate conversational summary
    print("Summarizing video...")
    summary_prompt = "Summarize the video into a conversation between two people. Denote first speaker as 'Person 1' and second speaker as 'Person 2'."
    function_json = {
        "type": "list",
        "items": {
            "type": "object",
            "properties": {
                "speaker_name": {
                    "type": "string",
                    "description": "The speaker name"
                },
                "dialogue": {
                    "type": "string",
                    "description": "dialogue"
                }
            }
        }
    }
    summary_as_conversation = visual_summarizer.run(
        youtube_video, 
        "gemini-1.5-flash",
        summary_prompt,
        fps=1,
        audio_context=True,
        function_json=function_json
    )
    print("Summary generated")
    
    # Step 3: Generate speech and avatar videos for each dialogue turn
    print("Generating speech and avatar videos...")
    reference_audio = sieve.File(url="")  # Required placeholder
    
    avatar_videos = []
    for entry_num, entry in enumerate(summary_as_conversation):
        if entry['speaker_name'] == "Person 1":
            voice = voice1
            image = image1
        elif entry['speaker_name'] == "Person 2":
            voice = voice2
            image = image2
        else:
            raise ValueError(f"Unknown speaker: {entry['speaker_name']}")

        target_audio_future = tts.push(voice, entry['dialogue'], reference_audio, "curiosity")
        avatar_video_future = portrait_avatar.push(
            source_image=image,
            driving_audio=target_audio_future.result(),
            aspect_ratio="1:1"
        )
        avatar_videos.append(avatar_video_future)

    for entry_num, avatar_video_future in enumerate(avatar_videos):
        try:
            avatar_video = avatar_video_future.result()            
            normalized_video = f"normalized_{entry_num}.mp4"
            reencode_video(avatar_video.path, normalized_video)
            avatar_videos[entry_num] = normalized_video
        except Exception as e:
            print(f"Error processing turn {entry_num}: {e}")
            raise e
    
    # Step 4: Merge avatar videos in sequence
    output_path = 'output_avatar_video.mp4'
    merge_videos(avatar_videos, output_path)
    print('Video generation complete')
    
    return sieve.File(output_path)

if __name__ == "__main__":
    youtube_url = "https://youtube.com/shorts/D-F32ieZ4WA?si=X7QzBXMEuJM6d-E4"
    odd_voice = "cartesia-commercial-man"
    even_voice = "cartesia-sweet-lady"
    odd_image = sieve.File('boy_cropped.jpeg')
    even_image = sieve.File('girl_cropped.jpeg')
    output_video = video2dialogue(youtube_url, odd_voice, even_voice, odd_image, even_image)