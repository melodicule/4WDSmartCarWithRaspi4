#-*- coding:UTF-8 -*-
import RPi.GPIO as GPIO
import cv2
import pyzbar.pyzbar as pyzbar
import time
import _thread
import requests

#xml文件路径
cascade_path = '/home/pi/Downloads/haarcascade_frontalface_default.xml'

#定义白名单
white_list = ['some names']

#是否发现有效二维码
find_qrcode = True
#是否鸣笛警告
waring = False

#小车电机引脚定义
IN1 = 20
IN2 = 21
IN3 = 19
IN4 = 26
ENA = 16
ENB = 13

#RGB三色灯引脚定义
LED_R = 22
LED_G = 27
LED_B = 24 

#小车按键定义
key = 8

#蜂鸣器引脚定义
buzzer = 8

#循迹红外引脚定义
#TrackSensorLeftPin1 TrackSensorLeftPin2 TrackSensorRightPin1 TrackSensorRightPin2
#      3                 5                  4                   18
TrackSensorLeftPin1  =  3   #定义左边第一个循迹红外传感器引脚为3口
TrackSensorLeftPin2  =  5   #定义左边第二个循迹红外传感器引脚为5口
TrackSensorRightPin1 =  4   #定义右边第一个循迹红外传感器引脚为4口
TrackSensorRightPin2 =  18  #定义右边第二个循迹红外传感器引脚为18口

#超声波引脚定义
EchoPin = 0
TrigPin = 1
#舵机引脚定义
ServoPin = 11

#sm.ms Picture Upload
class SMUploader:
    def __init__(self):
        self.session = requests.Session()
        self.api_key = 'YOUR KEY' #CHANGE HERE

    def upload_sm(self, file):
        url = 'https://sm.ms/api/v2/upload'
        headers = {}
        headers['Authorization'] = self.api_key
        files = {
            'smfile': open(file, 'rb')
        }

        res = self.session.post(url, headers=headers, files=files)
        if res.status_code > 300:
            return False, None
        else:
            json = res.json()
            code = json.get('code')

            if code == 'image_repeated':
                return True, json.get('images')
            elif code == 'success':
                return True, json['data']['url']

    def close(self):
        self.session.close()

#Push to wechat
class ServerChanPush:
    def __init__(self):
        self.url = 'https://sc.ftqq.com/YOUR_URL'  #CHANGE HERE

    def send_message(self, title, content):
        data = {
            'text': title,
            'desp': content
        }
        req = requests.post(url=self.url, data=data)
        print(req.text)

#设置GPIO口为BCM编码方式
GPIO.setmode(GPIO.BCM)

#忽略警告信息
GPIO.setwarnings(False)

#记录舵机当前角度
angle = 90

#打开摄像头
cam = cv2.VideoCapture
#打开级联分类器模型文件
face_cascade = cv2.CascadeClassifier(cascade_path)

