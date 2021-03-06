import os
import sys
import imghdr
from ffmpy import FFmpeg
from collections import OrderedDict
import random
import math
import urllib2
import json
import string
import re
import uuid
import datetime
import time
import traceback
from filters import CombiningFilter, ZoompanEffectFilter, ImageSlideFilter, FadeTransitionFilter, FilterChain, SlideTransitionFilter, ConcatFilter, ReplicateAudioFilter, TrimAudioFilter, FadeOutAudioFilter, ZoompanSlideInTransitionFilter
from enum import IntEnum

FPS = 25
SCENE_DURATION_T = 5
TRANSITION_T = 0.5
OUTPUT_VIDEO_WIDTH = 1200
OUTPUT_VIDEO_HEIGHT = 800
AUDIO_FADE_OUT_T = 5
AUDIO_TRACKS_INDEX_URL = "https://s3.amazonaws.com/asapvideo/audio/tracks.json"
MAX_ZOOM = 1.0565

"""
    Batch modes enumerator.
"""
class BatchMode(IntEnum):
    none = 0,
    initial_batch = 1,  
    non_initial_batch = 2


"""
    Receives list of urls and returns the valid ones.
"""
def get_valid_media_urls_only(list, content_type = None):
    regex = r'('
    # Scheme (HTTP, HTTPS, FTP and SFTP):
    regex += r'(?:(https?|s?ftp):\/\/)?'
    # www:
    regex += r'(?:www\.)?'
    regex += r'('
    # Host and domain (including ccSLD):
    regex += r'(?:(?:[A-Z0-9][A-Z0-9-]{0,61}[A-Z0-9]\.)+)'
    # TLD:
    regex += r'([A-Z]{2,6})'
    # IP Address:
    regex += r'|(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    regex += r')'
    # Port:
    regex += r'(?::(\d{1,5}))?'
    # Query path:
    regex += r'(?:(\/\S+)*)'
    regex += r')'
    prog = re.compile(regex, re.IGNORECASE)

    # add all urls that are recognised as correct, return status code 200 and image content type
    result = []
    for u in [u for u in list if prog.match(u)]:
        try:
            r = urllib2.urlopen(u)
            if r.getcode() == 200 and (content_type == None or r.info().getheader('Content-Type').startswith(content_type)):
                result.append(r.geturl())
        except:
            pass

    return result
    

"""
    Creates video from all image files found in the passed directory.
"""
def make_from_dir(dir, scene_duration = SCENE_DURATION_T, outdir=dir, ffmpeg='ffmpeg', width=None, height=None, audio=True, effect=None, transition=None, batch_mode=BatchMode.none):
    # add all image files in the folder as input
    return _make([ff for ff in [os.path.join(dir,f) for f in os.listdir(dir)] if imghdr.what(ff) != None], scene_duration, outdir, ffmpeg, width, height, audio, effect, transition, batch_mode)


"""
    Creates video from all urls passed as a url list.
"""
def make_from_url_list(list, scene_duration = SCENE_DURATION_T, outdir=None, ffmpeg='ffmpeg', width=None, height=None, audio=True, effect=None, transition=None, batch_mode=BatchMode.none):
    dir = outdir if outdir else os.path.dirname(os.path.realpath(__file__))
    l = _download_file_list(list, dir)
    return _make(l, scene_duration, dir, ffmpeg, width, height, audio, effect, transition, batch_mode)


