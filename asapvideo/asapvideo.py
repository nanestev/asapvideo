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
from filters import PanZoomEffectFilter, FadeTransitionFilter, SlideTransitionFilter, ConcatFilter, ImageSlideFilter, FilterChain, ReplicateAudioFilter, TrimAudioFilter, FadeOutAudioFilter
import multiprocessing

FPS = 25
SCENE_DURATION_T = 5
TRANSITION_T = 0.5
OUTPUT_VIDEO_WIDTH = 1200
OUTPUT_VIDEO_HEIGHT = 800
AUDIO_FADE_OUT_T = 5
AUDIO_TRACKS_INDEX_URL = "https://s3.amazonaws.com/asapvideo/audio/tracks.json"

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
    

def make_from_dir(dir, scene_duration = SCENE_DURATION_T, outdir=dir, ffmpeg='ffmpeg', width=None, height=None, audio=True, effect=None, transition=None):
    # add all image files in the folder as input
    return _make([ff for ff in [os.path.join(dir,f) for f in os.listdir(dir)] if imghdr.what(ff) != None], scene_duration, outdir, ffmpeg, width, height, audio, effect, transition)

def make_from_url_list(list, scene_duration = SCENE_DURATION_T, outdir=None, ffmpeg='ffmpeg', width=None, height=None, audio=True, effect=None, transition=None):
    dir = outdir if outdir else os.path.dirname(os.path.realpath(__file__))
    l = _download_file_list(list, dir)
    return _make(l, scene_duration, dir, ffmpeg, width, height, audio, effect, transition)

def _make(images, scene_duration, dir, ffmpeg, width, height, audio, effect, transition):
    # exit if no images were found
    if bool(images) == False:
        return None

    inputs = OrderedDict([(i, "-loop 1") for i in images])
    count = len(inputs)
    scene_duration_f = scene_duration * FPS
    # calculate the length of the whole video
    lenght_t = scene_duration*count
    effects = {"zoompan": PanZoomEffectFilter(scene_duration_f)}
    transitions = {"fadeinout": FadeTransitionFilter(TRANSITION_T, scene_duration), "slidein": SlideTransitionFilter(TRANSITION_T)}

    # create the video filter chain
    videoseq = FilterChain([ImageSlideFilter(scene_duration, width/2*2 if width != None else -2 if height != None else OUTPUT_VIDEO_WIDTH, height/2*2 if height != None else -2 if width != None else OUTPUT_VIDEO_HEIGHT)])
    if transition in transitions: 
        videoseq.append(transitions[transition])
    if effect in effects: 
        videoseq.append(effects[effect])
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
        applied_filters += audioseq.generate(["%d:a" % count])[0]
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

def _download_file(pars):
    result = None
    url = pars[0]
    outdir = pars[1]
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    try:
        r = urllib2.urlopen(url)
        if r.getcode() == 200:
            file = os.path.normpath(os.path.join(outdir, str(uuid.uuid4())))
            with open(file,'wb+') as o:
                while True:
                    data = r.read()
                    if not data: break
                    o.write(data)
            result = file
    except:
        print traceback.format_exc(sys.exc_info())
    finally:
        r.close()
    return result

def _download_file_list(list, outdir):
    #pool = multiprocessing.Pool(processes=4)
    #return pool.map(_download_file, [(u, outdir) for u in list])
    return [_download_file((u, outdir)) for u in list]

#if __name__ == "__main__":
#    list = [
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=11",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=12",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=13",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=14",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=15",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=16",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=17",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=18",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=19",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=20",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=21",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=22",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=23",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=24",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=25",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=26",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=27",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=28",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=29",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=30",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=31",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=32",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=33",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=34",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=35",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=36",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=37",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=38",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=39",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=40",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=41",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=42",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=43",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=44",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=45",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=46",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=47",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=48",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=49",
#        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=50"
#    ]
#    t=time.time()
#    make_from_url_list(list, transition = "slidein", outdir = "c:\\temp", audio=True, width=793, height=613)
#    print "finished for %d seconds" % (time.time() - t)

#if __name__ == "__main__":
#    list = [
#        "https://s3.amazonaws.com/asapvideo/video/tmp/0e4a1468-34a6-11e6-b49d-03a71b3fd792/video1.mp4",
#        "https://s3.amazonaws.com/asapvideo/video/tmp/0e4a1468-34a6-11e6-b49d-03a71b3fd792/video2.mp4",
#        "https://s3.amazonaws.com/asapvideo/video/tmp/0e4a1468-34a6-11e6-b49d-03a71b3fd792/video3.mp4",
#        "https://s3.amazonaws.com/asapvideo/video/tmp/0e4a1468-34a6-11e6-b49d-03a71b3fd792/video4.mp4"
#    ]
#    t=time.time()
#    concat_videos(list, audio=True, outdir = "c:\\temp")
#    print "finished for %d seconds" % (time.time() - t)