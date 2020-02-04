import sys, os
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
from telethon.sessions import StringSession
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

CHAT_WITH_BOT_ID = os.environ['CHAT_WITH_BOT_ID']

client = TelegramClient(StringSession(os.environ['CLIENT_SESSION']), api_id, api_hash)

vid_format = 'best[ext=mp4,height<=1080]+best[ext=mp4,height<=480]/best[ext=mp4,height<=1080]/best[ext=mp4]/bestvideo[ext=mp4,height<=1080]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
worst_video_format = 'best[ext=mp4,height<=360]/bestvideo[ext=mp4,height<=360]+bestaudio[ext=m4a]/best'
audio_format = 'bestaudio[ext=m4a]/bestaudio/best[ext=mp4,height<=480]/best[ext=mp4]/best'

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

class FFMpegAV(DumbReader):

    def __init__(self, vformat, aformat=None, audio_only=False):
        _finput = ffmpeg.input(vformat['url'], **{"user-agent": user_agent, "loglevel": "error"})
        _fstream = None
        self.format = None
        if audio_only:
            self.format = 'mp3'
            acodec = None
            if 'acodec' in  vformat and vformat['acodec'] is not None:
                # if vformat['acodec'].startswith('mp4a'):
                #     acodec = 'm4a'
                if vformat['acodec'].startswith('mp3'):
                    acodec = 'mp3'

                if acodec != None:
                    _fstream = _finput.output('pipe:',
                                              format=acodec,
                                              acodec='copy',
                                              **{'vn': None})
                else:
                    _fstream = _finput.output('pipe:',
                                              format='mp3',
                                              acodec='mp3',
                                              **{'vn': None})
            else:
                _fstream = _finput.output('pipe:',
                                          format='mp3',
                                          acodec='mp3',
                                          **{'vn': None})
        else:
            _fstream = _finput.output('pipe:',
                                      format='mp4',
                                      vcodec='copy',
                                      acodec='copy',
                                      movflags='frag_keyframe')
        if aformat:
            self.stream = _fstream.global_args('-user-agent', user_agent, '-i', aformat['url'], '-map', '0:v', '-map', '1:a').run_async(pipe_stdout=True)
        else:
            self.stream = _fstream.run_async(pipe_stdout=True)

    def read(self, n: int = -1):
        return self.stream.stdout.read(n)

    def close(self) -> None:
        print('last data ', len(self.stream.stdout.read()))
        self.stream.kill()


