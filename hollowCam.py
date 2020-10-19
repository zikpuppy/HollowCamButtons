from guizero import App, PushButton, Slider, Text, ButtonGroup
from gpiozero import Button
import numpy as np
from PIL import Image, ImageDraw
from picamera import PiCamera
from yaml import load
import time

try:
    from yaml import CLoader as Loader
except:
    from yaml import Loader
stream = open('HollowCamConfig.yml',  'r')

hollowConfig = load (stream,  Loader=Loader)

cameraProps = hollowConfig.get("camera")
overlayProps = hollowConfig.get("overlay")
hardwareProps = hollowConfig.get("hardware")

DEFAULT_ALPHA = "1"
    
curOverlay = 0
oLay = 0

BRIGHT_JUMP = 4
CONTRAST_JUMP = 4
 
CAL_THRESHOLD = 128
CAL_THRESHOLD_JUMP = 8
calThreshold = CAL_THRESHOLD

OVERLAY_ALPHA = 128
OALPHA_JUMP = 8
overlayAlpha = OVERLAY_ALPHA

ROTATE = cameraProps['Rotation']

#define physical button addresses using BCM pinout
#GPIO button to activate the alignment box
boxBtn = Button(hardwareProps['AlligmentBoxBtn'])
#GPIO button to capture the tool overlay snapshot
calBtn = Button(hardwareProps['CaptureOverlayBtn'])
   
def pixelProcRed(intensity):
    return intensity

def pixelProcBlue(intensity):
    return intensity

def pixelProcGreen(intensity):
    return intensity

def pixelProcAlpha(intensity):
    ret = 0
    return ret

def cal_overlay():
    global imgW,imgH,oLay,curOverlay,calThreshold,winXoff, winYoff

    print("cal_overlay clicked = ",oLay)
    if (oLay != 0):
        camera.remove_overlay(curOverlay)
    
    Ioutput = np.ones((imgH, imgW, 4), dtype=np.uint8)
        
#capture a still image       
    camera.capture(Ioutput, 'rgba')
    tempImg = Image.fromarray(Ioutput)
    multiBands      = tempImg.split()


# Apply point operAppations that does thresholding on each color band
    redBand     = multiBands[0].point(pixelProcRed)
    greenBand   = multiBands[1].point(pixelProcGreen)
    blueBand    = multiBands[2].point(pixelProcBlue)
# the alpha band will be zero'd
    alphaBand   = multiBands[3].point(pixelProcAlpha)


#hRange is the start Y + the height of the cal box
    hRange = calboxY+calboxH
    for i in range(int(calboxY),hRange):
        for j in range(calboxX,calBoxWidth):
            if(greenBand.getpixel((j,i)) < calThreshold):
                alphaBand.putpixel((j,i),int (overlayAlpha))
    newImage = Image.merge("RGBA", (redBand, greenBand, blueBand, alphaBand))
    Ioutput = newImage.convert("RGBA")
    curOverlay = camera.add_overlay(Ioutput.tobytes(),fullscreen=False,
                                    window = (winXoff, winYoff, imgW, imgH),layer=3, alpha=128)
    oLay = 1
   
def box_overlay():
    global imgW,imgH,oLay,curOverlay,winXoff, winYoff
    global calboxX, calboxY, calboxH, calBoxWidth
    if (oLay != 0):
        camera.remove_overlay(curOverlay)
    output = Image.new('RGBA', (imgW, imgH) )
    draw = ImageDraw.Draw(output)
    draw.rectangle((calboxX, calboxY, calBoxWidth, calboxY+calboxH),  outline=(0, 255, 255))    

#Crosshairs
    draw.line(((imgW / 2),
              (imgH / 2) - 30,
              (imgW / 2),
              (imgH / 2) + 30),
              width=1, fill = "red")

    draw.line(((imgW / 2) - 30,
              (imgH / 2),
              (imgW / 2) + 30,
              (imgH / 2)),
              width=1, fill = "red")

    draw.arc(((imgW / 2) - 16,
              (imgH / 2) - 16,
              (imgW / 2) + 16,
              (imgH / 2) + 16),
              0,360,
              width=1, fill = "red")
    
    curOverlay = camera.add_overlay(output.tobytes(),fullscreen=False,
                                    window = (winXoff, winYoff, imgW, imgH),layer=3)
    oLay = 1