#电机引脚初始化为输出模式
#按键引脚初始化为输入模式
#寻迹引脚初始化为输入模式
def init():
    global pwm_ENA
    global pwm_ENB
    global pwm_servo
    GPIO.setup(ENA,GPIO.OUT,initial=GPIO.HIGH)
    GPIO.setup(IN1,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(IN2,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(ENB,GPIO.OUT,initial=GPIO.HIGH)
    GPIO.setup(IN3,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(IN4,GPIO.OUT,initial=GPIO.LOW)
    
    GPIO.setup(key,GPIO.IN)
    GPIO.setup(TrackSensorLeftPin1,GPIO.IN)
    GPIO.setup(TrackSensorLeftPin2,GPIO.IN)
    GPIO.setup(TrackSensorRightPin1,GPIO.IN)
    GPIO.setup(TrackSensorRightPin2,GPIO.IN)
    GPIO.setup(EchoPin,GPIO.IN)
    GPIO.setup(TrigPin,GPIO.OUT)
    GPIO.setup(ServoPin, GPIO.OUT)
    
    #设置pwm引脚和频率为2000hz
    pwm_ENA = GPIO.PWM(ENA, 2000)
    pwm_ENB = GPIO.PWM(ENB, 2000)
    #舵机频率50，每个周期20ms
    pwm_servo = GPIO.PWM(ServoPin, 50)
    pwm_ENA.start(0)
    pwm_ENB.start(0)
    
    
#小车前进   
def run(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)

#小车后退
def back(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)
    
#小车左转   
def left(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)

#小车右转
def right(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)
    
#小车原地左转
def spin_left(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)

#小车原地右转
def spin_right(leftspeed, rightspeed):
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.HIGH)
    pwm_ENA.ChangeDutyCycle(leftspeed)
    pwm_ENB.ChangeDutyCycle(rightspeed)

#小车停止   
def brake():
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)

#小车鸣笛
def whistle():
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(buzzer, GPIO.LOW)
    time.sleep(0.2) 
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(buzzer, GPIO.HIGH)
    time.sleep(0.3)

#鸣笛15s
def whistle_15s():
    #每个线程需要单独设置端口功能
    GPIO.setup(buzzer,GPIO.OUT,initial=GPIO.HIGH)
    start_time = time.time()
    while time.time() - start_time < 15 and warning:
        whistle()



def color_led(red, green, blue):
    GPIO.output(LED_R, red)
    GPIO.output(LED_G, green)
    GPIO.output(LED_B, blue)
    time.sleep(0.5)


def wink():
    GPIO.setup(LED_R, GPIO.OUT)
    GPIO.setup(LED_G, GPIO.OUT)
    GPIO.setup(LED_B, GPIO.OUT)
    while True:
        color_led(0, 0, 255)
        color_led(255, 0, 0)
        color_led(255, 255, 0)



#识别人脸   
def recognition(img):
    faces = face_cascade.detectMultiScale(gray, 1.1, 6)
    #print(faces)
    if len(faces) > 0:
        return True
    else:
        return False

#二维码识别
def scan_qrcode(img):
    barcodes = pyzbar.decode(img)
    barcodeData = None
    found = False
    for barcode in barcodes:
        barcodeData = barcode.data.decode("utf-8")
        print(barcodeData)
        if barcodeData in white_list:
            found = True
            break
    return found, barcodeData


#超声波函数
def Distance():
    GPIO.output(TrigPin,GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(TrigPin,GPIO.HIGH)
    time.sleep(0.000015)
    GPIO.output(TrigPin,GPIO.LOW)

    t3 = time.time()

    while not GPIO.input(EchoPin):
        t4 = time.time()
        if (t4 - t3) > 0.03 :
            return -1


    t1 = time.time()
    while GPIO.input(EchoPin):
        t5 = time.time()
        if(t5 - t1) > 0.03 :
            return -1

    t2 = time.time()
    time.sleep(0.01)
    print ("distance is %f " % (((t2 - t1)* 340 / 2) * 100))
    return ((t2 - t1)* 340 / 2) * 100
    
    

def tracking():
    end = False
    #检测到黑线时循迹模块相应的指示灯亮，端口电平为LOW
    #未检测到黑线时循迹模块相应的指示灯灭，端口电平为HIGH
    TrackSensorLeftValue1  = GPIO.input(TrackSensorLeftPin1)
    TrackSensorLeftValue2  = GPIO.input(TrackSensorLeftPin2)
    TrackSensorRightValue1 = GPIO.input(TrackSensorRightPin1)
    TrackSensorRightValue2 = GPIO.input(TrackSensorRightPin2)
    
    #print(TrackSensorLeftValue1, TrackSensorLeftValue2, TrackSensorRightValue1, TrackSensorRightValue2)
    #四路循迹引脚电平状态
    # 0 0 X 0
    # 1 0 X 0
    # 0 1 X 0
    #以上6种电平状态时小车原地右转
    #处理右锐角和右直角的转动
    if (TrackSensorLeftValue1 == False or TrackSensorLeftValue2 == False) and  TrackSensorRightValue2 == False:
        spin_right(40, 40)
        time.sleep(0.08)
 
    #四路循迹引脚电平状态
    # 0 X 0 0       
    # 0 X 0 1 
    # 0 X 1 0       
    #处理左锐角和左直角的转动
    elif TrackSensorLeftValue1 == False and (TrackSensorRightValue1 == False or  TrackSensorRightValue2 == False):
        spin_left(40, 40)
        time.sleep(0.08)
  
    # 0 X X X
    #最左边检测到
    elif TrackSensorLeftValue1 == False:
        spin_left(30, 30)
     
    # X X X 0
    #最右边检测到
    elif TrackSensorRightValue2 == False:
        spin_right(30, 30)
   
    #四路循迹引脚电平状态
    # X 0 1 X
    #处理左小弯
    elif TrackSensorLeftValue2 == False and TrackSensorRightValue1 == True:
        left(0,40)
   
    #四路循迹引脚电平状态
    # X 1 0 X  
    #处理右小弯
    elif TrackSensorLeftValue2 == True and TrackSensorRightValue1 == False:
        right(30, 0)
   
    #四路循迹引脚电平状态
    # X 0 0 X
    #处理直线
    elif TrackSensorLeftValue2 == False and TrackSensorRightValue1 == False:
        run(40, 40)
    #当为1 1 1 1时，尝试小角度左转找到黑线
    else:
        left(0,10)
        time.sleep(0.002)
        end = True
    return end

#小车返回时左转，需要确认左侧循迹模块是否检测到黑线
def spin_test():
    end = False
    #检测到黑线时循迹模块相应的指示灯亮，端口电平为LOW
    #未检测到黑线时循迹模块相应的指示灯灭，端口电平为HIGH
    LeftValue1  = GPIO.input(TrackSensorLeftPin1)
    LeftValue2  = GPIO.input(TrackSensorLeftPin2)
    RightValue1 = GPIO.input(TrackSensorRightPin1)
    RightValue2 = GPIO.input(TrackSensorRightPin2)
    
    if int(not RightValue2) + int(not LeftValue2) + int(not RightValue1) >= 2:
        end = True
    return end

#将消息推送到公众号
def upload(info, content):
    if not content.endswith('jpg'):
        push = ServerChanPush()
        push.send_message(info, content + '\n\n' + time.asctime(time.localtime()))
    else:
        uploader = SMUploader()
        rt, url = uploader.upload_sm(content)
        uploader.close()
        if rt:
            print(url)
            push = ServerChanPush()
            push.send_message(info, f'![head]({url})')
        
        
def servo_spin(next_angle):
    global angle
    global pwm_servo
    pwm_servo.start(0) #初始占空比
    print(angle, next_angle)
    if next_angle < angle:
        for i in reversed((next_angle, angle)):
            pwm_servo.ChangeDutyCycle(2.5 + 10 * i /180)
            time.sleep(0.02)
    elif next_angle > angle:
        for i in (angle, next_angle):
            pwm_servo.ChangeDutyCycle(2.5 + 10 * i /180)
            time.sleep(0.02)
    angle = next_angle
    time.sleep(1) #等待舵机转向指定角度
    pwm_servo.ChangeDutyCycle(0) #恢复初始占空比



#try/except语句用来检测try语句块中的错误，
#从而让except语句捕获异常信息并处理。
try:
    init()
    servo_spin(30)       
    _thread.start_new_thread(wink, ())
    print('enter loop')
    
    while True:
        ret, frame = cam.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        has_face = recognition(gray)
        if has_face:
            print('finded face')
            find_qrcode = False
            #开始鸣笛
            warning = True
            #鸣笛15s
            _thread.start_new_thread(whistle_15s, ())
            #寻路
            print('go!')
            out_count = 0
            while True:
                ret = int(tracking())
                out_count = ret * (out_count + 1)
                if out_count >= 30: #允许30次试错
                    break
            #巡线完成，停止
            brake()
            #旋转舵机
            servo_spin(75)
            #d停止鸣笛
            warning = False
            
            #识别二维码
            print('begin qrcode scan')
            start_time = time.time()
            while time.time() - start_time < 15:
                ret, frame2 = cam.read()
                gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                find_qrcode, qrcodeData = scan_qrcode(gray)
                if find_qrcode:
                    break
            #返回
            print('begin return')
            if not find_qrcode:
                path = '/home/pi/Pictures/head_portrait.jpg'
                cv2.imwrite(path, frame)
                print('picture saved')
                _thread.start_new_thread(upload, ('新的访客', path))
            else:
                _thread.start_new_thread(upload, ('新的访客', qrcodeData))
            
            
            #转向
            out_count = 0
            while True:
                spin_left(15, 15)
                time.sleep(0.05)
                ret = int(spin_test())
                out_count = ret * (out_count + ret)
                if out_count >= 3: #连续3次至少两个位置检测到黑线
                    break
            
            #略微加速
            run(20, 20)
            
            #返回
            print('go back')
            out_count = 0
            while True:
                tracking()
                dis = Distance()
                ret = int(dis > 5 and dis < 20) #过滤不正常的数据（负值）
                out_count = ret * (out_count + ret)
                
                if out_count >= 3: #连续三次雷达测距值小于20cm
                    print(dis)
                    break

            print('reach begining')
            #再次转向
            out_count = 0
            while True:
                spin_left(15, 15)
                time.sleep(0.05)
                ret = int(spin_test())
                out_count = ret * (out_count + ret)
                if out_count >= 3 #连续3次至少两个位置检测到黑线
                    break
            #停下
            brake()
            #旋转舵机
            servo_spin(30)
            #待机
            time.sleep(10)
        time.sleep(0.1)

  
       
except KeyboardInterrupt:
    print('quit')
    pass

#初始化
pwm_ENA.stop()
pwm_ENB.stop()
pwm_servo.stop()
GPIO.cleanup()


