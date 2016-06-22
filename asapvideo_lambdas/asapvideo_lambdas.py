import os
import sys
import stat
import boto3
import asapvideo
import shutil
import math
import json
import traceback

BATCH_SIZE = 10

def process_request_handler(event, context):
    # iterate through all new records
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'INSERT']:
        id = record['id']['S']
        list = asapvideo.get_valid_media_urls_only(record['urls']['SS'], 'image')
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

    # iterate through all modified records
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'MODIFY']:
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
                audio = bool(record['audio']) if 'audio' in record else True)

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
        transfer.upload_file(file, 'asapvideo', key, extra_args={'ACL': 'public-read'})
        video = "https://s3.amazonaws.com/asapvideo/" + key
    return video


def update_record(id, values):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('asapvideo')
    table.update_item(
        Key={'id': id},
        UpdateExpression='SET ' + ",".join(["{field} = :{field}".format(field = key) for key in values.iterkeys()]),
        ExpressionAttributeValues={":" + key : value for key, value in values.iteritems()}
    )


def add_output(id, batch, output):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('asapvideo')
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

#if __name__ == "__main__":
#    event = {
#        "Records": [
#            {
#                "eventName": "INSERT",
#                "dynamodb": {
#                    "NewImage": {
#                        "id": {
#                            "S": "some-id"
#                        },
#                        "urls": {
#                            "SS": [
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=11",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=12",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=13",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=14",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=15",
#                            ]
#                        }
#                    }
#                }
#            }
#        ]
#    }
#    process_request_handler(event, None)

#if __name__ == "__main__":
#    event = {
#        "Records": [
#            {
#                "eventName": "MODIFY",
#                "dynamodb": {
#                    "NewImage": {
#                        "batches": {
#                        "M": {
#                            "count": {
#                            "N": "4"
#                            },
#                            "outputs": {
#                            "L": [
#                                {
#                                "M": {
#                                    "batch": {
#                                        "N": "4"
#                                    },
#                                    "output": {
#                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video4.mp4"
#                                    }
#                                }
#                                },
#                                {
#                                "M": {
#                                    "batch": {
#                                        "N": "3"
#                                    },
#                                    "output": {
#                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video3.mp4"
#                                    }
#                                }
#                                },
#                                {
#                                "M": {
#                                    "batch": {
#                                        "N": "1"
#                                    },
#                                    "output": {
#                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video1.mp4"
#                                    }
#                                }
#                                },
#                                {
#                                "M": {
#                                    "batch": {
#                                        "N": "2"
#                                    },
#                                    "output": {
#                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video2.mp4"
#                                    }
#                                }
#                                }
#                            ]
#                            }
#                        }
#                        },
#                        "callback_url": {
#                            "S": "http://www.styloko.com"
#                        },
#                        "email": {
#                            "S": "myemail@gmail.com"
#                        },
#                        "height": {
#                            "N": "613"
#                        },
#                        "id": {
#                            "S": "833195d7-34a2-11e6-a74f-c1036123a238"
#                        },
#                        "scene_duration": {
#                            "N": "5"
#                        },
#                        "sts": {
#                            "S": "processing"
#                        },
#                        "transition": {
#                            "S": "fadeinout"
#                        },
#                        "urls": {
#                            "SS": [
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=11",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=12",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=13",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=14",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=15",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=16",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=17",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=18",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=19",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=20",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=21",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=22",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=23",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=24",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=25",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=26",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=27",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=28",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=29",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=30",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=31",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=32",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=33",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=34",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=35",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
#                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9"
#                            ]
#                        },
#                        "user_data": {
#                            "S": "my data"
#                        },
#                        "width": {
#                            "N": "793"
#                        }
#                    }
#                }
#            }
#        ]
#    }
#    process_request_handler(event, None)


#if __name__ == "__main__":
#    event = {
#        "Records": [
#            {
#                "Sns": {
#                    "Message": json.dumps({
#                        "id": "some-id",
#                        "batch": 1, 
#                        "urls": [
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9",
#                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
#                        ]
#                    })
#                }
#            }
#        ]
#    }
#    process_batch_handler(event, None)
