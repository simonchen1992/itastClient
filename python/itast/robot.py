import win32com.client
import time
import json
import numpy as np
from os import system
from colorama import init, Fore, Back, Style
#init(autoreset=True)

#  establish robot arm connection
eng = win32com.client.Dispatch("CAO.CaoEngine")
ctrl = eng.Workspaces(0).AddController("", "CaoProv.DENSO.RC8", "", "Server=192.168.96.1")
Marvin = ctrl.AddRobot("Marvin", "")
# suction system initialization
sucflag = ctrl.AddVariable("IO25", "")
# laser initialization
laserflag = ctrl.AddVariable("IO26", "")
laserflag.Value = 1
# end-position-detection initialization
endflag = ctrl.AddVariable("IO10", "")
# add curpos variable
curpos = Marvin.AddVariable("@CURRENT_POSITION")
# add external speed
extspd = Marvin.AddVariable("@EXTSPEED")


#  robot initialization
def init(session, deviceID):
    global terminal, dispenser, robotConf, test_height, test_position, device_orientation, test_speed, offset
    with open("robot_conf.json") as json_file:
        robotConf = json.load(json_file)
    #  fetch robot coordinate from robotConfiguration file
    terminal = robotConf["coordinate"]["dut"]
    dispenser = robotConf["coordinate"]["dispenser"]
    test_height = robotConf["custom"]["test_height"]
    test_position = robotConf["custom"]["test_position"]
    device_orientation = robotConf["custom"]["orientation"]
    sessionID = session['id']
    offset = {}
    for d in deviceID:
        offset[d] = session["dut" + d + "_offset"]
    test_speed = extspd.Value
    setting = raw_input("--------------Please enter the robot setting number if you want to modify--------------\n"
                    "1. Current calibrated 0C position for all listed devices are: \n" + Fore.RED +
                    str([('DUT' + dutID, terminal[dutID]) for dutID in sorted(deviceID)])[1:-1] + Style.RESET_ALL + "\n"
                    "2. Current calibrated dispensers' position are:\n" + Fore.RED +
                    str([('Dispenser' + i, dispenser[i]) for i in sorted(dispenser.keys())])[1:-1] + Style.RESET_ALL + "\n"
                    "3. Current testing heights are: " + Fore.RED + str(test_height) + Style.RESET_ALL +
                    "; Current testing positions are: " + Fore.RED + str(test_position) + Style.RESET_ALL + "\n"
                    "4. Current device orientation is: " + Fore.RED + device_orientation + Style.RESET_ALL + "\n"
                    "5. Current robot speed is: " + Fore.RED + str(test_speed) + Style.RESET_ALL + "\n"
                    "6. Initiate all settings into default.\n" +
                    Style.BRIGHT + "7. Start testing!!" + Style.RESET_ALL + "\n")
    while True:
        if setting == '1':
            return deviceCalibration(session, deviceID)
        elif setting == '2':
            return dispenerCalibration(session, deviceID)
        elif setting == '3':
            return customTestPosition(session, deviceID)
        elif setting == '4':
            return orientSetting(session, deviceID)
        elif setting == '5':
            return speedSetting(session, deviceID)
        elif setting == '6':
            return defaultSetting(session, deviceID)
        elif setting == '7':
            raw_input('Please turn the robot panel to AUTO mode.\n')
            robot_takearm()
        else:
            setting = raw_input()
            continue

# Robot exception handling
def ex_handle():
    try:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        ctrl.Execute('ClearError')
        if system('tasklist|find /i "Cao.exe"') == 0:
          system('taskkill /IM Cao.exe /F')
        raw_input('Press enter to exit')
    except:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        raw_input('Press enter to exit')
    finally:
        exit(1)

#  setting - calibrate device 0C position
def deviceCalibration(s, d):
    dutID = raw_input('Please input Device ID that you want to carlibrate. e.g. 1, 2, ref..\n')
    while dutID not in d:
        dutID = raw_input('Please input Device ID that you want to carlibrate. e.g. 1, 2, ref..\n')
    if raw_input('Do you want to suck another card?\n1. YES\n2. NO\n') == '1':
        rackIn = '1'  # can be choose if it need to be configured by user
        raw_input('Please turn the robot panel to AUTO mode.\n')
        robot_takearm()
        sucflag.Value = 0
        goto_rack(rackIn, device_orientation)
        takecard()
        robot_releasearm()
    raw_input('Please calibrate the parallel between device and card, then calibrate the Z coordinate of DUT1.\n')
    ta = curpos.Value
    z = ta[2]
    raw_input('Please calibrate XY coordinate of DUT%s.\n' %dutID)
    ta = curpos.Value
    x = ta[0]
    y = ta[1]
    # x = float(input('please ipuut X coordinate: '))
    # y = float(input('please ipuut Y coordinate: '))
    # z = float(input('please ipuut Z coordinate: '))
    robotConf["coordinate"]["dut"][dutID][0:3] = [x, y, z]
    with open("robotConf.json", 'w') as json_file:
        json_file.write(json.dumps(robotConf))
    return init(s, d)

