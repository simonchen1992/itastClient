#!/usr/bin/env python
from urllib import urlencode
from sys import stdin
import itast.settings
import itast.debug
import itast.client
import time
import json

with open('conf.json') as json_file:
    data = json.load(json_file)
start = data["start"]  # start service address
stop = data["stop"]  # stop service address
resetsupport = data["resetsupport"]  # Device support reset function or not: 0 supported, 1 not supported

def prompt(msg):
  print msg
  return stdin.readline()

# If engineer input a different answer from yes and no, system shall ask this question again
def promptyesno(msg):
  p = prompt(msg).strip('\n')
  while p != 'yes' and p != 'no':
    p = prompt(msg).strip('\n')
  return p

def promptFillSessionData(s):
  s['expedient'] = prompt("Expedient: ")
  s['owner'] = "Carlos GARCIA"
  s['dut1_id'] = prompt("DUT 1 ID (or part number): ")
  s['dut1_name'] = prompt("DUT 1 Name (model): ")
  s['dut1_description'] = "Testing Device 1"
  s['dut2_id'] = prompt("DUT 2 ID (or part number): ")
  s['dut2_name'] = prompt("DUT 2 Name (model): ")
  s['dut2_description'] = "Testing Device 2"
  s['dut1_offset'] = prompt("DUT 1 offset(mm) is: ")
  s['dut2_offset'] = prompt("DUT 2 offset(mm) is: ")
  s['notes'] = "Created for demo using ITAST Python client"
  s['visa_vtf'] = prompt("Visa VTF: ")
  s['official_run'] = True

def testposition(st):
  ntpos = str(st).replace('NT@', '')
  ntpos = ntpos.replace(' ', '')
  ntpos = ntpos.replace('0A', '0C,0N,0S,0E,0W')
  ntpos = ntpos.replace('1A', '1C,1N,1S,1E,1W')
  ntpos = ntpos.replace('2A', '2C,2N,2S,2E,2W')
  ntpos = ntpos.replace('3A', '3C,3N,3S,3E,3W')
  ntpos = ntpos.replace('4A', '4C,4N,4S,4E,4W')
  ntpos = ntpos.split(',')
  return ntpos
#------------------------------------------

sessionID=0
caseID=0
cardID=1
dutID='1'

# Initiate the current session
s = prompt('Do you want to create a new session? If yes, please enter yes. If no, please enter the session number:').strip('\n')
if s == 'yes':
  session = itast.client.getNewSession()
  promptFillSessionData(session)
  session = itast.client.updateSession(session)
else:
  session = itast.client.getSession(s)
sessionID = session['id']

# Initiate dispenser status
d1 = prompt("card number in card deck 1 is:")
d2 = prompt("card number in card deck 2 is:")
d3 = prompt("card number in card deck 3 is:")
d4 = prompt("card number in card deck 4 is:")
if promptyesno('Do you want to initialize the dispenser? Enter yes if you want to.').strip('\n') == 'yes':
  itast.client.dispenserInitial(d1,d2,d3,d4)
  print 'please wait until card deck movement finish (around 20secs)'
  time.sleep(15)
  prompt('please put the card in the deck')
if s == 'yes':
  prompt('As this is a new session, you shall put a dummy card at the top')

# amount devices on the table and calibrate 0C of all devices
if promptyesno('please calibrate 0C of DUT1, enter yes if it is done.').strip('\n') == 'yes':
  itast.client.getNewLog(sessionID, caseID, 'DUT1 Position 0C calibration', '', '', '')
else:
  exit()
if promptyesno('please calibrate 0C of DUTref, enter yes if it is done.').strip('\n') == 'yes':
  itast.client.getNewLog(sessionID, caseID, 'reference device Position 0C calibration', '', '', '')
else:
  exit()

# Test run of robot to find unaddressable positions (only care about dut1)
# Take card process of test run need to be improved
if s == 'yes':
  itast.client.requestJson('/robot/gotoRack1')
  itast.client.requestJson('/robot/takeCard')
  #itast.client.dispenserMov('1','2.9','up')
  itast.client.requestJson('/robot/testrunDUT1'+ '?' + 'id_test_session=' + str(sessionID))
  itast.client.requestJson('/robot/gotoRack2')
  itast.client.requestJson('/robot/releaseCard')
  itast.client.dispenserMov('2', '2.8', 'down')
  itast.client.getNewLog(sessionID,caseID,'Addressing of all positions', '', '', '')
  session = itast.client.getSession(sessionID)
NRposA = testposition(session['dut1_nrpos'])
print "Not reachable positions are:\n"
print NRposA

