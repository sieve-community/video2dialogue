""" 
Convert YouTube Video into a Conversational Exchange Between Two Talking Avatars
"""
import sieve

# Helper functions
import subprocess
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

    # Execute the command using subprocess.run
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Re-encoded: {input_path} -> {output_path}")
        print(result.stdout)  # Optionally print the standard output
    except subprocess.CalledProcessError as e:
        print("Error occurred while merging videos.")
        print(e.stderr)  # Optionally print the error message

def merge_videos(video_list,output_path):
    """
    Merge videos listed in the video_list_file into a single video.
    """
    # Write video list (filenames) to a text file for concatenation
    with open('video_list_file.txt', 'w') as f:
        for video in video_list:
            f.write(f"file '{video}'\n")
    
    # Concatenate the videos
    command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", "video_list_file.txt",
        "-loglevel", "warning",
        "-c", "copy",
        output_path     
    ]
    
    # Execute the command using subprocess.run
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Merge successful!")
        print(result.stdout)  # Optionally print the standard output
    except subprocess.CalledProcessError as e:
        print("Error occurred while merging videos.")
        print(e.stderr)  # Optionally print the error message
        
@sieve.function(
    name="video2dialogue",
    python_packages=[
        "numpy>=1.19.0",
    ],
    system_packages=["ffmpeg"],
)

def video2dialogue(youtube_url,voice1, voice2, image1 : sieve.File, image2: sieve.File):
    """
    :param youtube_url: url of the youtube video
    :param voice1: voice for speaker1 (choose a non-cloning voice compatible with sieve-tts. See sieve/tts readme.) 
    :param voice2: voice for speaker2 (choose a non-cloning voice compatible with sieve-tts. See sieve/tts readme.) 
    :param image1: input image for the avatar corresponding to speaker1.
    :param image2: input image for the avatar corresponding to speaker2.
    :return: The video featuring two avatars conversing, providing a summary of the YouTube video.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # use remote Sieve functions
    youtube_to_mp4 = sieve.function.get("sieve/youtube_to_mp4")
    visual_summarizer = sieve.function.get("sieve/visual-qa")
    tts = sieve.function.get("sieve/tts")
    portrait_avatar = sieve.function.get("sieve/portrait-avatar")

    # Step1: Download youtube video of given url
    print("downloading youtube video...")
    resolution = "highest-available"
    include_audio = True
    youtube_video = youtube_to_mp4.run(youtube_url, resolution, include_audio)
    print("done downloading!")
    
    # Step 2. Summarize video into conversational style between 2 people
    print("Summarizing video...")
    backend = "gemini-1.5-flash" #for more complex tasks use "gemini-1.5-pro"
    prompt = "Summarize the video into a conversation between two people. Denote first speaker as 'Person 1' and second speaker as 'Person 2'."
    fps = 1
    audio_context = True
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
    summary_as_conversation = visual_summarizer.run(youtube_video, backend, prompt, fps, audio_context,function_json)
    print("Summary: \n", summary_as_conversation)
    
    # Step 3. Convert each conversation-turn's text to speech & generate its talking avatar.
    # tts inputs:
    print("generating tts audio and its avatar video...")
    reference_audio = sieve.File(url="") #not passing this argument results throws error.
    
    turn = 0
    normalized_videos = []
    turn_results = {}  # Dictionary to store normalized videos by turn

   # ThreadPoolExecutor for concurrent execution
    with ThreadPoolExecutor() as executor:
        # List to keep track of all submitted jobs
        future_to_turn = {}

        # Submit TTS and avatar generation jobs
        for entry in summary_as_conversation:
            turn += 1
            if turn % 2 != 0:  # Odd-turn of conversation
                target_audio_future = tts.push(voice1, entry['dialogue'], reference_audio, "curiosity")
                avatar_video_future = portrait_avatar.push(
                    source_image=image1, 
                    driving_audio=target_audio_future.result(), 
                    aspect_ratio="1:1"
                )
            else:  # Even-turn
                target_audio_future = tts.push(voice2, entry['dialogue'], reference_audio, "curiosity")
                avatar_video_future = portrait_avatar.push(
                    source_image=image2, 
                    driving_audio=target_audio_future.result(), 
                    aspect_ratio="1:1"
                )

            # Store the avatar video future and turn in a dictionary for tracking
            future_to_turn[avatar_video_future] = turn

        # Process avatar generation results as they complete
        for future in as_completed(future_to_turn):
            turn = future_to_turn[future]
            try:
                avatar_video = future.result()  # Wait for the avatar video to complete
                print(f"Done TTS and avatar generation for turn-{turn}")
                
                # Re-encode the video
                normalized_video = f"normalized_{turn}.mp4"
                reencode_video(avatar_video.path, normalized_video)
                
                # Store normalized video path in a dictionary
                turn_results[turn] = normalized_video
            except Exception as e:
                print(f"Error processing turn-{turn}: {e}")
    
    # Append normalized videos to the list in the sequential order of turns
    for turn in sorted(turn_results.keys()):
        normalized_videos.append(turn_results[turn])
        
    print("done generating video avatars for all individual conversation turns!")
    
    # Step 5: Merge generated avatar videos 
    output_path = 'output_avatar_video.mp4'
    merge_videos(normalized_videos, output_path)
    print('done merging individual avatar videos!')
    output_video = sieve.File(output_path)
    return output_video

if __name__ == "__main__":
    youtube_url = "https://youtube.com/shorts/D-F32ieZ4WA?si=X7QzBXMEuJM6d-E4"
    odd_voice = "cartesia-commercial-man"
    even_voice = "cartesia-sweet-lady"
    odd_image = sieve.File('boy_cropped.jpeg')
    even_image = sieve.File('girl_cropped.jpeg')
    output_video = video2dialogue(youtube_url,odd_voice,even_voice,odd_image,even_image)