#  setting - calibrate dispenser positions
def dispenerCalibration(s, d):
    dispenserID = raw_input('Please input Dispenser ID that you want to carlibrate. e.g. 1, 2, 3, 4\n')
    while dispenserID not in dispenser.keys():
        dispenserID = raw_input('Please input Dispenser ID that you want to carlibrate. e.g. 1, 2, 3, 4\n')
    raw_input('Please calibrate XY coordinate of Dispenser%s.\n' % dispenserID)
    ta = curpos.Value
    x = ta[0]
    y = ta[1]
    robotConf["coordinate"]["dispenser"][dispenserID][0:2] = [x, y]
    with open("robotConf.json", 'w') as json_file:
        json_file.write(json.dumps(robotConf))
    return init(s, d)


# setting - custom testing height vs positions
def customTestPosition(s, d):
    zflag = False
    xyflag = False
    while not zflag:
        Z = raw_input('please enter the testing height: (e.g. 0,2,3,4)\n').split(',')
        Z = list(map(int, Z)) if (Z != ['']) else [0, 1, 2, 3, 4]
        zflag = True
        for i in Z:
            if i not in [0, 1, 2, 3, 4]:
                zflag = False
                break
    while not xyflag:
        XY = raw_input('please enter the testing positions: (e.g. 0,10,13,16,19)\n').split(',')
        XY = list(map(int, XY)) if (XY != ['']) else [0, 10, 13, 16, 19]
        xyflag = True
        for i in XY:
            if i not in [0, 10, 13, 16, 19]:
                xyflag = False
                break
    robotConf["custom"]["test_height"] = Z
    robotConf["custom"]["test_position"] = XY
    with open("robotConf.json", 'w') as json_file:
        json_file.write(json.dumps(robotConf))
    return init(s, d)

#  setting - device orientation
def orientSetting(s, d):
    ort = "Forward" if raw_input("Does the device face to the operator?\n1. YES, it's face to the operator.\n"
                             "2. NO, it's face to the robot.\n") != '2' else "Backward"
    robotConf["custom"]["orientation"] = ort
    with open("robotConf.json", 'w') as json_file:
        json_file.write(json.dumps(robotConf))
    return init(s, d)

#  setting - robot external speed
def speedSetting(s, d):
    # set external speed
    speed = 0
    try:
        while speed <= 0 or speed > 100:
            speed = int(raw_input('Please input the robot external speed (between 0 and 100):\n'))
    except ValueError as e:
        raw_input(e)
        exit(1)
    Marvin.Execute('ExtSpeed', [speed, 100, 100])
    return init(s, d)

#  setting - restore default settings
def defaultSetting(s, d):
    robotConf["custom"]["test_height"] = [0, 2, 3, 4]
    robotConf["custom"]["test_position"] = [0, 10, 13, 16, 19]
    robotConf["interval"] = 1.2
    Marvin.Execute('ExtSpeed', [70, 100, 100])
    robotConf["custom"]["orientation"] = 'Forward'
    with open("robotConf.json", 'w') as json_file:
        json_file.write(json.dumps(robotConf))
    return init(s, d)

#  Robot - take arm authority
def robot_takearm():
    try:
        Marvin.Execute("TakeArm", 0)
        Marvin.Execute("Motor", 1)
        Marvin.Change("Tool1")
    except:
        ex_handle()

#  Robot - release arm authority
def robot_releasearm():
    Marvin.Execute("Motor", 0)
    Marvin.Execute("GiveArm", )

