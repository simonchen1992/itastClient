import win32com.client
import time
import json
import numpy as np
import itast.client as client
from colorama import Fore, Back, Style

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

def clear_error():
    try:
        ctrl.Execute('ClearError')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'
        exit()
    print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + '\033[0m'

#  robot initialization
def init(sessionID, deviceID):
    global terminal, dispenser, data, test_height, test_position, device_orientation, test_speed, offset
    with open("appconfig.json") as json_file:
        data = json.load(json_file)
    #  fetch robot coordinate from appconfigiguration file
    terminal = data["coordinate"]["dut"]
    dispenser = data["coordinate"]["dispenser"]
    test_height = data["custom"]["test_height"]
    test_position = data["custom"]["test_position"]
    device_orientation = data["custom"]["orientation"]
    offset = data["offset"]
    test_speed = extspd.Value
    setting = raw_input("--------------Please enter the robot setting number if you want to modify--------------\n"
                    "1. Current calibrated 0C position for all listed device is: \n" + Fore.RED +
                    str([('DUT' + dutID, terminal[dutID]) for dutID in deviceID])[1:-1] + Style.RESET_ALL + "\n"
                    "2. Current testing heights are: " + Fore.RED + str(test_height) + Style.RESET_ALL +
                    "; Current testing positions are: " + Fore.RED + str(test_position) + Style.RESET_ALL + "\n"
                    "3. Current device orientation is: " + Fore.RED + device_orientation + Style.RESET_ALL + "\n"
                    "4. Current robot speed is: " + Fore.RED + str(test_speed) + Style.RESET_ALL + "\n"
                    "5. Initiate all settings into default.\n" +
                    Style.BRIGHT + "6. Start testing!!" + Style.RESET_ALL + "\n")
    while True:
        if setting == '1':
            return calibrate_setting(sessionID, deviceID)
        elif setting == '2':
            return custom_testposition(sessionID, deviceID)
        elif setting == '3':
            return orientation_setting(sessionID, deviceID)
        elif setting == '4':
            return speed_setting(sessionID, deviceID)
        elif setting == '5':
            return default_setting(sessionID, deviceID)
        elif setting == '6':
            robot_takearm()
            client.getNewLog(sessionID, '', 'DUT1 Position 0C calibration', '', '', '')
            client.getNewLog(sessionID, '', 'reference device Position 0C calibration', '', '', '')
            return device_orientation
        else:
            setting = raw_input()
            continue

#  setting - calibrate device 0C position
def calibrate_setting(s, d):
    dutID = raw_input('Please input Device ID that you want to carlibrate. e.g. 1, 2, ref..\n')
    if raw_input('Do you want to suck another card?\n1. YES\n2. NO\n') == '1':
        rackIn = raw_input('Please enter rackIn dispenser number\n')
        raw_input('Please alter the robot panel to AUTO mode.\n')
        robot_takearm()
        sucflag.Value = 0
        goto_rack(rackIn, device_orientation)
        takecard()
        robot_releasearm()
    raw_input('Please alter the robot panel to MANUAL mode.\n')
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
    data["coordinate"]["dut"][dutID][0:3] = [x, y, z]
    with open("appconfig.json", 'w') as json_file:
        json_file.write(json.dumps(data))
    return init(s, d)

# setting - custom testing height vs positions
def custom_testposition(s, d):
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
    data["custom"]["test_height"] = Z
    data["custom"]["test_position"] = XY
    with open("appconfig.json", 'w') as json_file:
        json_file.write(json.dumps(data))
    return init(s, d)

#  setting - device orientation
def orientation_setting(s, d):
    ort = "Forward" if raw_input("Does the device face to the operator?\n1. YES, it's face to the operator.\n"
                             "2. NO, it's face to the robot.\n") != '2' else "Backward"
    data["custom"]["orientation"] = ort
    with open("appconfig.json", 'w') as json_file:
        json_file.write(json.dumps(data))
    return init(s, d)

