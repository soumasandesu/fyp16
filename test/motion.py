import argparse
import time

import cv2
import imutils
import numpy as np

from FaceCascading import FaceCascadingOpencvHaar, FaceCascadingOpencvLbp
from FaceRecognising import FaceRecognisingOpencv
from ImageCorrection import ImageCorrection
from MotionDetection import MotionDetection, NoWaitMotionDetection
from Performance.Performance import TimeElapseCounter
from Performance.Frames import FrameLimiter, FpsCounter
from VideoRecorder import NoWaitVideoRecorder


def filterImg(g):
    lap = TimeElapseCounter()
    lap.start()
    g = ImageCorrection.equalize_cv2(g)
    g = ImageCorrection.sharpenGaussianCv2Mat(g)
    g = ImageCorrection.brightness(g, 25)
    g = ImageCorrection.contrast(g, 1.25)
    # print('filter img %.4f secs' % lap.lap())
    return g

vid = None
file = False

ap = argparse.ArgumentParser()
gp = ap.add_mutually_exclusive_group()
gp.add_argument("-v", "--video", help="path to the video file")
gp.add_argument("-p", "--picam", help="use Raspberry Pi Camera", action='store_true')
ap.add_argument("-w", "--showWnd", help="show window for the output image", action='store_true')
ap.add_argument("-a", "--min-area", type=int, default=200, help="minimum area size")
args = vars(ap.parse_args())

if args['picam'] is True:
    from imutils.video.pivideostream import PiVideoStream

    vid = PiVideoStream((854, 480), 30)
elif args['video'] is not None:
    from imutils.video.filevideostream import FileVideoStream

    vid = FileVideoStream(args['video'], queueSize=256)
    file = True
else:
    from imutils.video.webcamvideostream import WebcamVideoStream

    vid = WebcamVideoStream()
vid.start()
time.sleep(2)

lastFrame = None
outVideoWriter = None

md = NoWaitMotionDetection()
vr = NoWaitVideoRecorder(fps=10)
fl = FrameLimiter()
fps = FpsCounter()
lap = TimeElapseCounter()

face_detect = FaceCascadingOpencvHaar()
face_recognise = FaceRecognisingOpencv()

i = 0

try:
    while True:
        mat = vid.read()
        if mat is None:
            time.sleep(1)
            continue
        mat = cv2.flip(mat, -1)
        mat = imutils.resize(mat, height=360)
        bbMat = mat
        # bbMat = imutils.resize(mat, height=144)
        bbMat = cv2.cvtColor(bbMat, cv2.COLOR_BGR2GRAY)
        bb = md.putNewFrameAndCheck(bbMat)
        # bb = np.array(np.round(np.multiply(bb, 480./144.)), 'int32')
        for (x1, y1, x2, y2) in bb:
            y2 = y1 + (y2 - y1) / 3
            trim_for_face = bbMat[y1:y2, x1:x2]
            trim_for_face = filterImg(trim_for_face)
            lap = TimeElapseCounter()
            lap.start()
            faces = face_detect.detect_face_crop_frame(trim_for_face)
            # print('face detect %.4f secs' % lap.lap())
            for f in faces:
                who, conf = face_recognise.predict(f)
                print("!!!!!! ==>  %s, %.2f" % (who, conf))

            lap.start()
        if lap.is_started() and (0 < lap.lap() > 5):
            vr.endWrite()
        else:
            vr.write(mat)
        fl.limitFps(10)
        actualFps = fps.actualFps()
        print("%.2f fps" % actualFps)
        cv2.putText(mat, "fps = %.2f" % actualFps, (30, 30), cv2.FONT_HERSHEY_DUPLEX, .6, (0, 192, 0), 1)
        if args['showWnd']:
            cv2.imshow("bbx", mat)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or (file and not vid.more()):
                break
            elif key == ord("p"):
                while (cv2.waitKey(1) & 0xFF) != ord("p"):
                    if key == ord("q"):
                        break
                    continue
except KeyboardInterrupt, SystemExit:
    print("oops")

print("waiting")
vr.endWriteWaitJoin()
print("ok")
vid.stop()
cv2.destroyAllWindows()