def av_info(url, use_m3u8=False, audio_info=False):
    if use_m3u8:
        m3u8_obj = m3u8.load(url)
        url = m3u8_obj.segments[0].absolute_uri  # override for mediainfo call
        dur = 0
        for s in m3u8_obj.segments:
            if hasattr(s, 'duration'):
                dur += s.duration

    mediainf_args = None
    if audio_info:
        mediainf_args = '--Inform=Audio;%Duration%'
    else:
        mediainf_args = '--Inform=Video;%Width%\\n%Height%\\n%Duration%'
    mi_proc = subprocess.Popen(['mediainfo', mediainf_args, '2>', '/dev/null', url],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    out = mi_proc.stdout.read()
    out = out.split(b'\n')

    w = h = None
    if not audio_info:
        w = int(out[0])
        h = int(out[1])
    if use_m3u8:
        dur = int(dur)
    else:
        dur = int(int(float(out[2 if not audio_info else 0]))/1000)

    if audio_info:
        return dur
    else:
        return w, h, dur

def video_format(url):
    mi_proc = subprocess.Popen(['mediainfo', '--Inform=General;%Format%', '2>', '/dev/null', url],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    out = mi_proc.stdout.read()
    return out.split(b'\n')[0].decode('utf-8')

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3719.5 Safari/537.36'

def video_size(url, http_headers=None):
    head_req = request.Request(url, method='HEAD', headers=http_headers)
    try:
        with request.urlopen(head_req) as resp:
            return int(resp.headers['Content-Length'])
    except:
        return 1479*1024*1024*1024 # trying upload file even if failed to get size



def m3u8_video_size(url, http_headers=None):
    m3u8_obj = m3u8.load(url)
    size = 0

    for seg in m3u8_obj.segments:
        head_req = request.Request(seg.absolute_uri, method='HEAD', headers=http_headers)
        with request.urlopen(head_req) as resp:
            size += int(resp.headers['Content-Length'])

    return size

async def main():
    chat_and_message_id = str(sys.argv[1])
    urls = str(sys.argv[2]).split(" ")
    mode = None if len(sys.argv) <= 3 else sys.argv[3]

    y_format = None
    playlist_start = None
    playlist_end = None
    # p - playlist video; pa - playlist audio; pw - playlist worse video
    if mode is not None:
        if mode.startswith('p') or mode.startswith('pa') or mode.startswith('pw'):
            pmode, prange = mode.split(':')
            _start, _end = prange.split('-')
            playlist_start = int(_start)
            playlist_end = int(_end)
            # cut "p" from mode variable if mode == "pa" or "pw"
            mode = pmode if len(pmode) == 1 else pmode[-1]

        if mode == 'a':
            # audio mode
            y_format = audio_format
        elif mode == 'w':
            # wordst video mode
            y_format = worst_video_format
        else:
            # normal mode
            y_format = vid_format
    else:
        y_format = vid_format

    for u in urls:
        try:
            params = {'format': y_format, 'noplaylist': True, 'youtube_include_dash_manifest': False}
            if playlist_start != None and playlist_end != None:
                if playlist_start == 0 and playlist_end == 0:
                    params['playliststart'] = 1
                    params['playlistend'] = 10
                else:
                    params['playliststart'] = playlist_start
                    params['playlistend'] = playlist_end
            else:
                params['playlist_items'] = '1'

            y = ydl.YoutubeDL(params)
            vinfo = y.extract_info(u, download=False)
        except Exception as e:
            if "Please log in or sign up to view this video" in e.__str__():
                if 'vk.com' in u or 'facebook.com' in u:
                    try:
                        params['username'] = os.environ['VIDEO_ACCOUNT_USERNAME']
                        params['password'] = os.environ['VIDEO_ACCOUNT_PASSWORD']
                        yy = ydl.YoutubeDL(params)
                        vinfo = yy.extract_info(u, download=False)
                    except Exception as e:
                        await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                        continue
                else:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            elif 'are video-only' in e.__str__():
                try:
                    params['format'] = 'bestvideo[ext=mp4]'
                    yy = ydl.YoutubeDL(params)
                    vinfo = yy.extract_info(u, download=False)
                except Exception as e:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                    continue
            else:
                await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+e.__str__())
                traceback.print_exc()
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
            ffmpeg_av = None
            http_headers = None
            if 'http_headers' not in entry:
                if len(formats) > 0 and 'http_headers' in formats[0]:
                        http_headers = formats[0]['http_headers']
            else:
                http_headers = entry['http_headers']

            if formats is not None:
                for i, f in enumerate(formats):
                    if f['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                        continue
                    if 'm3u8' in f['protocol']:
                        file_size = m3u8_video_size(f['url'], http_headers)
                    else:
                        file_size = video_size(f['url'], http_headers)

                    if f['protocol'] == 'https' and (True if ('acodec' in f and (f['acodec'] == 'none' or f['acodec'] == None)) else False):
                        # Dash video
                        vformat = f
                        mformat = None
                        vsize = video_size(vformat['url'], http_headers)
                        msize = 0
                        if len(formats) > i+1:
                            mformat = formats[i+1]
                            video_size(mformat['url'], http_headers)
                        file_size = vsize + msize + 10*1024*1024
                        if file_size/(1024*1024) < TG_MAX_FILE_SIZE:
                            ffmpeg_av = FFMpegAV(vformat, mformat)
                            chosen_format = f
                        break
                    if ('m3u8' in f['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE):
                        chosen_format = f
                        ffmpeg_av = FFMpegAV(chosen_format, audio_only=True if mode == 'a' else False)
                        break
                    if file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE:
                        chosen_format = f
                        if mode == 'a' and not (chosen_format['acodec'].startswith('mp3')): #or chosen_format['acodec'].startswith('mp4a')):
                            ffmpeg_av = FFMpegAV(chosen_format, audio_only=True if mode == 'a' else False)
                        break

            else:
                if entry['protocol'] in ['rtsp', 'rtmp', 'rtmpe', 'mms', 'f4m', 'ism', 'http_dash_segments']:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                    return
                if 'm3u8' in entry['protocol']:
                    file_size = m3u8_video_size(entry['url'], http_headers)
                else:
                    file_size = video_size(entry['url'], http_headers)
                if ('m3u8' in entry['protocol'] and file_size / (1024*1024) <= TG_MAX_FILE_SIZE):
                    chosen_format = entry
                    ffmpeg_av = FFMpegAV(chosen_format, audio_only=True if mode == 'a' else False)
                if (file_size / (1024 * 1024) <= TG_MAX_FILE_SIZE):
                    chosen_format = entry
                    if mode == 'a' and not (chosen_format['acodec'].startswith('mp3')): #or chosen_format['acodec'].startswith('mp4a')):
                        ffmpeg_av = FFMpegAV(chosen_format, audio_only=True if mode == 'a' else False)


            try:
                if chosen_format is None and ffmpeg_av is None:
                    await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                    return
                if chosen_format['ext'] == 'unknown_video':
                    format = video_format(chosen_format['url'])
                    if format == 'MPEG-4':
                        chosen_format['ext'] = 'mp4'
                    else:
                        await client.send_message(CHAT_WITH_BOT_ID, chat_and_message_id+" "+"ERROR: Failed find suitable video format")
                        return
                if mode == 'a':
                    # we don't know real size due to converting formats
                    # so increase it in case of real size is less large then estimated
                    file_size += 200000
                file = await client.upload_file(ffmpeg_av if ffmpeg_av is not None else chosen_format['url'],
                                                file_name=entry['title'] + '.' + (chosen_format['ext'] if ffmpeg_av is None or ffmpeg_av.format is None else ffmpeg_av.format),
                                                file_size=file_size, http_headers=http_headers)

                width = height = duration = None
                if mode == 'a':
                    if ('duration' not in entry and 'duration' not in chosen_format):
                        duration = av_info(chosen_format['url'], use_m3u8=('m3u8' in chosen_format['protocol']), audio_info=True)
                    else:
                        duration = int(entry['duration']) if 'duration' not in entry else int(entry['duration'])

                elif ('duration' not in entry and 'duration' not in chosen_format) or ('width' not in chosen_format) or ('height' not in chosen_format):
                    width, height, duration = av_info(chosen_format['url'], use_m3u8=('m3u8' in chosen_format['protocol']))
                else:
                    width, height, duration = chosen_format['width'], chosen_format['height'], \
                                              int(entry['duration']) if 'duration' not in entry else int(entry['duration'])

                if ffmpeg_av is not None:
                    ffmpeg_av.close()

                attributes = None
                if mode == 'a':
                    attributes = DocumentAttributeAudio(duration, title=entry['title'])
                else:
                    attributes = DocumentAttributeVideo(duration,
                                                        width,
                                                        height,
                                                        supports_streaming=False if ffmpeg_av is not None else True)
                force_document = False
                if ffmpeg_av is None and (chosen_format['ext'] != 'mp4' and mode != 'a'):
                        force_document = True
                await client.send_file(CHAT_WITH_BOT_ID, file, video_note=False if mode == 'a' or force_document else True,
                                       voice_note= True if mode == 'a' else False,
                                       attributes=((attributes,) if not force_document else None), caption=chat_and_message_id, force_document=force_document)
            except Exception as e:
                print(e)
                traceback.print_exc()


client.start()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

