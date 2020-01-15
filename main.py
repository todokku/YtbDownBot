import sys, os
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import youtube_dl as ydl
from urllib import request
import traceback
import subprocess
import m3u8
import asyncio
import typing
import ffmpeg


api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

CHAT_WITH_BOT_ID = int(os.environ['CHAT_WITH_BOT_ID'])

client = TelegramClient(os.environ['TG_CLIENT_SESSION_FILE_NAME'], api_id, api_hash)

video_format = 'best[ext=mp4,height<=1080]+best[ext=mp4,height<=480]/best[ext=mp4,height<=1080]/bestvideo[ext=mp4,height<=1080]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
y = ydl.YoutubeDL({'format': video_format, 'noplaylist': True, 'youtube_include_dash_manifest': False})

TG_MAX_FILE_SIZE = 1500


class DumbReader(typing.BinaryIO):
    def write(self, s: typing.Union[bytes, bytearray]) -> int:
        pass
    def mode(self) -> str:
        pass
    def name(self) -> str:
        pass
    def close(self) -> None:
        pass
    def closed(self) -> bool:
        pass
    def fileno(self) -> int:
        pass
    def flush(self) -> None:
        pass
    def isatty(self) -> bool:
        pass
    def readable(self) -> bool:
        pass
    def readline(self, limit: int = -1) -> typing.AnyStr:
        pass
    def readlines(self, hint: int = -1) -> typing.List[typing.AnyStr]:
        pass
    def seek(self, offset: int, whence: int = 0) -> int:
        pass
    def seekable(self) -> bool:
        pass
    def tell(self) -> int:
        pass
    def truncate(self, size: int = None) -> int:
        pass
    def writable(self) -> bool:
        pass
    def write(self, s: typing.AnyStr) -> int:
        pass
    def writelines(self, lines: typing.List[typing.AnyStr]) -> None:
        pass
    def __enter__(self) -> 'typing.IO[typing.AnyStr]':
        pass
    def __exit__(self, type, value, traceback) -> None:
        pass

class FFMpegVideo(DumbReader):

    def __init__(self, vformat, mformat=None):
        if mformat:
            self.stream = ffmpeg.input(vformat['url'], **{"user-agent": user_agent}).output('pipe:',
                                                                                            format='mp4',
                                                                                            acodec='copy',
                                                                                            vcodec='copy',
                                                                                            movflags='frag_keyframe').global_args('-user-agent', user_agent, '-i', mformat['url'], '-map', '0:v', '-map', '1:a').run_async(pipe_stdout=True)
        else:
            self.stream = ffmpeg.input(vformat['url'], **{"user-agent": user_agent}).output('pipe:',
                                                                                            format='mp4',
                                                                                            vcodec='copy',
                                                                                            acodec='copy',
                                                                                            movflags='frag_keyframe').run_async(pipe_stdout=True)

    def read(self, n: int = -1):
        return self.stream.stdout.read(n)

    def close(self) -> None:
        print('last data ', len(self.stream.stdout.read()))
        self.stream.kill()


