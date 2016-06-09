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

fps = 25
scene_duration_t = 5
scene_duration_f = scene_duration_t * fps
transition_t = 0.5
width = 1000
height = 1000
effects = ["zoompan=z='min(zoom+0.0015,1.5)':d={df}", "zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={df}"]
scene_filter = "[{n}:v]{effect},trim=duration={dt},fade=t=in:st=0:d={tt},fade=t=out:st={te}:d={tt},scale='iw*min({w}/iw\,{h}/ih)':'ih*min({w}/iw\,{h}/ih)', pad={w}:{h}:'({w}-iw*min({w}/iw\,{h}/ih))/2':'({h}-ih*min({w}/iw\,{h}/ih))/2',setpts=PTS-STARTPTS[v{n}]"
audio_fade_out_t = 4
audio_tracks_index_url = "https://s3.amazonaws.com/asapvideo/audio/tracks.json"

def make_from_dir(dir):
    # add all image files in the folder as input
    inputs = OrderedDict([(ff, None) for ff in [os.path.join(dir,f) for f in os.listdir(dir)] if imghdr.what(ff) != None])

    # exit if no images were found
    if bool(inputs) == False:
        return False

    count = len(inputs)
    # calculate the length of the whole video
    lenght_t = scene_duration_t*count

    # load available audio tracks info
    audio_track = None
    try:
        # loads the index from url
        response = urllib2.urlopen(audio_tracks_index_url)
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
    applied_filters = [scene_filter.format(n=ind, effect=effects[ind % 2].format(df=scene_duration_f), dt=scene_duration_t, tt=transition_t, te=scene_duration_t-transition_t, w=width, h=height) for ind, x in enumerate(inputs)]
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
        applied_filters.append("[a]aselect=between(t\,0\,{d}),volume='if(lt(t,{e}),1,max(1-(t-{e})/{ae},0))':eval=frame[audio]".format(d=lenght_t, e=lenght_t-audio_fade_out_t, ae=audio_fade_out_t))
        # add the audio track to the inputs collection
        inputs.update({audio_track[0]: None})

    # build the video
    ff = FFmpeg(
        global_options = ["-y"],
        inputs = inputs,
        outputs = {os.path.join(dir,"out.mp4"): "-filter_complex \"" + ";".join(applied_filters) + "\" -map \"[video]\"" + (" -map \"[audio]\"" if audio_track else "") + " -c:v libx264 -pix_fmt yuvj420p -q:v 1"}
	)
    #print ff.cmd
    ff.run()
    return True
    
if __name__ == "__main__":
    make_from_dir(".")