import os
import sys
import stat
import boto3
import asapvideo
import shutil
import math
import json
import traceback

BATCH_SIZE = 20
BATCHES_SNS_TOPIC = 'arn:aws:sns:us-east-1:419956479724:asapvideo-batches'
S3_BUCKET = 'asapvideo'
DYNAMODB_TABLE = 'asapvideo'

def process_request_handler(event, context):
    # iterate through all new records
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'INSERT' and 'urls' in r['dynamodb']['NewImage']]:
        id = record['id']['S']
        list = asapvideo.get_valid_media_urls_only([o['M']['url']['S'] for o in sorted(record['urls']['L'], key=lambda url: int(url['M']['pos']['N']))], 'image')
        scene_duration = int(record['scene_duration']['N']) if 'scene_duration' in record else asapvideo.SCENE_DURATION_T
        width = int(record['width']['N']) if 'width' in record else None
        height = int(record['height']['N']) if 'height' in record else None
        transition = record['transition']['S'] if 'transition' in record else None
        effect = record['effect']['S'] if 'effect' in record else None
        batches = int(math.ceil(len(list) / float(BATCH_SIZE)))
        
        if batches == 0:
            update_record(id, {"sts": "processed"})
        else:
            update_record(id, {"sts": "processing", "batches": {"count": batches}})
            sns = boto3.client('sns')
            for i in range(0, batches):
                message = json.dumps(clear_dict({
                    "id": id,
                    "batch": i + 1,
                    "urls": list[max((i*BATCH_SIZE)-1, 0):(i+1)*BATCH_SIZE],
                    "scene_duration": scene_duration,
                    "width": width,
                    "height": height,
                    "transition": transition,
                    "effect": effect,
                    "audio": False
                }), separators=(',', ':'))
                response = sns.publish(
                    TopicArn=BATCHES_SNS_TOPIC,
                    Message=message,
                    Subject='SubmitBatch'
                )

    # iterate through all modified records
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'MODIFY' and 'urls' in r['dynamodb']['NewImage']]:
        # take those that are ready for final processment
        if  record['sts']['S'] == 'processing' and 'batches' in record and 'outputs' in record['batches']['M'] and int(record['batches']['M']['count']['N']) == len(record['batches']['M']['outputs']['L']):
            try:
                id = record['id']['S']

                # create ouput directory
                outdir = "/tmp/" + id
                if not os.path.exists(outdir):
                    os.makedirs(outdir)

                # concatenate all outputs
                file = asapvideo.concat_videos(
                    [o['M']['output']['S'] for o in sorted(record['batches']['M']['outputs']['L'], key=lambda output: int(output['M']['batch']['N']))],
                    outdir = outdir,
                    ffmpeg = get_ffmpeg(),
                    audio = True
                )

                # upload to s3 and modify the record for a last time
                video = upload_to_s3(file, id)
                state = {'sts': 'processed' if video else 'failed'}
                if video: state.update({'video': video})
                update_record(id, state)
            except:
                print "Failed to concatenate batches"
                print traceback.format_exc(sys.exc_info())

def process_batch_handler(event, context):
    for record in [json.loads(r['Sns']['Message']) for r in event['Records']]:
        id = record['id']

        try:
            batch = record['batch']

            # creates ouput directory
            outdir = "/tmp/" + id
            if not os.path.exists(outdir):
                os.makedirs(outdir)

            # runs video creation
            file = asapvideo.make_from_url_list(
                record['urls'], 
                scene_duration = int(record['scene_duration']) if 'scene_duration' in record else asapvideo.SCENE_DURATION_T,
                outdir = outdir,
                ffmpeg = get_ffmpeg(),
                width = int(record['width']) if 'width' in record else None,
                height = int(record['height']) if 'height' in record else None,
                transition = record['transition'] if 'transition' in record else None,
                effect = record['effect'] if 'effect' in record else None,
                audio = bool(record['audio']) if 'audio' in record else True,
                batch_mode = asapvideo.BatchMode.initial_batch if batch == 1 else asapvideo.BatchMode.non_initial_batch)

            if file == None:
                raise Exception("No output video was created for request %s batch %d" % (id, batch))

            video_url = upload_to_s3(file, "tmp/" + id + '/video' + str(batch))
            add_output(id, batch, video_url)
        except:
            print "Failed to make video for batch %d" % batch
            print traceback.format_exc(sys.exc_info())
            update_record(id, {"sts":"failed"})


def upload_to_s3(file, name):
    video = None
    if file:               
        s3 = boto3.client('s3')
        transfer = boto3.s3.transfer.S3Transfer(s3)
        key = 'video/{name}{ext}'.format(name=name, ext=os.path.splitext(file)[1]) 
        transfer.upload_file(file, S3_BUCKET, key, extra_args={'ACL': 'public-read'})
        video = "https://s3.amazonaws.com/%s/%s" % (S3_BUCKET,key)
    return video


def update_record(id, values):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.update_item(
        Key={'id': id},
        UpdateExpression='SET ' + ",".join(["{field} = :{field}".format(field = key) for key in values.iterkeys()]),
        ExpressionAttributeValues={":" + key : value for key, value in values.iteritems()}
    )


def add_output(id, batch, output):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.update_item(
        Key={'id': id},
        UpdateExpression='SET batches.outputs=list_append(if_not_exists(batches.outputs, :l), :o)',
        ExpressionAttributeValues={":l": [], ":o": [{"batch": batch, "output": output}]}
    )


def get_ffmpeg():
    if os.path.isfile("/tmp/ffmpeg"):
        return os.path.abspath("/tmp/ffmpeg")
    elif os.path.isfile("ffmpeg"):
        shutil.copy("ffmpeg", "/tmp/ffmpeg")
        os.chmod("/tmp/ffmpeg", stat.S_IEXEC)
        return os.path.abspath("/tmp/ffmpeg")
    return "ffmpeg"


def clear_dict(d):
    # d.iteritems isn't used as you can't del or the iterator breaks.
    for key, value in d.items():
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            del_none(value)
    return d