def prevOn():
    global imgW,imgH,mainAlpha,curOverlay,oLay,winXoff, winYoff
    camera.stop_preview()
    print(imgW, imgH)
    camera.resolution = (imgW, imgH)
    camera.rotation = ROTATE
    if (oLay != 0):
        camera.remove_overlay(curOverlay)
        oLay = 0
    camera.start_preview(alpha=mainAlpha,fullscreen=False, window = (winXoff, winYoff, imgW, imgH))

def app_done():
    camera.close()
    app.destroy()

def resolution_changed():
    global imgW,imgH, calboxX, calboxY,calboxH,calBoxWidth

    camera.stop_preview()
    if (res_choice.value =="5"):
        imgW = 1024
        imgH = 720
        calBoxWidth = imgW - 100
        calboxX = int(imgW / 2) - 150
        
    if (res_choice.value =="4"):
        imgW = 1280
        imgH = 720
        calBoxWidth = imgW - 200
        calboxX = int(imgW / 2) - 150
        
    if (res_choice.value == "3"):
        imgW = 1024
        imgH = 576
        calBoxWidth = imgW
        calboxX = int(imgW / 2) - 50

    if (res_choice.value == "2"):
        imgW = 960
        imgH = 544
        calBoxWidth = imgW
        calboxX = int(imgW / 2) - 50

    if (res_choice.value == "1"):
        imgW = 640
        imgH = 480
        calBoxWidth = imgW
        calboxX = int(imgW / 2) - 50

    print("resolution_changed",res_choice.value,imgW,imgH)
    calboxY = int(imgH / 3)
    calboxH = int(imgH / 3)
    prevOn()

def mainAlpha_changed(slider_value):
    global mainAlpha
    mainAlpha = 255    
    if (slider_value == "0"):
        mainAlpha = 128    
    prevOn()
    
#applied alpha 
def overlayAlpha_changed(slider_value): 
    global overlayAlpha
#     print("oAlpha_changed",OVERLAY_ALPHA + (int(slider_value)*OALPHA_JUMP))
    overlayAlpha = OVERLAY_ALPHA + (int(slider_value)*OALPHA_JUMP)  


def wb_changed():
#     print("wb_changed ",wb_choice.value)
    camera.awb_mode=wb_choice.value
    
def contrast_changed(slider_value):
#     print("contrast_changed ",int(slider_value)*CONTRAST_JUMP)
    camera.contrast =int(slider_value) * CONTRAST_JUMP
    
def bright_changed(slider_value):
#     print("bright_changed",50+(int(slider_value) * BRIGHT_JUMP))
    camera.brightness =50+(int(slider_value) * BRIGHT_JUMP)

#tool calibration threshold
def threshold_changed(slider_value):
    global calThreshold
    calThreshold = CAL_THRESHOLD + (int(slider_value)*CAL_THRESHOLD_JUMP)
#     print("threshold_changed",calThreshold)

def exposure_changed(slider_value):
#     print("exposure_changed",int(slider_value) * 2)
    camera.exposure_compensation = (int(slider_value) * 2)

def btn_box_pressed():    
#   This is for a physical button press It must detect the status of the allignment box then show/hide accordingly
    print("Physical button allignment box pressed.")
    mainAlphaSlider.value = 0
    time.sleep(1)
    box_overlay()
    
def btn_cal_pressed():
#   This is for a physical button press It should clear any previous overlay and snap a new overlay image 
    print("Physical button callibration pressed.")
    mainAlphaSlider.value = 1
    time.sleep(1)
    cal_overlay()

#Define physical button press events
#These could be handled as direct calls to box_overlay and cal_overlay,
#I call an intermediary method to perform addition functions on physical button presses
boxBtn.when_pressed = btn_box_pressed
calBtn.when_pressed = btn_cal_pressed

#############################################################
# Main Code
app = App(title="HollowCam",layout="grid",width=220, height=725)
camera = PiCamera()
camera.hflip = cameraProps['HorizontalFlip']
#position of video window
winXoff = cameraProps['VideoXOffset']
winYoff = cameraProps['VideoYOffset']

