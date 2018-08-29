import win32com.client
import json
#import itast.client
import time

#  fetch robot coordinate from configuration file
# with open("conf.json") as json_file:
#     data = json.load(json_file)
# dut1 = data["positions"]["dut1"]
# dut2 = data["positions"]["dut2"]
# ref = data["positions"]["ref"]
# c1 = data["positions"]["c1"]
# c2 = data["positions"]["c2"]
# c3 = data["positions"]["c3"]
# c4 = data["positions"]["c4"]

#  robot initialization
def init():
    global ctrl, Marvin, laserflag, endflag, sucflag, curpos
    eng = win32com.client.Dispatch("CAO.CaoEngine")
    ctrl = eng.Workspaces(0).AddController("", "CaoProv.DENSO.RC8", "", "Server=192.168.96.1")
    try:
        ctrl.Execute('ClearError')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        exit()
    print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
    # Marvin = ctrl.AddRobot("Marvin", "")
    # try:
    #     pass
    #     #Marvin.Execute("TakeArm")
    #     #Marvin.Execute("Motor", 1)
    # except:
    #     print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo',0)[1] + '\033[0m'
    #     exit()
    # Marvin.Change("Tool1")
    # # suction system initialization
    # sucflag = ctrl.AddVariable("IO25", "")
    # # laser initialization
    # laserflag = ctrl.AddVariable("IO26", "")
    # laserflag.Value = 1
    # # end-position-detection initialization
    # endflag = ctrl.AddVariable("IO10", "")
    # # add curpos variable
    # curpos = Marvin.AddVariable("@CURRENT_POSITION")
    # # set external speed
    # Marvin.Execute('ExtSpeed', [50,100,100])

def release():
    pass
    #Marvin.Execute("Motor", 0)
    #Marvin.Execute("GiveArm")

def clear():
    try:
        ctrl.Execute('ClearError')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo',0)[1] + '\033[0m'
        exit()



def goto_rack1():
    try:
        curpos_ta = curpos.Value
        if curpos_ta[1] > 100:
            pass
        elif curpos_ta[0] > 200:
            Marvin.Move(2, [[300, 200, 200, c1[3], c1[4], c1[5]], 'p', '@E'], 'SPEED=30')
        else:
            Marvin.Move(2, [[200, -200, 200, c1[3], c1[4], c1[5]], 'p', '@E'], 'SPEED=30')
            Marvin.Move(2, [[300, 200, 200, c1[3], c1[4], c1[5]], 'p', '@E'], 'SPEED=30')
        Marvin.Move(2, [c1, 'p', '@E'], 'SPEED=10')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()

def goto_rack2():
    try:
        curpos_ta = curpos.Value
        if curpos_ta[1] > 100:
            pass
        elif curpos_ta[0] > 200:
            Marvin.Move(2, [[300, 200, 200, c2[3], c2[4], c2[5]], 'p', '@E'], 'SPEED=30')
        else:
            Marvin.Move(2, [[200, -200, 200, c2[3], c2[4], c2[5]], 'p', '@E'], 'SPEED=30')
            Marvin.Move(2, [[300, 200, 200, c2[3], c2[4], c2[5]], 'p', '@E'], 'SPEED=30')
        Marvin.Move(2, [c2, 'p', '@E'], 'SPEED=10')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()

def goto_rack3():
    try:
        curpos_ta = curpos.Value
        if curpos_ta[1] < -100:
            pass
        elif curpos_ta[0] > 200:
            Marvin.Move(2, [[300, -200, 200, c3[3], c3[4], c3[5]], 'p', '@E'], 'SPEED=30')
        else:
            Marvin.Move(2, [[200, 200, 200, c3[3], c3[4], c3[5]], 'p', '@E'], 'SPEED=30')
            Marvin.Move(2, [[300, -200, 200, c3[3], c3[4], c3[5]], 'p', '@E'], 'SPEED=30')
        Marvin.Move(2, [c3, 'p', '@E'], 'SPEED=10')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()

def goto_rack4():
    try:
        curpos_ta = curpos.Value
        if curpos_ta[1] < -100:
            pass
        elif curpos_ta[0] > 200:
            Marvin.Move(2, [[300, -200, 200, c4[3], c4[4], c4[5]], 'p', '@E'], 'SPEED=30')
        else:
            Marvin.Move(2, [[200, 200, 200, c4[3], c4[4], c4[5]], 'p', '@E'], 'SPEED=30')
            Marvin.Move(2, [[300, -200, 200, c4[3], c4[4], c4[5]], 'p', '@E'], 'SPEED=30')
        Marvin.Move(2, [c4, 'p', '@E'], 'SPEED=10')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()

def takecard(session, c):
    try:
        d = 0
        qr1 = itast.client.requestJson('/qrscan/startscan' + str(c))
        while qr1 == 'QR code not found!':
            qr1 = itast.client.requestJson('/qrscan/startscan' + str(c))
        Marvin.Execute("Draw", [2, "V( 0, 0, -180)", "speed = 10"])
        while endflag.Value is True:
            Marvin.Execute("Draw",[2, "V(0,0,-1)", "SPEED = 10"])
        sucflag.Value = 1
        time.sleep(1.5)
        while d < 20:
            Marvin.Execute("Draw", [2, "V(0,0,1)", "SPEED = 10"])
            d += 1
        Marvin.Execute("Draw", [2, "V( 0, 0, 185)", "speed = 10"])
        qr2 = itast.client.requestJson('/qrscan/startscan' + str(c))
        if qr1 == qr2:
            itast.client.getNewLog(session, 0, 'Failure in card pickup', '', '', '')
            exit('failure in card pickup')
        itast.client.getNewLog(session, 0, 'Successful pickup of the card', '', '', '')
        print 'Read success: ' + qr1
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()

def releasecard(session):
    try:
        Marvin.Execute("Draw", [2, "V( 0, 0, -192)", "speed = 10"])
        sucflag.Value = 0
        time.sleep(2)
        Marvin.Execute("Draw", [2, "V( 0, 0, 192)", "speed = 10"])
        itast.client.getNewLog(session, 0, 'Card in position and withdraw', '', '', '')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        Marvin.Execute("GiveArm")
        exit()



def point(s, n):
    i = 1
    L = []
    for index in [p1, p3, p4, p5]:
        h = index[0]
        for r in index[1:]:
            for angle in [0, 90, 180, 270]:
                # for angle in [270]:
                if h == 40:
                    angle = 0
                if angle == 0:
                    if r == 0:
                        dire = 'C'
                    else:
                        dire = 'E'
                if angle == 90:
                    dire = 'N'
                if angle == 180:
                    dire = 'W'
                if angle == 270:
                    dire = 'S'
                if r == index[1] and angle != 0:
                    continue
                while s < n and s == i:
                    L.append([s, r, h, angle, dire])
                    s += 1
                    i += 1
                    break
                if s != i:
                    i += 1
                    continue
    return L

init()