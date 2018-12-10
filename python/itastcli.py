#!/usr/bin/env python
from sys import stdin
import itast.settings
import itast.debug
import itast.client
import itast.qrscan as qrscan
import itast.robot as robot
import time
import json
from colorama import init, Fore, Back, Style
#init(autoreset=True)

RACK_IN = ['1']  # RFU
RACK_OUT = ['2']  # RFU

# read configuration from json file
with open('conf.json') as json_file:
    conf = json.load(json_file)
deviceID = conf["deviceID"]  # list all dutID
portQR = conf["portnumber"]["qrscan1"]  # port number of qr scanner (only care about 1)
cardHeight = conf['cardHeight']

def raiseEx(msg):
    raw_input(Fore.RED + str(msg) + Style.RESET_ALL)
    exit(1)

def prompt(msg):
    print msg
    return stdin.readline()

# If engineer input a different answer from yes and no, system shall ask this question again
def promptyesno(msg):
    p = prompt(msg).strip('\n').lower()
    while p not in ['yes', 'no']:
        p = prompt(msg).strip('\n').lower()
    return p

# Fill in the session information
def promptFillSessionData(s):
    s['expedient'] = prompt("Expedient: ")
    s['owner'] = "Carlos GARCIA"
    s['dut1_name'] = prompt("DUT 1 Name (model): ")
    s['dut1_id'] = prompt("DUT 1 ID (or part number): ")
    s['dut1_description'] = "Testing Device 1"
    s['dut2_name'] = prompt("DUT 2 Name (model): ")
    s['dut2_id'] = prompt("DUT 2 ID (or part number): ")
    s['dut2_description'] = "Testing Device 2"
    s['dutref_name'] = prompt("DUT ref Name (model): ")
    s['dutref_id'] = prompt('DUT ref ID (or part number): ')
    s['dut1_offset'] = prompt("DUT 1 offset(mm) is: ")
    s['dut2_offset'] = prompt("DUT 2 offset(mm) is: ")
    s['notes'] = prompt("Any comment or notes shall be here: ")
    s['visa_vtf'] = prompt("Visa VTF: ")
    s['official_run'] = True

# explain test positions from VISA template
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

# Initiate dispenser status
def dispenser_initiate():
    d = {}
    print('--------------Please fill in the dispenser setting parameter--------------\n')
    d['1'] = prompt("card number in card deck 1 is:")
    d['2'] = prompt("card number in card deck 2 is:")
    d['3'] = prompt("card number in card deck 3 is:")
    d['4'] = prompt("card number in card deck 4 is:")
    if promptyesno('Do you want to initialize the dispenser? Enter yes if you want to.').strip('\n') == 'yes':
        itast.client.dispenserInitial(d['1'], d['2'], d['3'], d['4'])
        print 'please wait until card deck movement finish (around 20secs)'
        time.sleep(15)
        prompt('please put the card in the deck')
    if newSession == 'yes':
        prompt('As this is a new session, you shall put a dummy card at the top')
    return d

# Initialize device configuration
def sdk_initiate(dutID):
    itast.client.sdkSetConfigToDefault(dutID, sessionID, '', dutID)  # prepare transaction procedure
    itast.client.sdkSetConfig(dutID, sessionID, '', 3, 1, dutID)  # disable CVM limit check to force online transaction
    return itast.client.sdkGetConfig(dutID, sessionID, '', dutID)

# Initiate the current session
newSession = prompt('Do you want to create a new session? If yes, please enter yes. If no, please enter the session number:').strip('\n')
if newSession == 'yes':
    session = itast.client.getNewSession()
    promptFillSessionData(session)
    session = itast.client.updateSession(session)
else:
    session = itast.client.getSession(newSession)
sessionID = session['id']


# Test run of robot to find unaddressable positions (only care about dut1)
# Take card process of test run need to be improved
# if newSession == 'yes':
#   itast.client.requestJson('/robot/gotoRack1')
#   itast.client.requestJson('/robot/takeCard')
#   #itast.client.dispenserMov('1', cardHeight,'up')
#   itast.client.requestJson('/robot/testrunDUT1'+ '?' + 'id_test_session=' + str(sessionID))
#   itast.client.requestJson('/robot/gotoRack2')
#   itast.client.requestJson('/robot/releaseCard')
#   itast.client.dispenserMov('2', cardHeight, 'down')
#   itast.client.getNewLog(sessionID,caseID,'Addressing of all positions', '', '', '')
#   session = itast.client.getSession(sessionID)
NRposA = testposition(session['dut1_nrpos'])
print "Not reachable positions are:"
print NRposA