#  Robot - goto Rack(dispenser)
def goto_rack(rack_num):
    global device_orientation
    tolerance = 1 if (device_orientation != 'Forward') else 0  # make up the difference if card is in opposite direction
    try:
        curpos_ta = curpos.Value
        r = dispenser[str(rack_num)]
        r[1] += tolerance  # make up the difference if card is in opposite direction
        if r[1] > 100:
            if curpos_ta[1] > 100:
                pass
            elif curpos_ta[0] > 200:
                Marvin.Move(2, [[300, 200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
            else:
                Marvin.Move(2, [[200, -200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
                Marvin.Move(2, [[300, 200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
        elif r[1] < -100:
            if curpos_ta[1] < -100:
                pass
            elif curpos_ta[0] > 200:
                Marvin.Move(2, [[300, -200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
            else:
                Marvin.Move(2, [[200, 200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
                Marvin.Move(2, [[300, -200, 200, r[3], r[4], r[5]], 'p', '@E'], 'SPEED=30')
        else:
            raise Exception("Not reachable dispenser")
        Marvin.Move(2, [r, 'p', '@E'], 'SPEED=30')
    except:
        ex_handle()

#  Robot - take the card
def takecard():
    try:
        i = 0
        Marvin.Execute("Draw", [2, "V(0, 0, -180)", "speed = 10"])
        while endflag.Value is True:
            Marvin.Execute("Draw", [2, "V(0, 0, -1)", "SPEED = 10"])
        sucflag.Value = 1
        time.sleep(1.5)
        while i < 20:
            Marvin.Execute("Draw", [2, "V(0, 0, 1)", "SPEED = 10"])
            i += 1
        Marvin.Execute("Draw", [2, "V(0, 0, 185)", "speed = 10"])
    except:
        ex_handle()

#  Robot - release the card
def releasecard():
    try:
        Marvin.Execute("Draw", [2, "V( 0, 0, -192)", "speed = 10"])
        sucflag.Value = 0
        Marvin.Execute("Draw", [2, "V( 0, 0, 5)", "speed = 10"])
        time.sleep(1.5)
        Marvin.Execute("Draw", [2, "V( 0, 0, 192)", "speed = 10"])
    except:
        ex_handle()

#  Robot - move to test positions
def goto_DUT(pos, dutID):
    r = pos[1]
    angle = pos[2]
    delta_y = r * np.cos(np.radians(angle - 90)) * (-1)
    delta_x = r * np.sin(np.radians(angle - 90))
    try:
        Marvin.Move(2, [[terminal[dutID][0] + delta_x, terminal[dutID][1] + delta_y, terminal[dutID][2] + 150, terminal[dutID][3], terminal[dutID][4], terminal[dutID][5]], 'p', '@E'], 'SPEED=35')
    except:
        ex_handle()

#  Robot - Moves down!
def goto_DUT_tx(h, dutID):
    try:
        # unit transfer: from cm to mm
        h = h * 10
        ta = curpos.Value
        if h == 0:
            Marvin.Move(2, [[ta[0], ta[1], terminal[dutID][2] + h, ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')
        else:
            Marvin.Move(2, [[ta[0], ta[1], terminal[dutID][2] + h - offset[dutID], ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')
    except:
        ex_handle()

#  Robot - Leave test position
def leave():
    try:
        ta = curpos.Value
        Marvin.Move(2, [[ta[0], ta[1], ta[2] + 150, ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')
    except:
        ex_handle()

#  Generate testing points
def points():
    global device_orientation
    s = 1
    n = 40
    i = 1
    L = []
    for z in test_height:
        if z == 4:
            L.append(['C', 0, 0, 4, '400'])
            break
        for xy in test_position:
            r = 15 if (xy // 10 == 1) else 0
            if xy % 10 == 0:
                angle = 0 if (device_orientation == 'Forward') else 180
            elif xy % 10 == 3:
                angle = 90 if (device_orientation == 'Forward') else 270
            elif xy % 10 == 6:
                angle = 180 if (device_orientation == 'Forward') else 0
            elif xy % 10 == 9:
                angle = 270 if (device_orientation == 'Forward') else 90
            if r == 0:
                dir = 'C'
            elif angle == 0:
                dir = 'E'
            elif angle == 90:
                dir = 'N'
            elif angle == 180:
                dir = 'W'
            elif angle == 270:
                dir = 'S'
            while s < n and s == i:
                L.append([dir, r, angle, z])
                s += 1
                i += 1
                break
            if s != i:
                i += 1
                continue
    return L

# generate points needed for extra testing when there's FAIL in 3
def extraPoints():
    global device_orientation
    device_orientation = 'Forward'
    s = 1
    n = 40
    i = 1
    L = []
    for z in [2]:
        if z == 4:
            L.append(['C', 0, 0, 4, '400'])
            break
        for xy in [10,13,16,19]:
            r = 15 if (xy // 10 == 1) else 0
            if xy % 10 == 0:
                angle = 0 if (device_orientation == 'Forward') else 180
            elif xy % 10 == 3:
                angle = 90 if (device_orientation == 'Forward') else 270
            elif xy % 10 == 6:
                angle = 180 if (device_orientation == 'Forward') else 0
            elif xy % 10 == 9:
                angle = 270 if (device_orientation == 'Forward') else 90
            if r == 0:
                dir = 'C'
            elif angle == 0:
                dir = 'E'
            elif angle == 90:
                dir = 'N'
            elif angle == 180:
                dir = 'W'
            elif angle == 270:
                dir = 'S'
            while s < n and s == i:
                L.append([dir, r, angle, z])
                s += 1
                i += 1
                break
            if s != i:
                i += 1
                continue
    return L

def testUnaddreesPoints():
    goto_rack(1)
    takecard()
    itast.client.requestJson('/robot/testrunDUT1'+ '?' + 'id_test_session=' + str(sessionID))
    goto_rack(2)
    releasecard()

if __name__ == '__main__':
    for p in extraPoints():
        print p

