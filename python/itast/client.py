from urllib import urlencode
import requests
import json
import itast.settings
import itast.utils
import time
import win32api
import threading
import os

def requestJson(query):
  res = requests.get(itast.settings.ITAST_HOST + query)
  return itast.utils.RawToJson(res.text)

# Sessions

def getNewSession():
  session = requestJson('/db/sessions/new')
  return session[0]

def getSession(id):
  session = requestJson('/db/sessions/' + str(id))
  return session[0]

def updateSession(s):
  if s['id']<1:
    return s
  updated = requestJson('/db/sessions/update/' + str(s['id']) + '?' + urlencode(s))
  return updated[0]

def getSessions(orderfield='id', order='desc', limit=0, start=0):
  sessions = requestJson('/db/sessions')
  return sessions

# Cases

def getNewCase(idsession, idcard, d, p, v='Pending'):
  c = {'id_test_session': idsession, 'id_card': idcard, 'dut': d, 'pos': p, 'verdict': v}
  case = requestJson('/db/cases/new' + '?' + urlencode(c))
  return case[0]

def getCase(id):
  case = requestJson('/db/cases/' + str(id))
  return case[0]

def getCases(orderfield='id', order='desc', limit=0, start=0):
  cases = requestJson('/db/cases')
  return cases

def updateCase(c):
  if c['id']<1:
    return c
  updated = requestJson('/db/cases/update/' + str(c['id']) + '?' + urlencode(c))
  return updated[0]

# Tx

def getNewTx(idsession, idcase, idcard, d, p, r, dur=0):
  t = {'id_test_session': idsession, 'id_test_case': idcase ,'id_card': idcard, 'dut': d, 'pos': p, 'res': r, 'duration': dur}
  tx = requestJson('/db/txs/new' + '?' + urlencode(t))
  return tx[0]

def getTx(id):
  tx = requestJson('/db/txs/' + str(id))
  return tx[0]

def getTxs(orderfield='id', order='desc', limit=0, start=0):
  txs = requestJson('/db/tx')
  return txs

def updateTx(t):
  if t['id']<1:
    return t
  updated = requestJson('/db/txs/update/' + str(t['id']) + '?' + urlencode(t))
  return updated[0]

# Cards

def getNewCard():
  card = requestJson('/db/cards/new')
  return card[0]

def getCard(id):
  card = requestJson('/db/cards/' + str(id))
  return card[0]

def getCards(orderfield='id', order='desc', limit=0, start=0):
  cards = requestJson('/db/cards')
  return cards

def updateCard(c):
  if c['id']<1:
    return c
  updated = requestJson('/db/cards/update/' + str(c['id']) + '?' + urlencode(c))
  return updated[0]

# Log

def getNewLog(idsession, idcase, c, a, code, vals):
  c = {'id_test_session': idsession, 'id_test_case': idcase, 'command': c, 'args': a, 'res_code': code, 'res_vals': vals}
  log = requestJson('/db/logs/new' + '?' + urlencode(c))
  return log[0]

def getLog(id):
  log = requestJson('/db/logs/' + str(id))
  return log[0]

def getLogs(orderfield='id', order='desc', limit=0, start=0):
  logs = requestJson('/db/logs')
  return logs

# sdk

def sdkGetConfig(d):
  return requestJson('/sdk/getconfig'+d)

def sdkSetConfigToDefault(d):
  return requestJson('/sdk/setconfigtodefault' + d)

def sdkSetConfig(tag, value, d):
  # TODO: this method is not implemented in the the server side
  print "SetConfig not implemented"
  return requestJson('/sdk/setconfig' + d + '?' + 'tag=' + str(tag) + '&' + 'value=' + str(value))

def sdkPrepareTransaction(tx,d):
  return requestJson('/sdk/preparetransaction' + d + '?' + urlencode(tx))

def sdkStartTransaction(amount, tx, dutID, config, pos, sessionID,caseID, data):  # changed for asyn way
  max_waiting_rffield = 1.5
  from itast.robot import goto_DUT_tx, goto_DUT, leave
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
        print e
  def start_tx():
    results = requestJson('/sdk/starttransaction' + dutID + '?' + 'amount=' + str(amount) + '&' + urlencode(tx))
    return results
  def robot_leave():
    leave()
  def stop_tx():
    exec_vcasCommand("itast.client.sdkStopCurrentTransaction(tx, dutID)", tx, dutID, sessionID,caseID, data)

  goto_DUT(pos, dutID)  # Goto test positions
  exec_vcasCommand("itast.client.sdkPrepareTransaction(tx, dutID)", tx, dutID, sessionID,caseID, data)  # Prepare transaction
  t1 = MyThread(start_tx, args='')
  t3 = threading.Thread(target=stop_tx, args='')
  t1.start()
  t1.join(max_waiting_rffield)
  goto_DUT_tx(pos[3], dutID)  # Card falls down
  print "start test:", time.ctime()
  t1.join(1)
  if t1.isAlive():
    print "moveup:", time.ctime()
    robot_leave()
    t1.join(8)
    if t1.isAlive():
      print "stop test:", time.ctime()
      t3.start()
      t1.join()
  return t1.get_result()

