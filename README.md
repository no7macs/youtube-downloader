# youtube-downloader
downloads all videos from a list of channels or playlists and does some image processing

# prerequisites

- Python 3.8.10 or higher
- [Youtube-dl 2021.12.17](https://github.com/ytdl-org/youtube-dl)
- [ffmpeg 3.0](https://github.com/FFmpeg/FFmpeg)

Both youtube-dl and ffmpeg have to be on the windows path since this invokes them through the commands

# Files
 ## sources.json
   This is a json file that holds all the links you want to download from wheere the key is the sub folder and the string is the link
   ```
   {
    "some sub folder":"a youtube link"
   }
   ```
 ## youtube.com_cookies.txt
  The youtube cookies file, you will need to pull your cookies with [Get Cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid?hl=en) to download anything age restricted          
