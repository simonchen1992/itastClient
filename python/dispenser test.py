#!/usr/bin/env python
from urllib import urlencode
from sys import stdin
import itast.settings
import itast.debug
import itast.client
import time
import win32com.client
import numpy as np
import pythoncom
import requests
import win32api
import json
from suds.client import Client

#calibrate 0C position of terminal
a = [-32.4, 312.67, 98, -179.66, -0.4, 0]

def prompt(msg):
  print msg
  return stdin.readline()

def requestJson(query):
  res = requests.get(itast.settings.ITAST_HOST + query)
  return itast.utils.RawToJson(res.text)


#test
# client = Client('http://localhost:50001/TestService')
# print client
#client.service.GetConfig()
# with open('conf.json') as json_file:
#     data = json.load(json_file)
# print data["positions"][0]["dut1"]
# config = itast.client.sdkGetConfig('ref')
# print int(config[1].split('\n')[35][5:],16)
# tx = itast.client.getTx(3)
# print itast.client.sdkStartTransaction(0.01, tx, 'ref', config)



prompt('233')
#/test

#robot initialization
eng = win32com.client.Dispatch("CAO.CaoEngine")
ctrl = None
ctrl = eng.Workspaces(0).AddController("", "CaoProv.DENSO.RC8", "", "Server=192.168.96.1")
Marvin = ctrl.AddRobot("Marvin", "")
try:
    Marvin.Execute("TakeArm", 0)
except pythoncom.com_error, e:
    print e.message
Marvin.Execute("Motor", 1)
Marvin.Change("Tool1")
# suction system initialization
sucflag = ctrl.AddVariable("IO25", "")
# laser initialization
laserflag = ctrl.AddVariable("IO26", "")
laserflag.Value = 1
# end-position-detection initialization
endflag = ctrl.AddVariable("IO10", "")
# add curpos variable
curpos = Marvin.AddVariable("@CURRENT_POSITION")
# set external speed
Marvin.Execute('ExtSpeed', [50,100,100])

#position coordinate
p1 = [0, 0, 15]
p2 = [10, 0, 15]
p3 = [20, 0]
p4 = [30, 0, 15]
p5 = [40, 0]
def point(s, n):
    i = 1
    L = []
    for index in [p1, p3, p4, p5]:
        h = index[0]
        for r in index[1:]:
            for angle in [0, 90, 180, 270]:
            #for angle in [270]:
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

#take card
def rackin():
    i = 0
    Marvin.Move(2, [[-344.7, 422.6, 200, -179.66, -0.4, 0], 'p', '@E'], 'SPEED=10')
    qr1 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    while qr1 == 'QR code not found!':
        qr1 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    Marvin.Execute("Draw", [2, "V( 0, 0, -180)", "speed = 10"])
    while endflag.Value is True:
        Marvin.Execute("Draw",[2, "V(0,0,-1)", "SPEED = 10"])
    sucflag.Value = 1
    time.sleep(2)
    while i < 20:
        Marvin.Execute("Draw", [2, "V(0,0,1)", "SPEED = 10"])
        i += 1
    Marvin.Execute("Draw", [2, "V( 0, 0, 185)", "speed = 10"])
    qr2 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    if qr1 == qr2:
        exit()
    else:
        print qr1 + ' read success'

#release card
def rackout():
    Marvin.Move(2, [[-346.25, 224.66, 200, -179.66, -0.4, 0], 'p', '@E'], 'SPEED=10')
    Marvin.Execute("Draw", [2, "V( 0, 0, -192)", "speed = 10"])
    sucflag.Value = 0
    time.sleep(2)
    Marvin.Execute("Draw", [2, "V( 0, 0, 192)", "speed = 10"])

def robotmov(delta_x, delta_y):
    Marvin.Move(2, [[a[0] + delta_x, a[1] + delta_y, a[2] + 150, a[3], a[4], a[5]], 'p', '@E'], 'SPEED=35')

def robottx(h):
    ta = curpos.Value
    Marvin.Move(2, [[ta[0], ta[1], a[2] + h, ta[3], ta[4], ta[5]], 'p', '@E'], 'SPEED=80')


# Initiate dispenser status
d1 = prompt("card number in card deck 1 is:")
d2 = prompt("card number in card deck 2 is:")
d3 = prompt("card number in card deck 3 is:")
d4 = prompt("card number in card deck 4 is:")
if prompt('Do you want to initialize the dispenser? Enter yes if you want to.').strip('\n') == 'yes':
  itast.client.dispenserInitial(d1,d2,d3,d4)
  prompt('please wait until card deck movement finish (around 20secs)')
  prompt('please put the card in the deck')


for carddeckID in [1]:
  # need to be improved that numbers in the card deck can be defined by engineer.
  for num in range(0,int(d1)):
    try:
        rackin()
    except pythoncom.com_error, e:
        print '\033[1;31;0mRobot error Occured' + e + '\033[0m'
        Marvin.Execute("GiveArm", 0)
        exit()
    itast.client.dispenserMov('1','2.8','up')
    for var in point(1,40):
        txverdict = []
        for times in range(0,7):
            r = var[1]
            h = var[2]
            angle = var[3]
            print 'Now is testing position ' + str(var[2]) + var[4] + " times " + str(times + 1)
            # need to improve, shall be configured of direction by operator
            delta_y = r * np.cos(np.radians(angle-90)) * (-1)
            delta_x = r * np.sin(np.radians(angle-90))
            robotmov(delta_x, delta_y)
            command = prompt('please start transaction').strip('\n')
            if command == 'p':
                break
            if command == 'end':
                Marvin.Execute("GiveArm", 0)
                prompt("test over")
                exit()
            robottx(h)
            time.sleep(1.5)
            #prompt('please leave')
            # result = results[1][5:9]
            # print result
            # txupdate = itast.client.TxVerdict(0.01, result, txverdict, 0, config)
            # txverdict = txupdate[2]
            # print txverdict
    try:
        rackout()
    except pythoncom.com_error, e:
        print '\033[1;31;0mRobot error Occured' + e + '\033[0m'
        Marvin.Execute("GiveArm", 0)
        exit()
    itast.client.dispenserMov('2', '2.8', 'down')
    # prompt("next card")

Marvin.Execute("GiveArm", 0)
prompt("test over")