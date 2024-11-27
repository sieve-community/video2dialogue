# video2dialogue

Transform YouTube Videos into Conversational Avatars with Sieve!

This Sieve pipeline converts a YouTube video into an interactive dialogue between two talking avatars. It consists of the following steps:

* Download YouTube Video with the [youtube_to_mp4](https://sievedata.com/functions/sieve/youtube_to_mp4) Sieve function.
* Summarize the downloaded video into conversational-style text using [visual-qa](https://sievedata.com/functions/sieve/visual-qa) Sieve function (employ suitable prompt).
* Summary text is converted into speech using [tts](https://sievedata.com/functions/sieve/tts) Sieve function.
* Talking avatars are generated with [portrait-avatar](https://sievedata.com/functions/sieve/portrait-avatar) Sieve function.

## Tutorial

A detailed explanation of the pipeline is provided in this [tutorial](https://sievedata.com/blog/transform-youtube-videos-into-notebooklm-like-conversational-avatars-with-sieve-notebooklm-api-guide).

## Options

* `youtube_url`: url of the youtube video
* `voice1` and `voice2`: voice for speakers in the generated dialogue (choose a non-cloning voice compatible with sieve-tts. See [sieve/tts](https://sievedata.com/functions/sieve/tts) readme).
* `image1` and `image2`: Input images for the talking avatars.

## Deploying `video2dialogue` to your own Sieve account

First ensure you have the Sieve Python SDK installed: `pip install sievedata` and set `SIEVE_API_KEY` to your Sieve API key.
You can find your API key at [https://www.sievedata.com/dashboard/settings](https://www.sievedata.com/dashboard/settings).

Then deploy the function to your account:

```bash
git clone https://github.com/sieve-community/video2dialogue
cd video2dialogue
sieve deploy pipeline.py
```

You can now find the function in your Sieve account and call it via API or SDK.
