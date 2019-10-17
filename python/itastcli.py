#!/usr/bin/env python
from sys import stdin
#import itast.settings
#import itast.debug
from itast.client import dbClient, sdkClient, dispenserClient
import itast.qrscan as qrscan
import itast.robot as robot
import time
import json
from colorama import init, Fore, Back, Style
#init(autoreset=True)

db = dbClient()
vcas = sdkClient()
dispenser = dispenserClient()

# read configuration from json file
with open('conf.json') as json_file:
	conf = json.load(json_file)
DEVICELIST = conf["DEVICELIST"]  # list all dutID
QRPORT = conf["portnumber"]["qrscan"]  # port number of qr scanner
cardHeight = conf['cardHeight']
RACK_IN = conf['RACKLIST']['rackin']
RACK_OUT = conf['RACKLIST']['rackout']

def errHandler(msg):
	raw_input(Fore.RED + str(msg) + Style.RESET_ALL)
	exit(1)

def prompt(msg):
	print msg
	return stdin.readline().strip('\n')

# If engineer input a different answer from yes and no, system shall ask this question again
def promptYesNo(msg):
	p = prompt(msg).lower()
	while p not in ['yes', 'no']:
		p = prompt(msg).lower()
	return p

# Fill in the session information
def promptFillSessionData(s):
	s['expedient'] = prompt("Expedient: ")
	s['owner'] = prompt("Testing Engineer: ")
	s['dut1_name'] = prompt("DUT 1 Name (model): ")
	s['dut1_id'] = prompt("DUT 1 ID (or S/N number): ")
	s['dut2_name'] = prompt("DUT 2 Name (model): ")
	s['dut2_id'] = prompt("DUT 2 ID (or S/N number): ")
	s['dutref_name'] = prompt("DUT ref Name (model): ")
	s['dutref_id'] = prompt('DUT ref ID (or part number): ')
	s['dut1_offset'] = prompt("DUT 1 offset(mm) is: ")
	s['dut1_offset'] = 0 if s['dut1_offset'].strip() == '' else s['dut1_offset']
	s['dut2_offset'] = prompt("DUT 2 offset(mm) is: ")
	s['dut2_offset'] = 0 if s['dut2_offset'].strip() == '' else s['dut2_offset']
	if s['dut1_offset'] >= 5 or s['dut2_offset'] >= 5:
		errHandler('The offset shall be smaller than 5mm according to EMV Requirements.')
	s['notes'] = prompt("Any comment or notes shall be here: ")
	s['visa_vtf'] = prompt("Visa VTF(for TA only): ")

# explain test positions from VISA template
def transTestPosition(st):
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
def dispenserInitiate(s):
	d = {}
	print('--------------Please fill in the dispenser setting parameter--------------\n')
	d['1'] = prompt("card number in card deck 1 is:")
	d['2'] = prompt("card number in card deck 2 is:")
	d['3'] = prompt("card number in card deck 3 is:")
	d['4'] = prompt("card number in card deck 4 is:")
	if promptYesNo('Do you want to initialize the dispenser? Enter yes if you want to.').strip('\n') == 'yes':
		dispenser.dispenserInitial(d['1'], d['2'], d['3'], d['4'])
		print 'please wait until card deck movement finish (around 20secs)'
		time.sleep(15)
		prompt('please put the card in the deck')
	if s == 'yes':
		prompt('As this is a new session, you shall put a dummy card at the top')
	return d

# Initialize device configuration
def sdkInitiate(dutID, sessionID):
	vcas.sdkSetConfigToDefault(dutID, sessionID, '0')  # prepare transaction procedure
	return vcas.sdkGetConfig(dutID, sessionID, '0')


# Test run of robot to find unaddressable positions (only care about dut1)
# Take card process of test run need to be improved
# if newSession == 'yes':
#   itast.client.requestJson('/robot/gotoRack1')
#   itast.client.requestJson('/robot/takeCard')
#   #dispenser.dispenserMov('1', cardHeight,'up')
#   itast.client.requestJson('/robot/testrunDUT1'+ '?' + 'id_test_session=' + str(sessionID))
#   itast.client.requestJson('/robot/gotoRack2')
#   itast.client.requestJson('/robot/releaseCard')
#   dispenser.dispenserMov('2', cardHeight, 'down')
#   db.createLog(sessionID,caseID,'Addressing of all positions', '', '', '')
#   session = itast.client.getSession(sessionID)

