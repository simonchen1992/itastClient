from urllib import urlencode
import requests
import json
import itast.settings
import itast.utils
import time
import win32api

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

def sdkSetConfig(tags, tx, d):
  # TODO: this method is not implemented in the the server side
  print "SetConfig not implemented"
  return requestJson('/sdk/setconfig' + d + '?' + 'tags=' + str(tags) + '&' + urlencode(tx))

def sdkPrepareTransaction(tx,d):
  return requestJson('/sdk/preparetransaction' + d + '?' + urlencode(tx))

def sdkStartTransaction(amount, tx, d, config):  # changed for asyn way
  foretime = time.time()
  result = requestJson('/sdk/starttransaction' + d + '?' + 'amount=' + str(amount) + '&' + urlencode(tx))
  while result is None:
    if time.time() - foretime <= int(config[1].split('\n')[35][5:], 16)-5:
      print time.time() - foretime
      pass
    else:
      #sdkStopCurrentTransaction(tx, d)
      print time.time() - foretime
  return result

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
    if devicetype == '28004000':
      txverdict.append('PASS')
    if devicetype == '20804000':
      txverdict.append('NT')
    if devicetype == '20004000':
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
  output = [changeamount, amount, txverdict]
  return output


def reset(d, stop, start, resetsupport):  # Input data: device number, startservice and stopservice address, reset support or not
  if resetsupport == 0:
    if sdkResetDevice(d)[0] != '00':
      win32api.ShellExecute(0, 'open', stop, '', '', 1)  # shall be run stop and start executable and then getdevicestate
      time.sleep(4)
      win32api.ShellExecute(0, 'open', start, '', '', 1)  # TODO: connect host with device
      time.sleep(4)
      if sdkGetDeviceState(d)[0] != '00':
        return False
      else:
        return True
    else:
      time.sleep(22)
  if sdkGetDeviceState(d)[0] != '00':
    win32api.ShellExecute(0, 'open', stop, '', '', 1)  # shall be run stop and start executable and then getdevicestate
    time.sleep(4)
    win32api.ShellExecute(0, 'open', start, '', '', 1)  # TODO: connect host with device
    time.sleep(4)
    if sdkGetDeviceState(d)[0] != '00':
      return False
    else:
      return True
  else:
    return True



