#!/usr/bin/env python
from urllib import urlencode
from sys import stdin
import itast.settings
import itast.debug
import itast.client
import itast.qrscan as qrscan
import itast.robot as robot
import time
import json

# read configuration from json file
with open('conf.json') as json_file:
    data = json.load(json_file)
start = data["start"]  # start service address
stop = data["stop"]  # stop service address
resetsupport = data["resetsupport"]  # Device support reset function or not: 0 supported, 1 not supported
deviceID = data["deviceID"]  # list all dutID
portQR = data["portnumber"]["qrscan1"]  # port number of qr scanner (only care about 1)

Rack_in_number = ['1']  # RFU
Rack_out_number = ['2']  # RFU

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
    s['dut1_id'] = prompt("DUT 1 ID (or part number): ")
    s['dut1_name'] = prompt("DUT 1 Name (model): ")
    s['dut1_description'] = "Testing Device 1"
    s['dut2_id'] = prompt("DUT 2 ID (or part number): ")
    s['dut2_name'] = prompt("DUT 2 Name (model): ")
    s['dut2_description'] = "Testing Device 2"
    s['dut1_offset'] = prompt("DUT 1 offset(mm) is: ")
    s['dut2_offset'] = prompt("DUT 2 offset(mm) is: ")
    s['notes'] = prompt("Any comment or notes shall be here: ")
    s['visa_vtf'] = prompt("Visa VTF: ")
    s['official_run'] = True

# Initiate the current session
newSession = prompt('Do you want to create a new session? If yes, please enter yes. If no, please enter the session number:').strip('\n')
if newSession == 'yes':
    session = itast.client.getNewSession()
    promptFillSessionData(session)
    session = itast.client.updateSession(session)
else:
    session = itast.client.getSession(newSession)
sessionID = session['id']

# explain test positions to codes
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

# VCAS command watchdog method
def exec_vcasCommand(cmd, tx):
    response = []
    exec 'response = %s' % cmd
    while response[0] != '00':  # prepare transaction procedure
        itast.client.getNewLog(sessionID, caseID, 'Execute refresh procedure', '', '', '')
        if itast.client.reset('1', stop, start, resetsupport):
            pass
        else:
            exit('reset failure')
    return response

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


# Test run of robot to find unaddressable positions (only care about dut1)
# Take card process of test run need to be improved
# if newSession == 'yes':
#   itast.client.requestJson('/robot/gotoRack1')
#   itast.client.requestJson('/robot/takeCard')
#   #itast.client.dispenserMov('1','2.9','up')
#   itast.client.requestJson('/robot/testrunDUT1'+ '?' + 'id_test_session=' + str(sessionID))
#   itast.client.requestJson('/robot/gotoRack2')
#   itast.client.requestJson('/robot/releaseCard')
#   itast.client.dispenserMov('2', '2.8', 'down')
#   itast.client.getNewLog(sessionID,caseID,'Addressing of all positions', '', '', '')
#   session = itast.client.getSession(sessionID)
NRposA = testposition(session['dut1_nrpos'])
print "Not reachable positions are:\n"
print NRposA

# Initialize device configuration
def sdk_initiate(dutID):
    itast.client.sdkSetConfigToDefault(dutID)  # prepare transaction procedure
    itast.client.sdkSetConfig(11, 0, dutID)  # disable CVM limit check to force online transaction
    return itast.client.sdkGetConfig(dutID)

