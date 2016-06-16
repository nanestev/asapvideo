import os
import sys
import stat
import boto3
import asapvideo
import shutil

def process_request_handler(event, context):
    # iterate through all the records and 
    for record in [r['dynamodb']['NewImage'] for r in event['Records'] if r['eventName'] == 'INSERT']:
        id = record['id']['S']
        state = {"sts": "failed"}
        
        try:
            # creates ouput directory
            outdir = "/tmp/" + id
            if not os.path.exists(outdir):
                os.makedirs(outdir)

            # runs video creation
            file = asapvideo.make_from_url_list(
                record['urls']['SS'], 
                scene_duration = int(record['scene_duration']['N'] if 'scene_duration' in record else asapvideo.SCENE_DURATION_T),
                outdir = outdir,
                ffmpeg = get_ffmpeg(),
                width = int(record['width']['N']) if 'width' in record else None,
                height = int(record['height']['N']) if 'height' in record else None,
                transition = record['transition']['S'] if 'transition' in record else None,
                effect = record['effect']['S'] if 'effect' in record else None)
            
            # if video was create successfully, we upload to s3
            if file:
                s3 = boto3.client('s3')
                transfer = boto3.s3.transfer.S3Transfer(s3)
                key = 'video/' + id + os.path.splitext(file)[1]
                transfer.upload_file(file, 'asapvideo', key, extra_args={'ACL': 'public-read'})
                state.update({"video": "https://s3.amazonaws.com/asapvideo/" + key})

            state["sts"] = "processed"
        except:
            print("Failed to make video: ", sys.exc_info()[0])

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

def get_ffmpeg():
    if os.path.isfile("/tmp/ffmpeg"):
        return os.path.abspath("/tmp/ffmpeg")
    elif os.path.isfile("ffmpeg"):
        shutil.copy("ffmpeg", "/tmp/ffmpeg")
        os.chmod("/tmp/ffmpeg", stat.S_IEXEC)
        return os.path.abspath("/tmp/ffmpeg")
    return "ffmpeg"

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
#                                "https://lh3.googleusercontent.com/XXvySCbKjkY-vi9AFC84-UGmLOcpDG7LfK8gXIUxWNgMua8TJD9KMhbSVVP7igLE4JmI95Wu3A8=w1920-h1080-rw-no",
#                                "https://lh3.googleusercontent.com/2wCn3hznt-gP9bnh0CIhrQyZEg0mnqxV6G8s3NhiVbn6XR-aGqQX6wV7zo70h_-O4bVhpeWRwg0=w1920-h1080-rw-no",
#                                "https://lh3.googleusercontent.com/_2c0u2O_6GU2cwL3uyx7BKUCgTEu0FJocKUZa7EHa840VZ-hwTr05FBA0MtEmf_Ae8nHAGDeZFI=w1920-h1080-rw-no"
#                            ]
#                        }
#                    }
#                }
#            }
#        ]
#    }
#    process_request_handler(event, None)