# Get device configuration (shall not only care about dut1)
itast.client.sdkSetConfigToDefault(dutID)  # prepare transaction procedure
config = itast.client.sdkGetConfig(dutID)

for carddeckID in [1]:
  # Need to be improved that numbers in the card deck can be defined by engineer.
  for num in range(0,int(d1)):
    itast.client.requestJson('/robot/gotoRack' + str(carddeckID))
    qr1 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    while qr1 == 'QR code not found!':
      qr1 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    itast.client.getNewLog(sessionID, caseID, 'Card check and identification', '', '', '')
    itast.client.requestJson('/robot/takeCard')
    itast.client.dispenserMov('1','2.8','up')
    qr2 = itast.client.requestJson('/qrscan/startscan' + str(carddeckID))
    if qr1 == qr2:
      itast.client.getNewLog(sessionID,caseID,'Failure in card pickup', '', '', '')
      exit()
    itast.client.getNewLog(sessionID, caseID, 'Successful pickup of the card', '', '', '')
    card = itast.client.getCard(qr1)
    positions = card['positions']
    print positions  # for reference only
    #prompt("Please, place " + card['vtf'] + " in Rack IN and take the tested card from Rack OUT.\nThen press [ENTER].")
    cardID = card['id']
    NTpos = testposition(positions)
    NTpos.extend(NRposA)
    print NTpos
    defectiveflag = False

    for dutID in ['1']:  # only one DUT for this session
      if defectiveflag:
        break
      PASS = []
      FAIL = []
      breakflag = False
      changeamount = 0
      amount = 0.01
      if card['active'] != 1:
        break
      # pending to check if device is qvsdc only
      for Z in ['0', '1', '2', '3', '4']:
        if breakflag:
          break
        for XY in ['N', 'S', 'W', 'E', 'C']:
          if breakflag:
            break
          posID = Z + XY  # Simon changed the "XY+Z" into "Z+XY" to fit the NT position in database
          NTflag = False  # initial not tested position flag
          txverdict = []
          tc = 0
          offlineflag = False  # initial offline decline flag
          for string in NTpos:
            if string == posID:
              NTflag = True
          if NTflag:
            if dutID != 'ref':
              continue
          case = itast.client.getNewCase(sessionID, cardID, dutID, posID)
          caseID = case['id']
          if card['MSD'] == 1:
            case['verdict'] = 'NT'
            case['comments'] = 'Test results is NT as device-under-test is a qVSDC-only device (against MSD-only Card)'
            itast.client.updateCase(case)
            continue
          if card['PKI'] == 1:
            case['verdict'] = 'PKI'
            itast.client.updateCase(case)
            continue

          while tc < 7:
            print "Testing " + posID + " of card " + card['vtf'] + ' on DUT' + dutID + str(tc + 1)
            tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
            itast.client.requestJson('/robot/gotoDUT' + dutID + XY)
            while itast.client.sdkPrepareTransaction(tx, dutID)[0] != '00':  # prepare transaction procedure
              if itast.client.reset(dutID, stop, start, resetsupport):
                 pass
              else:
                 exit('reset failure')
            itast.client.robotDuttx(dutID, Z, session['dut1_offset'])  # card falls down, 1s delay in server
            results = itast.client.sdkStartTransaction(amount, tx, dutID, config)
            while results[0] != '00':
              if itast.client.reset(dutID, stop, start, resetsupport):
                pass
              else:
                exit('reset failure')
              results = itast.client.sdkStartTransaction(amount, tx, dutID)
            result = results[1][5:9]
            print result
            if result == 'EF06':  # need to exit from switch interface
              itast.client.sdkStopCurrentTransaction(tx, dutID)

            txupdate = itast.client.TxVerdict(amount, result, txverdict, changeamount, config)
            changeamount = txupdate[0]
            amount = txupdate[1]
            txverdict = txupdate[2]
            print txverdict
            itast.client.sdkGetDebugLog(tx, dutID)

            # card defective test with a reference device
            if dutID == 'ref':
              if txverdict.count('PASS') >= 1:
                print "this card functions correctly"
                breakflag = True
                card['defective'] = '0'
                card = itast.client.updateCard(card)
                itast.client.getNewLog(sessionID, caseID, 'Test run completion', '', '', '')
                break
              if (txverdict.count('CF') + txverdict.count('TF')) >= 1:
                if posID == '4C':
                  print "this card is marked as defective, discard official testing"
                  breakflag = True
                  defectiveflag = True
                  card['defective'] = '1'
                  card = itast.client.updateCard(card)
                  itast.client.getNewLog(sessionID, caseID, 'Test run completion', '', '', '')
                  break
                else:
                  break
              if txverdict.count('NT') >= 1:
                # shall be remove
                breakflag = True
                defectiveflag = True
                case['manual'] = '1'
                case = itast.client.updateCase(case)
                break

            # # Deal with offline decline card
            # if result == '5A31':
            #   offlineflag = True
            #   tc = 0
            #   continue
            # tc = tc + 1

            # temporory method
            if result == '5A31':
              breakflag = True
              tc = 0
              break
            tc = tc + 1

            # official testing with DUT 1 and 2
            if txverdict.count('PASS') >= 5:
              if offlineflag:
                case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) transaction is attempt to be offline but the outcome is declined offline due to card does not return the Application Expiration Date, Tag 5F24.'
              PASS.append(Z)
              case['verdict'] = 'P'
              case = itast.client.updateCase(case)
              break
            if (txverdict.count('CF') + txverdict.count('TF')) >= 3:
              if txverdict.count('CF') >= 3:
                if offlineflag and txverdict.count('PASS') == 0 and len(PASS) == 0:
                  case['manual'] = '1'
                  case['comments'] = 'Due to transcation outcome is "Offline Decline", by following normal procedure, system has tried different possibilities to go online but all of them are failed. Please consider repeating this card with "cvm limit check" deactivated and use amount which is higher than floor limit.'
                  case['verdict'] = 'P'
                  case = itast.client.updateCase(case)
                  breakflag = True
                  break
                FAIL.append(Z)
                case['verdict'] = 'CF'
                case = itast.client.updateCase(case)
              else:
                if offlineflag and txverdict.count('PASS') == 0 and len(PASS) == 0:
                  case['manual'] = '1'
                  case['comments'] = 'Due to transcation outcome is "Offline Decline", by following normal procedure, system has tried different possibilities to go online but all of them are failed. Please consider repeating this card with "cvm limit check" deactivated and use amount which is higher than floor limit.'
                  case['verdict'] = 'P'
                  case = itast.client.updateCase(case)
                  breakflag = True
                  break
                FAIL.append(Z)
                case['verdict'] = 'TF'
                case = itast.client.updateCase(case)
              break

      # repeat all positions for Z=2 if appears fail in Z=3
      if len(PASS) != 0:
        if '3' in FAIL:
          Z = '2'
          for XY in ['N', 'S', 'W', 'E']:
            posID = Z + XY  # Simon changed the "XY+Z" into "Z+XY" to fit the NT position in database
            case = itast.client.getNewCase(sessionID, cardID, dutID, posID)
            caseID = case['id']
            txverdict = []
            tc = 0
            while tc < 7:
              print "Testing " + posID + " of card " + card['vtf'] + ' on DUT' + dutID + str(tc + 1)
              tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
              itast.client.requestJson('/robot/gotoDUT' + dutID + XY)
              while itast.client.sdkPrepareTransaction(tx, dutID)[0] != '00':  # prepare transaction procedure
                if itast.client.reset(dutID, stop, start, resetsupport):
                  pass
                else:
                  exit('reset failure')
              itast.client.robotDuttx(dutID, Z, session['dut1_offset'])  # card falls down, 1s delay in server
              results = itast.client.sdkStartTransaction(amount, tx, dutID, config)
              while results[0] != '00':
                if itast.client.reset(dutID, stop, start, resetsupport):
                  pass
                else:
                  exit('reset failure')
                results = itast.client.sdkStartTransaction(amount, tx, dutID)
              result = results[1][5:9]
              print result
              if result == 'EF06':  # need to exit from switch interface
                itast.client.sdkStopCurrentTransaction(tx, dutID)

              txupdate = itast.client.TxVerdict(amount, result, txverdict, changeamount, config)
              changeamount = txupdate[0]
              amount = txupdate[1]
              txverdict = txupdate[2]
              print txverdict
              itast.client.sdkGetDebugLog(tx, dutID)
              if result == '5A31':
                continue
              tc = tc + 1

              # official testing with DUT 1 and 2
              if txverdict.count('PASS') >= 5:
                PASS.append(Z)
                case['verdict'] = 'P'
                case = itast.client.updateCase(case)
                break
              if (txverdict.count('CF') + txverdict.count('TF')) >= 3:
                if txverdict.count('CF') >= 3:
                  FAIL.append(Z)
                  case['verdict'] = 'CF'
                  case = itast.client.updateCase(case)
                else:
                  FAIL.append(Z)
                  case['verdict'] = 'TF'
                  case = itast.client.updateCase(case)
                break
    itast.client.requestJson('/robot/gotoRack2')
    itast.client.requestJson('/robot/releaseCard')
    itast.client.dispenserMov('2', '2.8', 'down')
    itast.client.getNewLog(sessionID, caseID, 'Card in position and withdraw', '', '', '')

prompt("test over")