def main_loop():
	global dutID, caseID, amount, config
	offlineflag = False
	# Initiate the current session
	newSession = prompt('Do you want to create a new session? If yes, please enter yes. If no, please enter the session number:').strip('\n')
	if newSession == 'yes':
		session = db.createSession()
		promptFillSessionData(session)
		session = db.updateSession(session)
	else:
		session = db.getSession(newSession)
	sessionID = session['id']
	# Initialize the robot and calibrate positions for DUTs and dispensers
	robot.init(session, DEVICELIST)
	db.createLog(sessionID, '0', 'Position 0C calibration performed', '', '', '')
	# Initialize dispenser
	cardNumInrack = dispenserInitiate(newSession)
	#  Initialize VCAS configuration
	config = {}
	nonReachPos = {}
	for dutID in DEVICELIST:
		config[dutID] = sdkInitiate(dutID, sessionID)
		# TODO: nonreachpos for robot
		nonReachPos[dutID] = session['dut' + dutID + '_nrpos']

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
			qr1 = qrscan.multiscan(QRPORT[rackIn], 20)
			if qr1 == 'QR code not found!':
				print('Scan failure')
				break
			robot.takecard()
			qr2 = qrscan.startscan(QRPORT[rackIn])
			if qr1 == qr2:
				db.createLog(sessionID, '0', 'Failure in card pickup')  # record log in database
				print ('Failure in card pickup')
				break  # goto next rackIN
			db.createLog(sessionID, '0', 'Card check and identification')  # record log in database
			dispenser.dispenserMov(rackIn, cardHeight, 'up')
			#  get the card information from database
			card = db.getCard(qr1)
			cardID = card['id']

			"""
				If there are multiple devices under test,
				Each card needs to be tested in all devices (Device_Under_Test and Reference_Device)
			"""
			# Traversal for all devices to be test, configured in json file
			for dutID in DEVICELIST:
				vcas.sdkClearLogs(dutID, sessionID, caseID='')
				if defectiveflag:
					break
				if offlineflag:
					vcas.sdkSetConfigToDefault(dutID, sessionID, caseID='')
				#  Initial flags
				breakflag = False  # This flag will be set to true when one position is tested with verdict
				offlineflag = False  # This flag is only used to mark test case in database
				passflag = False  # This flag is to determine if z=2 needs to be tested
				failInthreeflag = False  # This flag is to determine if z=2 needs to be tested
				#  Parameter: Reset transaction parameter, shall be reset after change device
				txOnlineCounter = 0
				amount = 0.01
				#  BAD CASE: SHALL NOT HAPPEN IN REGULAR OPERATION
				if card['active'] != 1:
					break
				#  Get non tested position for each dut
				nonTestPos = transTestPosition(card['positions'])
				if nonReachPos[dutID] is not None:  # or it will raise "None type is not iterable"
					nonTestPos.extend(nonReachPos[dutID])  # the return value of "expend" is None, can only be used in this way
				"""
				  Collect all test positions which is customer by engineer,
				  In this loop will execute test on all required test height-positions for one device
				"""
				#  Traversal for positions
				for pos in robot.points():
					if breakflag:
						break
					#  Parameter: Reset transaction result, shall be reset after robot move position
					posVerdict = []
					attempt = 0
					#  Determine test positions
					NTflag = False
					posID = str(pos[3]) + pos[0]
					for string in nonTestPos:
						if string == posID:
							NTflag = True
					if NTflag and dutID != 'ref':
						continue
					#  Create test case: specified for one test height-position
					case = db.createCase(sessionID, cardID, dutID, posID)
					caseID = case['id']
					#  Special case: MSD and PKI
					if card['MSD'] == 1:
						case['verdict'] = 'NT'
						case['comments'] = 'Test results is NT as device-under-test is a qVSDC-only device (against MSD-only Card)'
						db.updateCase(case)
						continue
					if card['PKI'] == 1:
						case['verdict'] = 'PKI'
						db.updateCase(case)
						continue
					"""
					Each card shall be tested mutilple times in one positions,
					Pass criteria 3 pass in 5 attempt
					"""
					while attempt < 5:
						"""
						  This is common process for all DUT.
						"""
						# execute testing on test height-positions
						print "Testing " + posID + " of card " + str(card['id']) + ' on DUT' + dutID + str(attempt + 1)
						tx = db.createTx(sessionID, caseID, cardID, dutID, posID, '0000')
						txResult = vcas.sdkStartTransactionAsync(dutID, sessionID, caseID, amount, tx, pos)[1][5:9]
						print txResult
						txUpdate = vcas.genVerdict(amount, txResult, posVerdict, txOnlineCounter, config, dutID, sessionID, caseID)
						txOnlineCounter = txUpdate[0]
						amount = txUpdate[1]
						posVerdict = txUpdate[2]
						print posVerdict

						# Deal with 5A31: offline decline
						if txResult == '5A31' and posVerdict == []:
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
								db.createLog(sessionID, caseID, 'Get PASS with Reference Device', '', '', '')
								break
							elif posVerdict.count('NT') >= 1:
							# if reference device cannot deal with online transaction, stop testing until manual investigation
								case['manual'] = '1'
								db.updateCase(case)
								errHandler('Reference device failed')
							elif posID == '4C':   # if all position failure
								print "This card is marked as defective, discard official testing"
								breakflag = True
								defectiveflag = True
								card['defective'] = '1'
								card = db.updateCard(card)
								db.createLog(sessionID, caseID, 'Defective card detected!', '', '', '')
								break
							else:
								break

						"""
						  This process is only for testing device: DUT1, DUT2, etc...
						"""
						# official testing with DUT 1 and 2
						if posVerdict.count('PASS') >= 3:
							if offlineflag:
								case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
												'transaction is attempt to be offline but the outcome is declined offline ' \
												'due to card does not return the Application Expiration Date, Tag 5F24.'
							passflag = True
							case['verdict'] = 'P'
							db.updateCase(case)
							break
						if (posVerdict.count('CF') + posVerdict.count('TF')) >= 3:
							if pos[3] == 3:
								failInthreeflag = True
							if posVerdict.count('CF') >= 3:
								case['verdict'] = 'CF'
								db.updateCase(case)
							else:
								case['verdict'] = 'TF'
								db.updateCase(case)
							break

				# repeat all positions for Z=2 if appears fail in Z=3
				if passflag and failInthreeflag:
					for pos in robot.extraPoints():
						#  Parameter: Reset transaction result, shall be reset after move positions
						posVerdict = []
						attempt = 0
						posID = str(pos[3]) + pos[0]
						#  Create test case: specified for one test height-position
						case = db.createCase(sessionID, cardID, dutID, posID)
						caseID = case['id']
						while attempt < 5:
							print "Testing " + posID + " of card " + str(card['id']) + ' on DUT' + dutID + str(attempt + 1)
							tx = db.createTx(sessionID, caseID, cardID, dutID, posID, '0000')
							txResult = vcas.sdkStartTransactionAsync(dutID, sessionID, caseID, amount, tx, pos)[1][5:9]
							print txResult
							txUpdate = vcas.genVerdict(amount, txResult, posVerdict, txOnlineCounter, config, dutID, sessionID, caseID)
							txOnlineCounter = txUpdate[0]
							amount = txUpdate[1]
							posVerdict = txUpdate[2]
							print posVerdict
							attempt = attempt + 1

							# official testing with DUT 1 and 2
							if posVerdict.count('PASS') >= 3:
								if offlineflag:
									case['comments'] = 'Transaction forced with Online Approval. With a standard amount (i.e. 0.01) ' \
													  'transaction is attempt to be offline but the outcome is declined offline ' \
													  'due to card does not return the Application Expiration Date, Tag 5F24.'
								case['verdict'] = 'P'
								db.updateCase(case)
								break
							if (posVerdict.count('CF') + posVerdict.count('TF')) >= 3:
								if posVerdict.count('CF') >= 3:
									case['verdict'] = 'CF'
									db.updateCase(case)
								else:
									case['verdict'] = 'TF'
									db.updateCase(case)
								break
			robot.goto_rack(rackOut)
			robot.releasecard()
			dispenser.dispenserMov(rackOut, cardHeight, 'down')
			db.createLog(sessionID, caseID, 'Card in position and withdraw', '', '', '')
	robot.robot_releasearm()

if __name__ == '__main__':
  main_loop()
