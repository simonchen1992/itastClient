import MySQLdb
from urllib import urlencode
import requests
import itast.settings
import itast.utils
import time  # trace 1s down time for robot arm
import win32api  # open and close client VCAS
import threading # async way of testing
import os
import json
from colorama import init, Fore, Back, Style
#init(autoreset=True)

#os.system('runas & cd C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190307]_S920\\Host\\VcasStartHostApp & VcasStartHostApp.exe')
#os.system("cd C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190307]_S920\\Host\\VcasStartHostApp & VcasStartHostApp.exe")
#os.system("cd C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190307]_S920\\Host\\VcasStartHostApp & VcasStartHostApp.exe")
#os.system("VcasStartHostApp.exe")
#win32api.ShellExecute(0, 'runas', "VcasStartHostApp.exe", '', 'C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190304]_S920\\Host\\VcasStartHostApp\\', 1)  # shall be run stop and start executable and then getdevicestate
# #win32api.ShellExecute(0, 'open', start, '', '', 1)  # TODO: connect host with device
#raw_input()


class dbClient(object):
	def __init__(self):
		try:
			self.db = MySQLdb.connect(user='itast', passwd='APtsd01$', host='192.168.48.195', db='itast')
		except Exception as e:
			self.errHandle(e)

	def __del__(self):
		self.db.close()

	# General

	def errHandle(self, msg):
		raw_input(Fore.RED + str(msg) + Style.RESET_ALL)
		self.db.rollback()
		self.db.close()
		exit(1)

	def dbSelect(self, table, db_id):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "SELECT * FROM %s WHERE id = %s;" % (table, db_id)
			cursor.execute(sql)
			output = cursor.fetchoneDict()
			cursor.close()
			return output
		except Exception as e:
			self.errHandle(e)

	# Sessions

	def getSession(self, db_id):
		return self.dbSelect('test_sessions', db_id)

	def createSession(self):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "INSERT INTO test_sessions () Values ();"
			cursor.execute(sql)
			lastInsertId = self.db.insert_id()
			self.db.commit()
			cursor.close()
			return self.getSession(lastInsertId)
		except Exception as e:
			self.errHandle(e)

	def updateSession(self, s):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "UPDATE test_sessions SET"
			for key, value in s.items():
				if key not in ['id', 'created', 'timestamp', ] and value not in [None, '']:
					if key in ['dut1_offset', 'dut2_offset', 'dutref_offset', 'official_run']:
						sql += " %s = %s," % (key,value)
					else:
						sql += " %s = '%s'," % (key, value)
			sql = sql[:-1] + ' WHERE id = %s;' % s['id']
			cursor.execute(sql)
			self.db.commit()
			cursor.close()
			return self.getSession(s['id'])
		except Exception as e:
			self.errHandle(e)

	# Logs

	def getLog(self, db_id):
		return self.dbSelect('commands_log', db_id)

	def createLog(self, idsession, idcase, command, arg='', code='', vals=''):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "INSERT INTO commands_log (id_test_session,id_test_case,command,args,res_code,res_vals) " \
				  "Values (%s,%s,'%s','%s','%s','%s');" % (str(idsession), str(idcase), command, arg, code, vals)
			cursor.execute(sql)
			lastInsertId = self.db.insert_id()
			self.db.commit()
			cursor.close()
			return self.getLog(lastInsertId)
		except Exception as e:
			self.errHandle(e)

	# Cards

	def getCard(self, db_id):
		return self.dbSelect('visa_cards', db_id)

	def updateCard(self, c):  # CAN ONLY UPDATE "defective" FIELD, OTHERS ARE FIXED!!!
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "UPDATE visa_cards SET defective = %s WHERE id = %s" % (c['defective'], c['id'])
			cursor.execute(sql)
			self.db.commit()
			cursor.close()
			return self.getCase(c['id'])
		except Exception as e:
			self.errHandle(e)

	# Cases

	def getCase(self, db_id):
		return self.dbSelect('test_cases', db_id)

	def createCase(self, idsession, idcard, dut, pos, v='Pending'):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "INSERT INTO test_cases (id_test_session,id_card,dut,pos,verdict) " \
				  "Values (%s,%s,'%s','%s','%s');" % (str(idsession), str(idcard), dut, pos, v)
			cursor.execute(sql)
			lastInsertId = self.db.insert_id()
			self.db.commit()
			cursor.close()
			return self.getCase(lastInsertId)
		except Exception as e:
			self.errHandle(e)

	def updateCase(self, c):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "UPDATE test_cases SET"
			for key, value in c.items():
				if key not in ['id', 'created', 'timestamp', ] and value not in [None, '']:
					if key in ['id_test_session', 'id_card']:
						sql += " %s = %s," % (key,value)
					else:
						sql += " %s = '%s'," % (key, value)
			sql = sql[:-1] + ' WHERE id = %s;' % c['id']
			cursor.execute(sql)
			self.db.commit()
			cursor.close()
			return self.getCase(c['id'])
		except Exception as e:
			self.errHandle(e)

	# Tx

	def getTx(self, db_id):
		return self.dbSelect('test_txs', db_id)

	def createTx(self, idsession, idcase, idcard, dut, pos, r='0000', dur=0):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "INSERT INTO test_txs (id_test_session,id_test_case,id_card,dut,pos,res,duration) " \
				  "Values (%s,%s,%s,'%s','%s','%s','%s');" % (str(idsession), str(idcase), str(idcard), dut, pos, r, dur)
			cursor.execute(sql)
			lastInsertId = self.db.insert_id()
			self.db.commit()
			cursor.close()
			return self.getTx(lastInsertId)
		except Exception as e:
			self.errHandle(e)

	def updateTx(self, t):
		try:
			cursor = self.db.cursor(cursorclass=MySQLdb.cursors.DictCursor)
			sql = "UPDATE test_txs SET"
			for key, value in t.items():
				if key not in ['id', 'created', 'timestamp', ] and value not in [None, '']:
					if key in ['id_test_session', 'id_test_case' 'id_card']:
						sql += " %s = %s," % (key,value)
					else:
						sql += " %s = '%s'," % (key, value)
			sql = sql[:-1] + ' WHERE id = %s;' % t['id']
			cursor.execute(sql)
			self.db.commit()
			cursor.close()
			return self.getTx(t['id'])
		except Exception as e:
			self.errHandle(e)

