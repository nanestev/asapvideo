import os
import sys
import stat
import boto3
import asapvideo
import shutil
import math
import json

BATCH_SIZE = 10

def process_request_handler(event, context):
    # iterate through all the records and 
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'INSERT']:
        id = record['id']['S']
        list = asapvideo.get_valid_image_urls_only(record['urls']['SS'])
        scene_duration = int(record['scene_duration']['N']) if 'scene_duration' in record else asapvideo.SCENE_DURATION_T
        width = int(record['width']['N']) if 'width' in record else None
        height = int(record['height']['N']) if 'height' in record else None
        transition = record['transition']['S'] if 'transition' in record else None
        effect = record['effect']['S'] if 'effect' in record else None
        batches = int(math.ceil(len(list) / float(BATCH_SIZE)))
        state = {"batches": batches}
        
        if batches == 0:
            state.update({"sts": "processed"})
        elif batches == 1:
            video_url = get_video_url(id, "video", list, scene_duration, width, height, transition, effect, True)
            state.update({"sts": "processed", "video": video_url})
        else:
            state.update({"sts": "processing"})
            sns = boto3.client('sns')
            for i in range(0, batches):
                message = json.dumps(clear_dict({
                    "id": id,
                    "batch": i + 1,
                    "urls": list[i*10:(i+1)*10],
                    "scene_duration": scene_duration,
                    "width": width,
                    "height": height,
                    "transition": transition,
                    "effect": effect,
                    "audio": False
                }), separators=(',', ':'))
                response = sns.publish(
                    TopicArn='arn:aws:sns:us-east-1:419956479724:asapvideo-batches',
                    Message=message,
                    Subject='SubmitBatch'
                )

        update_record(id, state)

def process_batch_handler(event, context):
    for record in [json.loads(r['Sns']['Message']) for r in event['Records']]:
        id = record['id']
        state = {}
        try:
            batch = "video" + str(record['batch'])
            video_url = get_video_url(
                id, 
                batch, 
                record['urls'], 
                int(record['scene_duration']) if 'scene_duration' in record else asapvideo.SCENE_DURATION_T,
                int(record['width']) if 'width' in record else None,
                int(record['height']) if 'height' in record else None,
                record['transition'] if 'transition' in record else None,
                record['effect'] if 'effect' in record else None,
                bool(record['audio']) if 'audio' in record else True)

            if video_url == None:
                raise Exception("No output video was created for request %s batch %s" % (id, batch))

            state.update({batch: video_url})
        except:
            print("Failed to make video: ", sys.exc_info()[0])        
            state.update({"sts":"failed"})

        update_record(id, state)

def update_record(id, values):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('asapvideo')
    update_expr = 'SET ' + ",".join(["{field} = :{field}".format(field = key) for key in values.iterkeys()])

    table.update_item(
        Key={
            'id': id
        },
        UpdateExpression=update_expr,
        ExpressionAttributeValues={":" + key : value for key, value in values.iteritems()}
    )

def get_video_url(id, batch, urls, scene_duration, width, height, transition, effect, audio):
    video = None
    # creates ouput directory
    outdir = "/tmp/" + id
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # runs video creation
    file = asapvideo.make_from_url_list(urls, 
        scene_duration = scene_duration,
        outdir = outdir,
        ffmpeg = get_ffmpeg(),
        width = width,
        height = height,
        transition = transition,
        effect = effect,
        audio = audio)

    # if video was created successfully, we upload to s3
    if file:               
        s3 = boto3.client('s3')
        transfer = boto3.s3.transfer.S3Transfer(s3)
        key = 'video/{id}/{batch}{ext}'.format(id=id, batch=batch, ext=os.path.splitext(file)[1]) 
        transfer.upload_file(file, 'asapvideo', key, extra_args={'ACL': 'public-read'})
        video = "https://s3.amazonaws.com/asapvideo/" + key

    return video

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

if __name__ == "__main__":
    event = {
        "Records": [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "id": {
                            "S": "some-id"
                        },
                        "urls": {
                            "SS": [
                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/2wCn3hznt-gP9bnh0CIhrQyZEg0mnqxV6G8s3NhiVbn6XR-aGqQX6wV7zo70h_-O4bVhpeWRwg0=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/_2c0u2O_6GU2cwL3uyx7BKUCgTEu0FJocKUZa7EHa840VZ-hwTr05FBA0MtEmf_Ae8nHAGDeZFI=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/2wCn3hznt-gP9bnh0CIhrQyZEg0mnqxV6G8s3NhiVbn6XR-aGqQX6wV7zo70h_-O4bVhpeWRwg0=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/_2c0u2O_6GU2cwL3uyx7BKUCgTEu0FJocKUZa7EHa840VZ-hwTr05FBA0MtEmf_Ae8nHAGDeZFI=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/2wCn3hznt-gP9bnh0CIhrQyZEg0mnqxV6G8s3NhiVbn6XR-aGqQX6wV7zo70h_-O4bVhpeWRwg0=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/_2c0u2O_6GU2cwL3uyx7BKUCgTEu0FJocKUZa7EHa840VZ-hwTr05FBA0MtEmf_Ae8nHAGDeZFI=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/2wCn3hznt-gP9bnh0CIhrQyZEg0mnqxV6G8s3NhiVbn6XR-aGqQX6wV7zo70h_-O4bVhpeWRwg0=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/_2c0u2O_6GU2cwL3uyx7BKUCgTEu0FJocKUZa7EHa840VZ-hwTr05FBA0MtEmf_Ae8nHAGDeZFI=w1920-h1080-rw-no",
                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no"
                            ]
                        }
                    }
                }
            }
        ]
    }
    process_request_handler(event, None)