# globals
imgW = 0
imgH = 0
calboxX = calboxY=calboxH=calBoxWidth = 0
mainAlpha = 0

# define the box and cal buttons
menu_row = 1
cal_button = PushButton(app, text=" Box ",grid=[0,menu_row],align="left",command=box_overlay)
cal_button.bg = "pink"
cal_button = PushButton(app, text=" Cal ",grid=[1,menu_row],align="left", command=cal_overlay)
cal_button.bg = "yellow"

menu_row = menu_row +1
text = Text(app, text="------------", grid = [0,menu_row],align="left")
text = Text(app, text="------------", grid = [1,menu_row],align="left")

# defne the sliders for the calibration threshold compare value
# and the alpha value used on the the overlay 
menu_row = menu_row +1
text = Text(app, text="Cal", grid = [0,menu_row],align="left")
text = Text(app, text="Overlay", grid = [1,menu_row],align="left")

menu_row = menu_row +1
text = Text(app, text="Thresh", grid = [0,menu_row],align="left")
text = Text(app, text="Transp", grid = [1,menu_row],align="left")

menu_row = menu_row +1
slider = Slider(app, start= -3, end = 3, grid = [0,menu_row],align="left", command=threshold_changed)
slider.value = overlayProps['Threshold']
slider = Slider(app, start= -3, end = 3, grid = [1,menu_row],align="left", command=overlayAlpha_changed)
slider.value = overlayProps['Alpha']

menu_row = menu_row +1
text = Text(app, text="------------", grid = [0,menu_row],align="left")
text = Text(app, text="------------", grid = [1,menu_row],align="left")

menu_row = menu_row +1


text = Text(app, text="WB ", grid = [0,menu_row],align="left")
text = Text(app, text="Res ", grid = [1,menu_row],align="left")


menu_row = menu_row +1
wb_choice = ButtonGroup(app, options=[ ["auto", "auto"],
                                       ["tung", "tungsten"],
                                       ["fluor", "fluorescent"],
                                       ["sun", "sunlight"],
                                       ["shade", "shade"],
                                       ["cloudy", "cloudy"] ],
                        selected=cameraProps['WhiteBalance'],
                        horizontal=False,
                        grid=[0,menu_row],
                        align="left",
                        command=wb_changed)

res_choice = ButtonGroup(app, options=[ ["640x480", 1],
                                        ["960x544", 2],
                                        ["1024x576",3],
                                        ["1280x1024", 4],
                                        ["1024x720", 5]],
                         horizontal=False,
                         grid=[1,menu_row],
                         align="left",
                         selected=cameraProps['VideoResolution'],
                         command=resolution_changed)

menu_row = menu_row +1

text = Text(app, text="Contrast", grid = [1,menu_row],align="left")

slider = Slider(app, start= -3, end = 3, grid = [0,menu_row],align="left", command=contrast_changed)
slider.value = overlayProps['Contrast']

menu_row = menu_row +1
text = Text(app, text="Exposure", grid = [1,menu_row],align="left")
slider = Slider(app, start= -9, end = 9, grid = [0,menu_row],align="left", command=exposure_changed)
slider.value = overlayProps['Exposure']

menu_row = menu_row +1
#text = Text(app, text=" ", grid = [0,7],align="left")
text = Text(app, text="Bright", grid = [1,menu_row],align="left")
slider = Slider(app, start= -3, end = 3, grid = [0,menu_row],align="left", command=bright_changed)
slider.value = overlayProps['Brightness']

menu_row = menu_row +1
ext = Text(app, text="Alpha", grid = [1,menu_row],align="left")
mainAlphaSlider = Slider(app, start= 0, end = 1, grid = [0,menu_row],align="left", command=mainAlpha_changed)
mainAlphaSlider.value = cameraProps['MainAlpha']

menu_row = menu_row +1
quit_button = PushButton(app, text="Quit",grid=[1,menu_row],align="right",command=app_done)
quit_button.bg = "red"

# Dont change this order Must select resolution First
resolution_changed()
mainAlpha_changed(DEFAULT_ALPHA)
# prevOn()

app.display()