def main_loop():
    global dutID, caseID, amount, config
    # Initialize the robot arm
    robot.init(session, deviceID)
    # Initialize dispenser
    cardNumInrack = dispenser_initiate()
    #  Initialize VCAS configuration
    config = {}
    for dutID in deviceID:
        config[dutID] = sdk_initiate(dutID)

    """
        If there are more than one dispensers as RACK_IN (RACK_OUT must be one now),
        Pick cards for each RAIN_IN dispenser
    """
    #  Traversal for dispensers
    for rackIn, rackOut in zip(RACK_IN, RACK_OUT):
        #  Traversal for cards
        for temp in range(0, int(cardNumInrack[rackIn])):
            #  Flag: Reset defective flag
            defectiveflag = False
            #  Pick up and recognize card by qr scanner
            robot.goto_rack(rackIn)
            qr1 = qrscan.multiscan(portQR, 20)
            itast.client.getNewLog(sessionID, '', 'Card check and identification')  # record log in database
            robot.takecard()
            qr2 = qrscan.startscan(portQR)
            if qr1 == qr2:
                itast.client.getNewLog(sessionID, '', 'Failure in card pickup')  # record log in database
                raiseEx('Failure in card pickup')
            itast.client.getNewLog(sessionID, '', 'Successful pickup of the card')  # record log in database
            itast.client.dispenserMov(rackIn, cardHeight, 'up')
            #  get the card information from database
            card = itast.client.getCard(qr1)
            cardID = card['id']
            NTpos = testposition(card['positions'])
            NTpos.extend(NRposA)  # the return value of "expend" is None, can only be used in this way

            """
                If there are multiple devices under test,
                Each card needs to be tested in all devices (Device_Under_Test and Reference_Device)
            """
            # Traversal for all devices to be test, configured in json file
            for dutID in deviceID:
                if defectiveflag:
                  break
                #  Initial flags
                breakflag = False  # This flag will be set to true when one position is tested with verdict
                offlineflag = False  # This flag is only used to mark test case in database
                passflag = False  # This flag is to determine if z=2 needs to be tested
                failInthreeflag = False  # This flag is to determine if z=2 needs to be tested
                #  Parameter: Reset transaction parameter, shall be reset after change device
                changeamount = 0
                amount = 0.01
                #  BAD CASE: SHALL NOT HAPPEN IN REGULAR OPERATION
                if card['active'] != 1:
                    break
                """
                  Collect all test positions which is customer by engineer,
                  In this loop will execute test on all required test height-positions for one device
                """
                #  Traversal for positions
                for pos in robot.points(1, 40):
                    if breakflag:
                        break
                    #  Parameter: Reset transaction result, shall be reset after robot move position
                    posVerdict = []
                    attempt = 0
                    #  Determine test positions
                    NTflag = False
                    posID = str(pos[3]) + pos[0]
                    for string in NTpos:
                        if string == posID:
                            NTflag = True
                    if NTflag and dutID != 'ref':
                        continue
                    #  Create test case: specified for one test height-position
                    case = itast.client.getNewCase(sessionID, cardID, dutID, posID)
                    caseID = case['id']
                    #  Special case: MSD and PKI
                    if card['MSD'] == 1:
                        case['verdict'] = 'NT'
                        case['comments'] = 'Test results is NT as device-under-test is a qVSDC-only device (against MSD-only Card)'
                        itast.client.updateCase(case)
                        continue
                    if card['PKI'] == 1:
                        case['verdict'] = 'PKI'
                        itast.client.updateCase(case)
                        continue
                    """
                    Each card shall be tested mutilple times in one positions,
                    Pass criteria 5 pass in 7 attempt
                    """
                    while attempt < 7:
                        """
                          This is common process for all DUT.
                        """
                        # execute testing on test height-positions
                        print "Testing " + posID + " of card " + card['id'] + ' on DUT' + dutID + str(attempt + 1)
                        tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
                        result = itast.client.sdkStartTransactionAsync(dutID, sessionID, caseID, amount, tx, dutID, pos)[1][5:9]
                        print result
                        txupdate = itast.client.genVerdict(amount, result, posVerdict, changeamount, config[dutID])
                        changeamount = txupdate[0]
                        amount = txupdate[1]
                        posVerdict = txupdate[2]
                        print posVerdict

                        # Deal with 5A31: offline decline
                        if result == '5A31':
                            offlineflag = True
                            attempt = 0
                            continue
                        attempt = attempt + 1

                        """
                          This process is only for reference device
                        """
                        # card defective test with a reference device
                        if dutID == 'ref':
                            if posVerdict.count('PASS') >= 1:
                                print "this card functions correctly"
                                breakflag = True
                                itast.client.getNewLog(sessionID, caseID, 'Test run completion', '', '', '')
                                break
                            elif posVerdict.count('NT') >= 1:
                            # if reference device cannot deal with online transaction, stop testing until manual investigation
                                case['manual'] = '1'
                                itast.client.updateCase(case)
                                raiseEx('Reference device failed')
                            elif posID == '4C':   # if all position failure
                                print "this card is marked as defective, discard official testing"
                                breakflag = True
                                defectiveflag = True
                                card['defective'] = '1'
                                card = itast.client.updateCard(card)
                                itast.client.getNewLog(sessionID, caseID, 'Test run failure', '', '', '')
                                break
                            else:
                                break

                        """
                          This process is only for testing device: DUT1, DUT2, etc...
                        """
                        # official testing with DUT 1 and 2
                        if posVerdict.count('PASS') >= 5:
                            if offlineflag:
                                case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
                                                'transaction is attempt to be offline but the outcome is declined offline ' \
                                                'due to card does not return the Application Expiration Date, Tag 5F24.'
                            passflag = True
                            case['verdict'] = 'P'
                            itast.client.updateCase(case)
                            break
                        if (posVerdict.count('CF') + posVerdict.count('TF')) >= 3:
                            if pos[3] == 3:
                                failInthreeflag = True
                            if posVerdict.count('CF') >= 3:
                                case['verdict'] = 'CF'
                                itast.client.updateCase(case)
                            else:
                                case['verdict'] = 'TF'
                                itast.client.updateCase(case)
                            break

                # repeat all positions for Z=2 if appears fail in Z=3
                if passflag and failInthreeflag:
                    for posID in ['2W', '2S', '2E', '2N']:
                        #  Parameter: Reset transaction result, shall be reset after move positions
                        posVerdict = []
                        attempt = 0
                        #  Create test case: specified for one test height-position
                        case = itast.client.getNewCase(sessionID, cardID, dutID, posID)
                        caseID = case['id']
                        while attempt < 7:
                            print "Testing " + posID + " of card " + str(card['id']) + ' on DUT' + dutID + str(attempt + 1)
                            tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
                            result = \
                            itast.client.sdkStartTransactionAsync(dutID, sessionID, caseID, amount, tx, dutID, pos)[1][5:9]
                            print result
                            txupdate = itast.client.genVerdict(amount, result, posVerdict, changeamount, config[dutID])
                            changeamount = txupdate[0]
                            amount = txupdate[1]
                            posVerdict = txupdate[2]
                            print posVerdict
                            attempt = attempt + 1

                            # official testing with DUT 1 and 2
                            if posVerdict.count('PASS') >= 5:
                                if offlineflag:
                                    case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
                                                      'transaction is attempt to be offline but the outcome is declined offline ' \
                                                      'due to card does not return the Application Expiration Date, Tag 5F24.'
                                case['verdict'] = 'P'
                                itast.client.updateCase(case)
                                break
                            if (posVerdict.count('CF') + posVerdict.count('TF')) >= 3:
                                if posVerdict.count('CF') >= 3:
                                    case['verdict'] = 'CF'
                                    itast.client.updateCase(case)
                                else:
                                    case['verdict'] = 'TF'
                                    itast.client.updateCase(case)
                                break
            robot.goto_rack(rackOut)
            robot.releasecard()
            itast.client.dispenserMov(rackOut, cardHeight, 'down')
            itast.client.getNewLog(sessionID, caseID, 'Card in position and withdraw', '', '', '')
    robot.robot_releasearm()

if __name__ == '__main__':
  main_loop()