def video_info(url, use_m3u8=False):
    if use_m3u8:
        m3u8_obj = m3u8.load(url)
        url = m3u8_obj.segments[0].absolute_uri  # override for mediainfo call
        dur = 0
        for s in m3u8_obj.segments:
            if hasattr(s, 'duration'):
                dur += s.duration

    mi_proc = subprocess.Popen(['mediainfo', '--Inform=Video;%Width%\\n%Height%\\n%Duration%', '2>', '/dev/null', url],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    out = mi_proc.stdout.read()
    out = out.split(b'\n')
    w = int(out[0])
    h = int(out[1])
    if use_m3u8:
        dur = int(dur)
    else:
        dur = int(int(out[2])/1000)


    return w, h, dur

def video_format(url):
    mi_proc = subprocess.Popen(['mediainfo', '--Inform=General;%Format%', '2>', '/dev/null', url],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    out = mi_proc.stdout.read()
    return out.split(b'\n')[0].decode('utf-8')

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3719.5 Safari/537.36'
def video_size(url):
    headers = {'User-Agent': user_agent}
    head_req = request.Request(url, method='HEAD', headers=headers)
    with request.urlopen(head_req) as resp:
        return int(resp.headers['Content-Length'])


def m3u8_video_size(url):
    m3u8_obj = m3u8.load(url)
    size = 0

    for seg in m3u8_obj.segments:
        head_req = request.Request(seg.absolute_uri, method='HEAD')
        with request.urlopen(head_req) as resp:
            size += int(resp.headers['Content-Length'])

    return size

async def main():
    started = int(sys.argv[1])
    chat_and_message_id = str(sys.argv[2])
    urls = str(sys.argv[3]).split(" ")

    if started != 0:
        print("Already started " + str(sys.argv[1:]))
        await client.connect()


    for u in urls:
        try:
            vinfo = y.extract_info(u, download=False)
        except Exception as e:
            if "Please log in or sign up to view this video" in e.__str__():
                if 'vk.com' in u or 'facebook.com' in u:
                    try:
                        yy = ydl.YoutubeDL({'format': video_format, 'noplaylist': True, 'username': os.environ['VIDEO_ACCOUNT_USERNAME'], 'password': os.environ['VIDEO_ACCOUNT_PASSWORD']})
                        vinfo = yy.extract_info(u, download=False)
                    except Exception as e:
                        await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                        continue
                else:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            elif 'This playlist does not exist' in e.__str__() or 'This playlist is private' in e.__str__():
                try:
                    yy = ydl.YoutubeDL({'format': video_format, 'noplaylist': True, 'youtube_include_dash_manifest': False})
                    vinfo = yy.extract_info(u, download=False)
                except Exception as e:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            elif 'are video-only' in e.__str__():
                try:
                    yy = ydl.YoutubeDL({'format': 'bestvideo[ext=mp4]', 'noplaylist': True, 'youtube_include_dash_manifest': False})
                    vinfo = yy.extract_info(u, download=False)
                except Exception as e:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            else:
                await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                continue

        entries = None
        if '_type' in vinfo and vinfo['_type'] == 'playlist':
            entries = vinfo['entries']
        else:
            entries = [vinfo]

        for entry in entries:
            formats = entry.get('requested_formats')
            file_size = None
            chosen_format = None
            ffmpeg_video = None

            if formats is not None:
                for i, f in enumerate(formats):
                    if f['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                        continue
                    if 'm3u8' in f['protocol']:
                        file_size = m3u8_video_size(f['url'])
                    else:
                        file_size = video_size(f['url'])

                    if f['protocol'] == 'https' and f['acodec'] == None:
                        # Dash video
                        vformat = f
                        mformat = None
                        vsize = video_size(vformat['url'])
                        msize = 0
                        if len(formats) > i+1:
                            mformat = formats[i+1]
                            video_size(mformat['url'])
                        file_size = vsize + msize + 10*1024*1024
                        if file_size/(1024*1024) < TG_MAX_FILE_SIZE:
                            ffmpeg_video = FFMpegVideo(vformat, mformat)
                            chosen_format = f
                        break
                    if ('m3u8' in f['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE):
                        chosen_format = f
                        ffmpeg_video = FFMpegVideo(chosen_format)
                        break
                    if file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE:
                        chosen_format = f
                        break

            else:
                if entry['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                    return
                if 'm3u8' in entry['protocol']:
                    file_size = m3u8_video_size(entry['url'])
                else:
                    file_size = video_size(entry['url'])
                if ('m3u8' in entry['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE):
                    chosen_format = entry
                    ffmpeg_video = FFMpegVideo(chosen_format)
                if (file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE):
                    chosen_format = entry

            try:
                if chosen_format is None and ffmpeg_video is None:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                    return
                if chosen_format['ext'] == 'unknown_video':
                    format = video_format(chosen_format['url'])
                    if format == 'MPEG-4':
                        chosen_format['ext'] = 'mp4'
                    else:
                        await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                        return
                file = await client.upload_file(ffmpeg_video if ffmpeg_video is not None else chosen_format['url'], file_name=entry['title'] + '.' + chosen_format['ext'], file_size=file_size, user_agent=user_agent)
                if ('duration' not in entry and 'duration' not in chosen_format) or ('width' not in chosen_format) or ('height' not in chosen_format):
                    width, height, duration = video_info(chosen_format['url'], use_m3u8=('m3u8' in chosen_format['protocol']))
                else:
                    width, height, duration = chosen_format['width'], chosen_format['height'], int(entry['duration']) if 'duration' not in entry else int(entry['duration'])

                if ffmpeg_video is not None:
                    ffmpeg_video.close()
                await client.send_file(CHAT_WITH_BOT_ID, file, video_note=True,
                                       attributes=(DocumentAttributeVideo(duration,
                                                                          width,
                                                                          height,
                                                                          supports_streaming=False if ffmpeg_video is not None else True),), caption=chat_and_message_id)
            except Exception as e:
                print(e)
                traceback.print_exc()


started = int(sys.argv[1])
if not started:
    client.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

