""" 
Convert YouTube Video into a Conversational Exchange Between Two Talking Avatars
"""
import sieve

# Helper functions
def conversation_to_list(conversation_text):
    """
    Convert conversation text to a list, 
    with each turn of the conversation as an item in the list.
    """
    # Split the text by newline character
    conversation_list = conversation_text.split('\n')
    # Remove empty strings from the list
    conversation_list = [line for line in conversation_list if line.strip()]

    # Get a list of dialogues with each item as a tuple of format (speaker_id,text).
    processed_conversation = []
    for line in conversation_list:
        if line.startswith("Person 1:"):
            speaker = "Person 1"
            text = line.replace("Person 1:", "").strip()
        elif line.startswith("Person 2:"):
            speaker = "Person 2"
            text = line.replace("Person 2:", "").strip()
        else:
            # Find the position of the first colon
            colon_index = line.find(":")
            # If a colon is found, return the content after it
            if colon_index != -1:
                text = line[colon_index + 1:].strip()
                speaker = line[:colon_index]
            else: # If no colon is found, return the entire sentence
                speaker = "Unknown"
                text = line.strip()
        processed_conversation.append((speaker, text))
    
    return processed_conversation 

import subprocess
def reencode_video(input_path, output_path):
    """
    Re-encode a video to normalize codec properties.
    """
    command = [
        "ffmpeg",
        "-loglevel", "warning",
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
    summary_as_conversation = visual_summarizer.run(youtube_video, backend, prompt, fps, audio_context)
    print("Summary: \n", summary_as_conversation)
    
    # Step 3. Obtain conversation text as list
    summary_conversation_list = conversation_to_list(summary_as_conversation)
    print('Processed Conversation list:\n ',summary_conversation_list)
    
    # Step 4. Convert each conversation-turn's text to speech & generate its talking avatar.
    # tts inputs:
    print("generating tts audio and its avatar video...")
    reference_audio = sieve.File(url="") #not passing this argument results throws error.
    
    turn = 0
    normalized_videos = []
    for speaker, text in summary_conversation_list:
        turn += 1
        if turn % 2 != 0: # odd-turn of conversation
            target_audio = tts.run(voice1, text,reference_audio,"curiosity")
            avatar_video = portrait_avatar.run(source_image=image1, driving_audio=target_audio,aspect_ratio = "16:9")
            print(f'odd turn: done tts and avatar generation for turn-{turn}')
        else: #even-turn
            target_audio = tts.run(voice2, text, reference_audio,"curiosity")
            avatar_video = portrait_avatar.run(source_image=image2, driving_audio=target_audio,aspect_ratio = "16:9")
            print(f'even turn: done tts and avatar generation for turn-{turn}')
        #Encode generated video to ensure same frame rate, video codec, audio codec and similar video quality.
        normalized_video = f"normalized_{turn}.mp4"
        reencode_video(avatar_video.path, normalized_video)
        normalized_videos.append(normalized_video)
    print("done generating video avatars for all individual conversation turns!")
    
    # Step 5: Merge generated avatar videos 
    output_path = 'output_avatar_video.mp4'
    merge_videos(normalized_videos, output_path)
    print('done merging individual avatar videos!')
    output_video = sieve.File(output_path)
    return output_video

if __name__ == "__main__":
    # output_path = "energyClams_avatar_video.mp4"  
    youtube_url = "https://youtube.com/shorts/D-F32ieZ4WA?si=X7QzBXMEuJM6d-E4"
    odd_voice = "cartesia-commercial-man"
    even_voice = "cartesia-sweet-lady"
    odd_image = sieve.File(url="https://storage.googleapis.com/sieve-prod-us-central1-public-file-upload-bucket/c4d968f5-f25a-412b-9102-5b6ab6dafcb4/342623d3-10ce-4f43-8c2d-d445639225ac-boy.jpeg")
    even_image = sieve.File(url="https://storage.googleapis.com/sieve-prod-us-central1-public-file-upload-bucket/dea37047-9b88-44b7-aacb-a5f4745f1f2d/db7a439e-24f8-40cd-b29d-43935e1a2ae7-input-source_image.jpg")

    output_video = video2dialogue(youtube_url,odd_voice,even_voice,odd_image,even_image)