#  setting - robot external speed
def speed_setting(s, d):
    # set external speed
    speed = 0
    try:
        while speed <= 0 or speed > 100:
            speed = int(raw_input('Please input the robot external speed (between 0 and 100):\n'))
    except ValueError as e:
        print(e)
        print('\033[1;31;0mTry to only enter a number/float.\n')
        raw_input()
    Marvin.Execute('ExtSpeed', [speed, 100, 100])
    return init(s, d)

#  setting - restore default settings
def default_setting(s, d):
    data["custom"]["test_height"] = [0, 2, 3, 4]
    data["custom"]["test_position"] = [0, 10, 13, 16, 19]
    data["interval"] = 1.2
    Marvin.Execute('ExtSpeed', [70, 100, 100])
    data["custom"]["orientation"] = 'Forward'
    with open("appconfig.json", 'w') as json_file:
        json_file.write(json.dumps(data))
    return init(s, d)

#  Robot - take arm authority
def robot_takearm():
    try:
        Marvin.Execute("TakeArm", 0)
        Marvin.Execute("Motor", 1)
        Marvin.Change("Tool1")
    except:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        ctrl.Execute('ClearError')
        exit()

#  Robot - release arm authority
def robot_releasearm():
    Marvin.Execute("Motor", 0)
    Marvin.Execute("GiveArm", )

def clear():
    try:
        ctrl.Execute('ClearError')
    except:
        print '\033[1;31;0mRobot error Occured: ' + ctrl.Execute('GetCurErrorinfo',0)[1] + '\033[0m'
        exit()

#  Robot - goto Rack(dispenser)
def goto_rack(rack_num, ort):
    tolerance = 1 if (ort != 'Forward') else 0  # make up the difference if card is in opposite direction
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
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        Marvin.Execute("GiveArm")
        exit()

#  Robot - take the card
def takecard():
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

#  Robot - release the card
def releasecard():
    try:
        Marvin.Execute("Draw", [2, "V( 0, 0, -192)", "speed = 10"])
        sucflag.Value = 0
        time.sleep(1.5)
        Marvin.Execute("Draw", [2, "V( 0, 0, 192)", "speed = 10"])
    except:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        Marvin.Execute("GiveArm")
        exit()

#  Robot - move to test positions
def goto_DUT(pos, dutID):
    r = pos[1]
    angle = pos[2]
    delta_y = r * np.cos(np.radians(angle - 90)) * (-1)
    delta_x = r * np.sin(np.radians(angle - 90))
    try:
        Marvin.Move(2, [[terminal[dutID][0] + delta_x, terminal[dutID][1] + delta_y, terminal[dutID][2] + 150, terminal[dutID][3], terminal[dutID][4], terminal[dutID][5]], 'p', '@E'], 'SPEED=35')
    except:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        ctrl.Execute('ClearError')
        exit()

#  Robot - Moves down!
def goto_DUT_tx(h, dutID):
    try:
        ta = curpos.Value
        if h == 0:
            Marvin.Move(2, [[ta[0], ta[1], terminal[dutID][2] + h, ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')
        else:
            Marvin.Move(2, [[ta[0], ta[1], terminal[dutID][2] + h - offset[dutID], ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')
    except:
        print(Fore.RED + 'Robot error Occured: ' + ctrl.Execute('GetCurErrorinfo', 0)[1] + Style.RESET_ALL)
        ctrl.Execute('ClearError')
        exit()

#  Generate testing points
def points(s, n, ort):
    i = 1
    L = []
    for z in test_height:
        if z == 4:
            L.append(['C', 0, 0, 4, '400'])
            break
        for xy in test_position:
            r = 15 if (xy // 10 == 1) else 0
            if xy % 10 == 0:
                angle = 0 if (ort == 'Forward') else 180
            elif xy % 10 == 3:
                angle = 90 if (ort == 'Forward') else 270
            elif xy % 10 == 6:
                angle = 180 if (ort == 'Forward') else 0
            elif xy % 10 == 9:
                angle = 270 if (ort == 'Forward') else 90
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
                L.append([dir, r, angle, z, str(z)+str(xy).zfill(2)])
                s += 1
                i += 1
                break
            if s != i:
                i += 1
                continue
    return L

if __name__ == '__main__':
    init('1', ['1','ref'])
