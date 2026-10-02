import yt_dlp as youtube_dl
import asyncio
import aiohttp
import urllib.parse

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -probesize 16M -analyzeduration 0',
    'options': '-vn -filter:a "volume=1.0"'
}

ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

class YouTubeStreamer:
    @staticmethod
    async def get_stream(search_query: str, loop=None):
        loop = loop or asyncio.get_event_loop()
        encoded_search = urllib.parse.quote(search_query)
        invidious_instances = [
            "https://inv.id.my",
            "https://invidious.nerdvpn.de",
            "https://vid.puffyan.us"
        ]
        
        audio_url = None
        song_title = search_query
        
        async with aiohttp.ClientSession() as session:
            for instance in invidious_instances:
                try:
                    async with session.get(f"{instance}/api/v1/search?q={encoded_search}&type=video", timeout=3) as resp:
                        if resp.status == 200:
                            results = await resp.json()
                            if results and len(results) > 0:
                                video_id = results[0]['videoId']
                                song_title = results[0]['title']
                                async with session.get(f"{instance}/api/v1/videos/{video_id}", timeout=3) as vid_resp:
                                    if vid_resp.status == 200:
                                        vid_data = await vid_resp.json()
                                        adaptive = vid_data.get('adaptiveFormats', [])
                                        audio_formats = [f for f in adaptive if 'audio' in f.get('type', '')]
                                        if audio_formats:
                                            audio_url = audio_formats[0]['url']
                                            break
                except Exception:
                    continue

        if not audio_url:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search_query}", download=False))
            if 'entries' in data and data['entries']:
                data = data['entries'][0]
                audio_url = data.get('url')
                song_title = data.get('title', search_query)

        if not audio_url:
            raise Exception("Audio stream unavailable.")

        return audio_url, song_title, FFMPEG_OPTIONS