def main_loop():
    global dutID, caseID, amount, config
    # Initialize the robot arm
    device_orientation = robot.init(sessionID, deviceID)
    # Initialize dispenser
    cardInrack = dispenser_initiate()
    #  Initialize VCAS configuration
    config = {}
    for dutID in deviceID:
        config[dutID] = sdk_initiate(dutID)

    """
        If there is mulitiple number of dispenser,
        Divide them into rackIn dispenser and rackOut dispenser
    """
    for rackIn, rackOut in zip(Rack_in_number, Rack_out_number):

        """
        Collect all cards which has been put on rackIn dispenser:
        pick up and recognize the card"""
        for num in range(0, int(cardInrack[rackIn])):
            #  Flag: Reset defective flag
            defectiveflag = False
            #  Pick up and recognize card by qr scanner
            robot.goto_rack(rackIn, device_orientation)
            qr1 = qrscan.multiscan(portQR, 20)
            itast.client.getNewLog(sessionID, '', 'Card check and identification', '', '', '')  # record log in database
            robot.takecard()
            qr2 = qrscan.startscan(portQR)
            if qr1 == qr2:
                itast.client.getNewLog(sessionID, '', 'Failure in card pickup', '', '', '')  # record log in database
                exit()
            itast.client.getNewLog(sessionID, '', 'Successful pickup of the card', '', '', '')  # record log in database
            itast.client.dispenserMov(rackIn, '2.8', 'up')
            #  get the card information from database
            card = itast.client.getCard('175')
            cardID = card['id']
            NTpos = testposition(card['positions'])
            NTpos.extend(NRposA)  # the return value of "expend" is None, can only be used in this way

            """
                If there is multiple device under test,
                Divide them into DUT and reference device
            """
            # Execute for all device listed in json file
            for dutID in deviceID:
                #  defective card shall not be tested by DUT
                if defectiveflag:
                  break
                #  Flag: Reset breakflag flag
                breakflag = False
                # initial offline decline flag, thig flag is only used to mark test case in database
                offlineflag = False
                #  Flag: Reset the flag to determine if 2 is needed to be test
                passflag = False
                failInthreeflag = False
                #  Parameter: Reset transaction parameter, shall be reset after change device
                changeamount = 0
                amount = 0.01
                if card['active'] != 1:
                    break
                """
                  Collect all test positions which is customer by engineer,
                  In this loop will execute test on all required test height-positions for one device
                """
                # pending to check if device is qvsdc only
                for pos in robot.points(1, 40, device_orientation):
                    if breakflag:
                        break
                    #  Parameter: Reset transaction result, shall be reset after move positions
                    txverdict = []
                    attempt = 0
                    #  Determine test positions
                    posID = str(pos[3]) + pos[0]
                    for string in NTpos:
                        if string == posID:
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
                        print "Testing " + posID + " of card " + card['vtf'] + ' on DUT' + dutID + str(attempt + 1)
                        tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
                        robot.goto_DUT(pos, dutID)  # Goto test positions
                        exec_vcasCommand("itast.client.sdkPrepareTransaction(tx, dutID)", tx)  # Prepare transaction
                        robot.goto_DUT_tx(pos[3], dutID)  # Card falls down
                        result = exec_vcasCommand("itast.client.sdkStartTransaction(amount, tx, dutID, config[dutID])", tx)[1][5:9]
                        print result
                        txupdate = itast.client.TxVerdict(amount, result, txverdict, changeamount, config[dutID])
                        changeamount = txupdate[0]
                        amount = txupdate[1]
                        txverdict = txupdate[2]
                        print txverdict
                        exec_vcasCommand("itast.client.sdkGetDebugLog(tx, dutID)", tx)  # Getdebuglog from last transaction
                        # Deal with 5A31: offline decline
                        if result == '5A31':
                            offlineflag = True
                            attempt = 0
                            continue
                        # Deal with EF05: Request reset
                        if result == 'EF05':
                            if resetsupport == "01":
                                prompt('Please reset the device manually and reconnect the device and webservice!')
                            else:
                                itast.client.sdkResetDevice(dutID)
                                time.sleep(20)
                        attempt = attempt + 1

                        """
                          This process is only for reference device
                        """
                        # card defective test with a reference device
                        if dutID == 'ref':
                            if txverdict.count('PASS') >= 1:
                                print "this card functions correctly"
                                breakflag = True
                                itast.client.getNewLog(sessionID, caseID, 'Test run completion', '', '', '')
                                break
                            elif txverdict.count('NT') >= 1:
                            # if reference device cannot deal with online transaction, stop testing until manual investigation
                                case['manual'] = '1'
                                itast.client.updateCase(case)
                                raise Exception('Reference device failed')
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
                        if txverdict.count('PASS') >= 5:
                            if offlineflag:
                                case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
                                                'transaction is attempt to be offline but the outcome is declined offline ' \
                                                'due to card does not return the Application Expiration Date, Tag 5F24.'
                            passflag = True
                            case['verdict'] = 'P'
                            itast.client.updateCase(case)
                            break
                        if (txverdict.count('CF') + txverdict.count('TF')) >= 3:
                            if pos[3] == 3:
                                failInthreeflag = True
                            if txverdict.count('CF') >= 3:
                                case['verdict'] = 'CF'
                                itast.client.updateCase(case)
                            else:
                                case['verdict'] = 'TF'
                                itast.client.updateCase(case)
                            break

                # repeat all positions for Z=2 if appears fail in Z=3
                if passflag and failInthreeflag:
                    for pos in robot.points(1, 40, device_orientation):
                        #  Parameter: Reset transaction result, shall be reset after move positions
                        txverdict = []
                        attempt = 0
                        #  Determine test positions
                        posID = str(pos[3]) + pos[0]
                        if pos[3] != 2:
                            continue
                        #  Create test case: specified for one test height-position
                        case = itast.client.getNewCase(sessionID, cardID, dutID, posID)
                        caseID = case['id']
                        while attempt < 7:
                            print "Testing " + posID + " of card " + str(card['id']) + ' on DUT' + dutID + str(attempt + 1)
                            tx = itast.client.getNewTx(sessionID, caseID, cardID, dutID, posID, '0000')
                            robot.goto_DUT(pos, dutID)  # Goto test positions
                            exec_vcasCommand("itast.client.sdkPrepareTransaction(tx, dutID)", tx)  # Prepare transaction
                            robot.goto_DUT_tx(pos[3], dutID)  # Card falls down
                            result = exec_vcasCommand("itast.client.sdkStartTransaction(amount, tx, dutID, config[dutID])", tx)[1][
                                     5:9]
                            print result
                            txupdate = itast.client.TxVerdict(amount, result, txverdict, changeamount, config[dutID])
                            changeamount = txupdate[0]
                            amount = txupdate[1]
                            txverdict = txupdate[2]
                            print txverdict
                            exec_vcasCommand("itast.client.sdkGetDebugLog(tx, dutID)", tx)  # Getdebuglog from last transaction
                            # Deal with EF05: Request reset
                            if result == 'EF05':
                                if resetsupport == "01":
                                    prompt('Please reset the device manually and reconnect the device and webservice!')
                                else:
                                    itast.client.sdkResetDevice(dutID)
                                    time.sleep(20)
                            attempt = attempt + 1

                            # official testing with DUT 1 and 2
                            if txverdict.count('PASS') >= 5:
                                if offlineflag:
                                    case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
                                                      'transaction is attempt to be offline but the outcome is declined offline ' \
                                                      'due to card does not return the Application Expiration Date, Tag 5F24.'
                                case['verdict'] = 'P'
                                itast.client.updateCase(case)
                                break
                            if (txverdict.count('CF') + txverdict.count('TF')) >= 3:
                                if txverdict.count('CF') >= 3:
                                    case['verdict'] = 'CF'
                                    itast.client.updateCase(case)
                                else:
                                    case['verdict'] = 'TF'
                                    itast.client.updateCase(case)
                                break
            robot.goto_rack(rackOut, device_orientation)
            robot.releasecard()
            itast.client.dispenserMov(rackOut, '2.8', 'down')
            itast.client.getNewLog(sessionID, caseID, 'Card in position and withdraw', '', '', '')

if __name__ == '__main__':
  main_loop()

prompt("test over")