# decro function which will used in Class sdkClient
def watchdog(f):
	def exec_vcasCommand(self, dutID, sessionID, caseID, *args, **kwargs):
		response = f(self, dutID, *args, **kwargs)
		if response[0] != '00':  # prepare transaction procedure
			start = self.conf["start"]  # start service address
			stop = self.conf["stop"]  # stop service address
			super(sdkClient, self).createLog(sessionID, caseID, 'Execute refresh procedure')
			if not self.reset(dutID, stop, start, sessionID):
				self.errHandle('reset failure')
			response = f(self, dutID, *args, **kwargs)
			if response[0] != '00':
				self.errHandle('Cannot receive proper response even after reset procedure.')
		return response
	return exec_vcasCommand

class sdkClient(dbClient):
	def __init__(self):
		# initial db object
		super(sdkClient, self).__init__()
		# get conf.json in prior dictionary
		#self.confPath = os.path.abspath(os.path.dirname(os.getcwd()))
		with open('conf.json') as json_file:
			self.conf = json.load(json_file)

	def __del__(self):
		super(sdkClient, self).__del__()

	@classmethod
	def errHandle(self, msg):
		raw_input(Fore.RED + str(msg) + Style.RESET_ALL)
		exit(1)

	@classmethod
	def requestJson(self, query):
		res = requests.get(itast.settings.ITAST_HOST + query)
		return itast.utils.RawToJson(res.text)


	@watchdog
	def sdkGetConfig(self, d):
		return self.requestJson('/sdk/getconfig' + d)

	@watchdog
	def sdkSetConfigToDefault(self, d):
		return self.requestJson('/sdk/setconfigtodefault' + d)

	@watchdog
	def sdkSetConfig(self, d, tag, value):
		return self.requestJson('/sdk/setconfig' + d + '?' + 'tag=' + str(tag) + '&' + 'value=' + str(value))

	def sdkPrepareTransaction(self, d, tx):
		return self.requestJson('/sdk/preparetransaction' + d + '?' + urlencode(tx))

	def sdkStartTransaction(self, d, amount, tx):  # changed for asyn way
		return self.requestJson('/sdk/starttransaction' + d + '?' + 'amount=' + str(amount) + '&' + urlencode(tx))

	@watchdog
	def sdkStartTransactionAsync(self, d, amount, tx, pos):
		from itast.robot import goto_DUT_tx, goto_DUT, leave
		max_waiting_rffield = self.conf['deviceWaitingTime']
		asyncsupport = self.conf["asyncsupport"]  # Device support reset function or not: 0 supported, 1 not supported
		err_response = ['01', '']  # emulate return code 01 and no return value

		# simple rewrite of class threading.Thread to get result from the end of thread.
		class MyThread(threading.Thread):
			def __init__(self, func, args=()):
				threading.Thread.__init__(self)
				self.func = func
				self.args = args
			def run(self):
				self.result = self.func(*self.args)
			def get_result(self):
				try:
					return self.result
				except Exception as e:
					raw_input(Fore.RED + str(e) + Style.RESET_ALL)
					exit(1)

		def start_tx():
			results = self.sdkStartTransaction(d, amount, tx)
			return results

		def stop_tx():
			self.sdkStopCurrentTransaction(d, tx)

		goto_DUT(pos, d)  # Goto test positions
		if self.sdkPrepareTransaction(d, tx)[0] != '00':
			return err_response
		t1 = MyThread(start_tx, args='')
		t2 = threading.Thread(target=stop_tx, args='')
		t1.start()  # Send StartTransaction command to DUT
		t1.join(max_waiting_rffield)  # max_waiting_rffield indicate time between "send StartTransaction()" to "device open its RF field"
		goto_DUT_tx(pos[3], d)  # Card falls down
		downTime1 = time.time()
		t1.join(1)
		downTime2 = time.time()
		leave()
		tx['robotdown'] = time.strftime("%b %d %Y %H:%M:%S", time.localtime(downTime1))
		tx['robotup'] = time.strftime("%b %d %Y %H:%M:%S", time.localtime(downTime2))
		tx['duration'] = downTime2 - downTime1
		super(sdkClient, self).updateTx(tx)
		if t1.isAlive():
			# In sdk guideline 1.6, StartTransactionAsync and StopCurrentTransaction are optional
			if asyncsupport == '00':
				t1.join(13 - 1 - max_waiting_rffield)  # shall be improved: refer to timeout time
				if t1.isAlive():
					t2.start()
					t1.join()
					if t2.isAlive():
						t2.join()
			else:
				t1.join()
		response = t1.get_result()
		# Deal with EF05: Request reset
		if response[1][5:9] == 'EF05':
			self.sdkResetDevice(d)
			time.sleep(self.conf['resetTime'])
		# GetDebugLogs from last transaction
		if self.sdkGetDebugLog(d, tx)[0] != '00':  # Getdebuglog from last transaction
			return err_response
		return t1.get_result()

	def sdkStopCurrentTransaction(self, d, tx):
		return self.requestJson('/sdk/stopcurrenttransaction' + d + '?' + urlencode(tx))

	def sdkGetDebugLog(self, d, tx):
		return self.requestJson('/sdk/getdebuglog' + d + '?' + urlencode(tx))

	@watchdog
	def sdkClearLogs(self, d):
		#return self.requestJson('/sdk/clearlogs' + d + '?' + urlencode(tx))
		return self.requestJson('/sdk/clearlogs' + d)

	def sdkGetDeviceState(self, d):
		return self.requestJson('/sdk/getdevicestate' + d)

	def sdkResetDevice(self, d):
		return self.requestJson('/sdk/resetdevice' + d)

	# case verdict calculation
	def genVerdict(self, amount, retcode, posVerdict, txOnlineCounter, deviceConf, dutID, sessionID, caseID):  # TODO: EF00
		ttq = deviceConf[dutID][1].split('\n')[0][5:]  # from command GetConfig()
		if (retcode == '5931') or (retcode == '3030'):
			posVerdict.append('PASS')
		elif (retcode == 'EF03') or (retcode == 'EF04') or (retcode == 'EF05'):
			posVerdict.append('CF')
		elif (retcode == 'EF01') or (retcode == 'EF02') or (retcode == 'EF06') or (retcode == 'EF00'):
			posVerdict.append('TF')
		elif retcode == '5A31':
			# check if the device is online-capable device, if byte14 set to 1, device is offline-only device
			byte14 = bin(int(ttq[1], 16))[2:]  # [2:] is to remove '0b'
			if len(byte14) % 4 > 0:
				byte14 = ('0' * (4 - len(byte14) % 4)) + byte14
			if byte14[0] == '0':
				posVerdict = []  # reset posVerdict if the device is not offline-only
				# TODO: CANNOT CHANGE TTQ VIA SETCONFIG(), C# setconfig() function does not support UINT32[]
				# # 1st solution to get online: change byte2 bit8 of TTQ
				# if txOnlineCounter == 0:
				# 	ttqTObit = bin(int(ttq, 16))[2:]  # [2:] is to remove '0b'
				# 	ttqTObit = ttqTObit[:8] + '1' + ttqTObit[9:]
				# 	ttqint = int(ttqTObit, 2)
				# 	ttq = hex(int(ttqTObit, 2))[2:]
				# 	self.sdkSetConfig(dutID, sessionID, caseID, tag=1, value=ttqint)
				# 1st solution to get online: enable status check and use amount 1
				if txOnlineCounter == 0:
					self.sdkSetConfigToDefault(dutID, sessionID, caseID)
					self.sdkSetConfig(dutID, sessionID, caseID, tag=3, value=1)
					amount = 1.00
				# 2nd solution to get online: disable cvm limit check and use amount 81
				elif txOnlineCounter == 1:
					self.sdkSetConfigToDefault(dutID, sessionID, caseID)
					self.sdkSetConfig(dutID, sessionID, caseID, tag=11, value=0)
					amount = 81.00
				else:
					self.errHandle('Cannot Get online transaction by all means, please check manually. txOnlineCounter=%s' %txOnlineCounter)
			else:
				posVerdict.append('PASS')  # If device is offline-only, 5A31 can be accepted with PASS verdict
		else:
			self.errHandle('improper result: ' + str(retcode))
		txOnlineCounter += 1
		return [txOnlineCounter, amount, posVerdict]

	def reset(self, d, stop, start, sessionID):  # Input data: device number, startservice and stopservice address, reset support or not
		for resetChance in range(3):
			# ResetDevice() command is mandatory
			resetTime = self.conf['resetTime']
			resetRes = self.sdkResetDevice(d)[0]
			time.sleep(resetTime)
			if resetRes != '00':
				pass
			elif self.sdkGetDeviceState(d)[0] != '00':
				pass
			else:
				return True
			# common process
			#raw_input('Please reset the device manually and reconnect the device and webservice!\n')
			if self.sdkGetDeviceState(d)[0] != '00':
				win32api.ShellExecute(0, 'open', stop[1], '', stop[0], 1)  # shall be run stop and start executable and then getdevicestate
				time.sleep(4)
				win32api.ShellExecute(0, 'open', start[1], '', start[0], 1)  # TODO: connect host with device
				# win32api.ShellExecute(0, 'open', 'VcasStopHostApp.exe', '',
				# 					  'C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190307]_S920\\Host\\VcasStopHostApp\\',
				# 					  1)
				# time.sleep(4)
				# win32api.ShellExecute(0, 'open', "VcasStartHostApp.exe", '', 'C:\\Users\\user\\Desktop\\PAX_PAYWAVE_TA[20190307]_S920\\Host\\VcasStartHostApp\\', 1)  # shall be run stop and start executable and then getdevicestate


				time.sleep(15)
				if self.sdkGetDeviceState(d)[0] == '00':
					return True
			else:
				return True
		return False

class dispenserClient(object):
	# dispenser control
	def dispenserInitial(self, d1, d2, d3, d4):
		initial = {'d1': d1, 'd2': d2, 'd3': d3, 'd4': d4}
		return sdkClient.requestJson('/dispenser/initiate' + '?' + urlencode(initial))
	def dispenserMov(self, id, dis, dir):
		return sdkClient.requestJson('/dispenser/rack' + id + dir + '?' + 'distance=' + str(dis))


if __name__ == '__main__':
	a = dbClient()
	card = a.getCard(1)
	card['defective'] = 0
	a.updateCard(card)