"""
    Private method for creating video from list of local image files.
"""
def _make(images, scene_duration, dir, ffmpeg, width, height, audio, effect, transition, batch_mode):
    # exit if no images were found
    if bool(images) == False:
        return None

    scene_duration_f = scene_duration * FPS
    w = width/2*2 if width != None else -2 if height != None else OUTPUT_VIDEO_WIDTH
    h = height/2*2 if height != None else -2 if width != None else OUTPUT_VIDEO_HEIGHT

    # build the animation dictionary of filters and first slide handling flag
    animations = {
        "zoompan": (
            CombiningFilter(
                [
                    ZoompanEffectFilter(maxzoom = MAX_ZOOM, frames = scene_duration_f),
                    ImageSlideFilter(duration = scene_duration, width = w, height = h)
                ],
                outstreamprefix = "zpaf"),
            False
        ),
        "fadeinout": (
            CombiningFilter([
                    FadeTransitionFilter(transition_duration = TRANSITION_T, total_duration = scene_duration),
                    ImageSlideFilter(duration = scene_duration, width = w, height = h)
                ],
                outstreamprefix = "faf"),
            False
        ),
        "zoompanfadeinout": (
            CombiningFilter(
                [
                    ZoompanEffectFilter(maxzoom = MAX_ZOOM, frames = scene_duration_f),
                    FadeTransitionFilter(transition_duration = TRANSITION_T, total_duration = scene_duration),
                    ImageSlideFilter(duration = scene_duration, width = w, height = h)
                ],
                outstreamprefix = "zpfaf"),
            False
        ),
        "slidein": (
            FilterChain(
                [
                    ImageSlideFilter(duration = scene_duration, width = w, height = h),
                    SlideTransitionFilter(transition_duration = TRANSITION_T, preserve_first = batch_mode != BatchMode.non_initial_batch)
                ]),
            True
        ),
        "zoompanslidein": (
            ZoompanSlideInTransitionFilter(transition_duration = TRANSITION_T, total_duration = scene_duration, fps = FPS, width = w, height = h, maxzoom = MAX_ZOOM, preserve_first = batch_mode != BatchMode.non_initial_batch),
            True
        )
    }
    animationkey = (effect if effect else "") + (transition if transition else "")
    animation = animations[animationkey] if animationkey in animations else None

    # determines if transition is requested and how to interpret the inputs list
    preserve_first_slide = animation[1] if animation else False
    if batch_mode != BatchMode.non_initial_batch:
        slides = images
        lenght_t = scene_duration * len(slides)
    elif preserve_first_slide:
        slides = images
        lenght_t = scene_duration * (len(slides) - 1)
    else:
        slides = images[1:]
        lenght_t = scene_duration * len(slides)
               
    inputs = OrderedDict([(i, "-loop 1") for i in slides])

    # create the video filter chain
    videoseq = FilterChain()
    if animation: 
        videoseq.append(animation[0])
    else:
        videoseq.append(ImageSlideFilter(duration = scene_duration, width = w, height = h))
    videoseq.append(ConcatFilter(True, "video"))
    applied_filters = videoseq.generate(["%d:v" % i for (i,x) in enumerate(inputs)])[0]
    
    # load audio track if requested
    if audio == True:
        audio_track = _get_audio(lenght_t, dir)
        # build the filter chain and execute it
        audioseq = FilterChain([
            ReplicateAudioFilter(repetitions = int(math.ceil(lenght_t / float(audio_track[1])))), 
            ConcatFilter(is_video = False, outputtag = "caf"),
            TrimAudioFilter(length = lenght_t),
            FadeOutAudioFilter(start = lenght_t-AUDIO_FADE_OUT_T, length = AUDIO_FADE_OUT_T, outstreamprefix="audio")
        ])
        applied_filters += audioseq.generate(["%d:a" % len(inputs)])[0]
        # add the audio track to the inputs collection
        inputs.update({audio_track[0]: None})

    # build the video
    output = "video.mp4"
    output = dir + "/" + output if dir else output
    ff = FFmpeg(
        executable = ffmpeg,
        global_options = ["-y"],
        inputs = inputs,
        outputs = {output: "-filter_complex \"" + ";".join(applied_filters) + "\" -map \"[video]\"" + (" -map \"[audio]\"" if audio == True else "") + " -c:v libx264 -pix_fmt yuvj420p -q:v 1"}
	)
    #print ff.cmd
    ff.run()
    return output


