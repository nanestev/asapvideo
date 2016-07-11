import asapvideo_lambdas

def test_process_request_handler_with_newly_added_record():
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
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=11",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=12",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=13",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=14",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=15",
                            ]
                        }
                    }
                }
            }
        ]
    }
    asapvideo_lambdas.process_request_handler(event, None)

def test_process_request_handler_with_modified_record():
    event = {
        "Records": [
            {
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "batches": {
                        "M": {
                            "count": {
                            "N": "4"
                            },
                            "outputs": {
                            "L": [
                                {
                                "M": {
                                    "batch": {
                                        "N": "4"
                                    },
                                    "output": {
                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video4.mp4"
                                    }
                                }
                                },
                                {
                                "M": {
                                    "batch": {
                                        "N": "3"
                                    },
                                    "output": {
                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video3.mp4"
                                    }
                                }
                                },
                                {
                                "M": {
                                    "batch": {
                                        "N": "1"
                                    },
                                    "output": {
                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video1.mp4"
                                    }
                                }
                                },
                                {
                                "M": {
                                    "batch": {
                                        "N": "2"
                                    },
                                    "output": {
                                        "S": "https://s3.amazonaws.com/asapvideo/video/tmp/833195d7-34a2-11e6-a74f-c1036123a238/video2.mp4"
                                    }
                                }
                                }
                            ]
                            }
                        }
                        },
                        "callback_url": {
                            "S": "http://www.styloko.com"
                        },
                        "email": {
                            "S": "myemail@gmail.com"
                        },
                        "height": {
                            "N": "613"
                        },
                        "id": {
                            "S": "833195d7-34a2-11e6-a74f-c1036123a238"
                        },
                        "scene_duration": {
                            "N": "5"
                        },
                        "sts": {
                            "S": "processing"
                        },
                        "transition": {
                            "S": "fadeinout"
                        },
                        "urls": {
                            "SS": [
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=11",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=12",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=13",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=14",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=15",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=16",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=17",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=18",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=19",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=20",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=21",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=22",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=23",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=24",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=25",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=26",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=27",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=28",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=29",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=30",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=31",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=32",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=33",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=34",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=35",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
                                "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9"
                            ]
                        },
                        "user_data": {
                            "S": "my data"
                        },
                        "width": {
                            "N": "793"
                        }
                    }
                }
            }
        ]
    }
    asapvideo_lambdas.process_request_handler(event, None)


def test_process_batch_handler():
    event = {
        "records": [
            {
                "sns": {
                    "message": json.dumps({
                        "id": "some-id",
                        "batch": 1, 
                        "urls": [
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=6",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=7",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=8",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=9",
                            "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=10",
                        ]
                    })
                }
            }
        ]
    }
    asapvideo_lambdas.process_batch_handler(event, none)

#if __name__ == "__main__":
#    test_process_request_handler_with_newly_added_record()