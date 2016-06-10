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

FPS = 25
SCENE_DURATION_T = 5
SCENE_DURATION_F = SCENE_DURATION_T * FPS
TRANSITION_T = 0.5
OUTPUT_VIDEO_WIDTH = 1200
OUTPUT_VIDEO_HEIGHT = 800
AUDIO_FADE_OUT_T = 4
AUDIO_TRACKS_INDEX_URL = "https://s3.amazonaws.com/asapvideo/audio/tracks.json"

def make_from_dir(dir,outdir=dir):
    # add all image files in the folder as input
    return _make(OrderedDict([(ff, None) for ff in [os.path.join(dir,f) for f in os.listdir(dir)] if imghdr.what(ff) != None]), outdir)

def make_from_url_list(list,outdir=None):
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
    return _make(OrderedDict([(r.geturl(), None) for r in [urllib2.urlopen(u) for u in list if prog.match(u)] if r.getcode() == 200 and r.info().getheader('Content-Type').startswith("image")]), outdir)

def _make(inputs, dir):
    # exit if no images were found
    if bool(inputs) == False:
        return None

    count = len(inputs)
    # calculate the length of the whole video
    lenght_t = SCENE_DURATION_T*count
    effects = ["zoompan=z='min(zoom+0.0015,1.5)':d={df}", "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={df}"]
    scene_filter = "[{n}:v]{effect},trim=duration={dt},fade=t=in:st=0:d={tt},fade=t=out:st={te}:d={tt},scale='iw*min({w}/iw\,{h}/ih)':'ih*min({w}/iw\,{h}/ih)', pad={w}:{h}:'({w}-iw*min({w}/iw\,{h}/ih))/2':'({h}-ih*min({w}/iw\,{h}/ih))/2',setpts=PTS-STARTPTS[v{n}]"

    # load available audio tracks info
    audio_track = None
    try:
        # loads the index from url
        response = urllib2.urlopen(AUDIO_TRACKS_INDEX_URL)
        content = response.read()
        audio_tracks_index = json.loads(content.translate(None, string.whitespace))
        # extracts all suitable tracks
        audio_tracks = [(t["url"], t["length"]) for t in audio_tracks_index["tracks"] if (t["type"] == "track" and t["length"] <= lenght_t) or t["type"] == "loop"]
        random.shuffle(audio_tracks)
        audio_track = next(iter(audio_tracks))
    except:
        # if we fail to select audio track we log error message and continue
        print("Failed to select audio track: ", sys.exc_info()[0].message)
        pass

    # create all video streams by applying effects to every image we found
    applied_filters = [scene_filter.format(n=ind, effect=effects[ind % 2].format(df=SCENE_DURATION_F), dt=SCENE_DURATION_T, tt=TRANSITION_T, te=SCENE_DURATION_T-TRANSITION_T, w=OUTPUT_VIDEO_WIDTH, h=OUTPUT_VIDEO_HEIGHT) for ind, x in enumerate(inputs)]
    # concatenate all video streams into a single stream
    applied_filters.append("{tags} concat=n={count}:v=1:a=0 [video]".format(tags="".join(["[v{0}]".format(ind) for ind, x in enumerate(inputs)]), count=count))

    if audio_track:
        # calculate number of loops for the audio track
        audio_track_repetition = int(math.ceil(lenght_t / float(audio_track[1])))
        # copy the audio track into the required number of audio streams
        applied_filters.append(";".join(["[{n}:a]afifo[a{i}]".format(n=count, i=i) for i in range(audio_track_repetition)]))
        # concatenate the audio streams into a single audio loop stream
        applied_filters.append("".join(["[a{i}]".format(i=i) for i in range(audio_track_repetition)]) + "concat=n={n}:v=0:a=1[a]".format(n=audio_track_repetition))
        # trim the audio stream to the required number of seconds and applies fade out effect
        applied_filters.append("[a]aselect=between(t\,0\,{d}),volume='if(lt(t,{e}),1,max(1-(t-{e})/{ae},0))':eval=frame[audio]".format(d=lenght_t, e=lenght_t-AUDIO_FADE_OUT_T, ae=AUDIO_FADE_OUT_T))
        # add the audio track to the inputs collection
        inputs.update({audio_track[0]: None})

    # build the video
    output = "video.mp4"
    output = os.path.join(dir,output) if dir else output
    ff = FFmpeg(
        global_options = ["-y"],
        inputs = inputs,
        outputs = {output: "-filter_complex \"" + ";".join(applied_filters) + "\" -map \"[video]\"" + (" -map \"[audio]\"" if audio_track else "") + " -c:v libx264 -pix_fmt yuvj420p -q:v 1"}
	)
    #print ff.cmd
    ff.run()
    return output