"""
    Concatenates all video files passed as a url list.
"""
def concat_videos(list, outdir=None, ffmpeg='ffmpeg', audio=True):
    dir = outdir if outdir else os.path.dirname(os.path.realpath(__file__))
    videos = _download_file_list(list, dir)
    if bool(videos) == False:
        return None
    
    # make the video files list
    file_name = os.path.normpath(os.path.join(dir, str(uuid.uuid4())))
    with open(file_name, 'w') as file:
        for video in videos:
            file.write("file '" + video + "'\n")

    # concatenate the videos
    output = os.path.normpath(os.path.join(dir, "video.mp4"))
    ff = FFmpeg(
        executable = ffmpeg,
        global_options = ["-y", "-f" ,"concat", "-safe", "0", "-protocol_whitelist", "file,http,https,tcp,tls"],
        inputs = {file_name: None},
        outputs = {output: "-c copy"}
	)
    #print ff.cmd
    out = ff.run()

    # if audio background is requested we will try to get duration of movie and matching audio file
    if audio == True:
        # collect data for concatenated movie total duration
        length = time.strptime(re.findall("(?<=time\\=)[0-9.:]+", out)[-1],"%H:%M:%S.%f")
        lenght_t = datetime.timedelta(hours=length.tm_hour,minutes=length.tm_min,seconds=length.tm_sec).total_seconds()
        inputs = OrderedDict([(output, None)])
        applied_filters = ["[0:v]null[video]"]
        audio_track = _get_audio(lenght_t, dir)
        # build the filter chain and execute it
        audioseq = FilterChain([
            ReplicateAudioFilter(repetitions = int(math.ceil(lenght_t / float(audio_track[1])))), 
            ConcatFilter(is_video = False, outputtag = "caf"),
            TrimAudioFilter(length = lenght_t),
            FadeOutAudioFilter(start = lenght_t-AUDIO_FADE_OUT_T, length = AUDIO_FADE_OUT_T, outstreamprefix="audio")
        ])
        applied_filters += audioseq.generate(["1:a"])[0]
        # add the audio track to the inputs collection
        inputs.update({audio_track[0]: None})

        # build the video
        output = os.path.normpath(os.path.join(dir, "videoa.mp4"))
        ff = FFmpeg(
            executable = ffmpeg,
            global_options = ["-y"],
            inputs = inputs,
            outputs = {output: "-filter_complex \"" + ";".join(applied_filters) + "\" -map \"[video]\" -map \"[audio]\""}
	    )
        #print ff.cmd
        ff.run()

    return output


"""
    Private method that gets audio track from the AUDIO_TRACKS_INDEX_URL audio library by desired length.
"""
def _get_audio(lenght, outdir):
    try:
        # loads the index from url
        r = urllib2.urlopen(AUDIO_TRACKS_INDEX_URL)
        content = ""
        while True:
            data = r.read()
            if not data: break
            content += data
        audio_tracks_index = json.loads(content.translate(None, string.whitespace))
        # extracts all suitable tracks
        audio_tracks = [(t["url"], t["length"]) for t in audio_tracks_index["tracks"] if (t["type"] == "track" and t["length"] <= lenght) or t["type"] == "loop"]
        random.shuffle(audio_tracks)
        track = next(iter(audio_tracks)) 
        return (_download_file((track[0], outdir)), track[1])
    except:
        # if we fail to select audio track we log error message and continue
        print("Failed to select audio track: ", sys.exc_info()[0])
        raise
    finally:
        r.close()

    return None

"""
    Downloads single file and stores it locally. Function is designed to be used with parallel library.
"""
def _download_file(pars):
    result = None
    url = pars[0]
    outdir = pars[1]
    retries = 0

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    while retries < 3:
        time.sleep(retries)
        retries += 1
        r = None
        try:
            r = urllib2.urlopen(url)
            file = os.path.normpath(os.path.join(outdir, str(uuid.uuid4())))
            with open(file,'wb+') as o:
                while True:
                    data = r.read()
                    if not data: break
                    o.write(data)
            result = file
            break
        except:
            print traceback.format_exc(sys.exc_info())
            if retries == 3: raise
        finally:
            if r: r.close()
            
    return result


"""
    Downloads files from url list.
"""
def _download_file_list(list, outdir):
    #pool = multiprocessing.Pool(processes=4)
    #return pool.map(_download_file, [(u, outdir) for u in list])
    return [_download_file((u, outdir)) for u in list]