def sdkStopCurrentTransaction(tx, d):
  return requestJson('/sdk/stopcurrenttransaction' + d + '?' + urlencode(tx))

def sdkGetDebugLog(tx, d):
  return requestJson('/sdk/getdebuglog' + d + '?' + urlencode(tx))

def sdkClearLogs(tx, d):
  return requestJson('/sdk/clearlogs' + d + '?' + urlencode(tx))

def sdkGetDeviceState(d):
  return requestJson('/sdk/getdevicestate' + d)

def sdkResetDevice(d):
  return requestJson('/sdk/resetdevice' + d)


# VCAS command watchdog method
def exec_vcasCommand(cmd, tx, dutID, sessionID, caseID, data):
    start = data["start"]  # start service address
    stop = data["stop"]  # stop service address
    resetsupport = data["resetsupport"]  # Device support reset function or not: 0 supported, 1 not supported
    response = []
    exec 'response = %s' % cmd
    while response[0] != '00':  # prepare transaction procedure
        itast.client.getNewLog(sessionID, caseID, 'Execute refresh procedure', '', '', '')
        if itast.client.reset('1', stop, start, resetsupport):
            pass
        else:
            exit('reset failure')
        exec 'response = %s' % cmd
    return response


# robot
def robotDuttx(dutID, Z, offset):
  txposition = {'z': Z, 'dut1_offset': offset}
  return requestJson('/robot/txDUT' + dutID + '?' + urlencode(txposition))

#dispenser
def dispenserInitial(d1, d2, d3, d4):
  initial = {'d1': d1, 'd2': d2, 'd3': d3, 'd4': d4}
  return requestJson('/dispenser/initiate' + '?' + urlencode(initial))

def dispenserMov(id, dis, dir):
  return requestJson('/dispenser/rack' + id + dir + '?' + 'distance=' + dis)

# qr scanner
def qrStartscan():
  return requestJson('/qrscan/startscan')

def qrStopscan():
  return requestJson('/qrscan/stopscan')

# case verdict calculation
def TxVerdict(amount, result, txverdict, changeamount, config):  # TODO: EF00
  devicetype = config[1].split('\n')[0][5:]
  if (result == '5931') or (result == '3030'):
    txverdict.append('PASS')
  elif (result == 'EF03') or (result == 'EF04') or (result == 'EF05'):
    txverdict.append('CF')
  elif (result == 'EF01') or (result == 'EF02') or (result == 'EF06'):
    txverdict.append('TF')
  elif result == '5A31':
    # check if the device is online-capable device
    bstr = bin(int(devicetype[1], 16))[2:]
    l = len(bstr) % 4
    if l > 0:
      bstr = ('0' * (4 - l)) + bstr
    if bstr[0] == '0':
        Amountzerocheck = config[1].split('\n')[9][5:]
        Statuscheck = config[1].split('\n')[2][5:]
        Floorlimit = config[1].split('\n')[6][5:]
        # change changeamount value
        # put manual investigation flag
        if changeamount == 0:
          changeamount = 1
          if Amountzerocheck == '01':
            amount = 0.00
          elif Statuscheck == '00':
            amount = int(Floorlimit)/100 + 1
          else:
            amount = 1.00
          txverdict = []
        else:
          txverdict.append('NT')
  else:
    txverdict.append('improper result: ' + result)
  return [changeamount, amount, txverdict]


def reset(d, stop, start, resetsupport):  # Input data: device number, startservice and stopservice address, reset support or not
  t = 0
  if resetsupport == '00':
    resetRes = sdkResetDevice(d)[0]
    time.sleep(22)
    if resetRes != '00':
      pass
    elif sdkGetDeviceState(d)[0] != '00':
      pass
    else:
      return True
  # common process
  while t <= 3:
    if t > 0:
      raw_input('Please reset the device manually and reconnect the device and webservice!\n')
    if sdkGetDeviceState(d)[0] != '00':
      win32api.ShellExecute(0, 'open', stop, '', '', 1)  # shall be run stop and start executable and then getdevicestate
      time.sleep(4)
     # if os.system('tasklist|find /i "AuthTest_tool.exe"') == 0:
     #   os.system('taskkill /IM AuthTest_tool.exe /F')
      time.sleep(4)
      win32api.ShellExecute(0, 'open', start, '', '', 1)  # TODO: connect host with device
      time.sleep(15)
      if sdkGetDeviceState(d)[0] != '00':
        if t == 3:
          return False
        else:
          t += 1
          continue
      else:
        return True
    else:
      return True




