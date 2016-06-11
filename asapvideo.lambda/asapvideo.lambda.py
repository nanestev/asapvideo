import os
import sys
import boto3
import asapvideo

def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            request = record['dynamodb']['NewImage']
            id = request['id']['S']
            succeeded = False
            video = None
            try:
                file = asapvideo.make_from_url_list(
                    request['urls']['SS'], 
                    scene_duration = int(request['scene_duration']['N'] if 'scene_duration' in request else asapvideo.SCENE_DURATION_T))
                if file:
                    s3 = boto3.client('s3')
                    transfer = boto3.s3.transfer.S3Transfer(s3)
                    key = 'video/' + id + os.path.splitext(file)[1]
                    transfer.upload_file(file, 'asapvideo', key, extra_args={'ACL': 'public-read'})
                    video = "https://s3.amazonaws.com/asapvideo/" + key
                succeeded = True
            except:
                print("Failed to make video: ", sys.exc_info()[0].message)

            update_record(id, "processed" if succeeded else "failed", video)
            

def update_record(id, status, video = None):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('asapvideo')
    update_expr = 'SET sts = :val1'
    expr_attr_values = { ':val1': status }
    if video:
        update_expr = update_expr + ", video = :val2"
        expr_attr_values.update({ ":val2": video })

    table.update_item(
        Key={
            'id': id
        },
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_attr_values
    )

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
#                                "url1",
#                                "url2",
#                                "url3"
#                            ]
#                        }
#                    }
#                }
#            }
#        ]
#    }
#    lambda_handler(event, None)
