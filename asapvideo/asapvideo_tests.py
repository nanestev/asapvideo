import asapvideo

def test_make_from_url_list():
    list = [
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=1",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=2",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=3",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=4",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=5"
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
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=16",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=17",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=18",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=19",
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
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=30",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=31",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=32",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=33",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=34",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=35",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=36",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=37",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=38",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=39",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=40",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=41",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=42",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=43",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=44",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=45",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=46",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=47",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=48",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=49",
        "https://printastic-pdfpreview.imgix.net/796092bcda15-b7c91f455aea4ba698281cb3e0478e4a.pdf?page=50"
    ]
    t=time.time()
    make_from_url_list(list, effect = "zoompan", transition = "slidein", outdir = "c:\\temp", audio=True, width=793, height=613, batch_mode = BatchMode.none)
    print "finished for %d seconds" % (time.time() - t)

def test_concat_videos():
    list = [
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video1.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video2.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video3.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video4.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video5.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video6.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video7.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video8.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video9.mp4",
        "https://s3.amazonaws.com/asapvideo/video/tmp/be4b2879-3fac-11e6-b83b-377abc4c5986/video10.mp4"
    ]
    t=time.time()
    concat_videos(list, audio=False, outdir = "c:\\temp")
    print "finished for %d seconds" % (time.time() - t)

#if __name__ == "__main__":
#    test_make_from_url_list()