from urllib import urlencode
import requests
import os
import json
import itast.settings
import itast.utils
import time
import win32api
import threading
from colorama import init, Fore, Back, Style
#init(autoreset=True)

# General

confPath = os.path.abspath(os.path.dirname(os.getcwd()))
with open(confPath + '/conf.json') as json_file:
    conf = json.load(json_file)

def raiseEx(msg):
    raw_input(Fore.RED + str(msg) + Style.RESET_ALL)
    exit(1)

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

def getNewLog(idsession, idcase, c, a='', code='', vals=''):
    c = {'id_test_session': idsession, 'id_test_case': idcase, 'command': c, 'args': a, 'res_code': code, 'res_vals': vals}
    log = requestJson('/db/logs/new' + '?' + urlencode(c))
    return log[0]

def getLog(id):
    log = requestJson('/db/logs/' + str(id))
    return log[0]

def getLogs(orderfield='id', order='desc', limit=0, start=0):
    logs = requestJson('/db/logs')
    return logs

# SDK

# watchdog modifier
def watchdog(f):
  def exec_vcasCommand(dutID, sessionID, caseID, *args, **kwargs):
      response = f(*args, **kwargs)
      if response[0] != '00':  # prepare transaction procedure
          start = conf["start"]  # start service address
          stop = conf["stop"]  # stop service address
          resetsupport = conf["resetsupport"]  # Device support reset function or not: 0 supported, 1 not supported
          itast.client.getNewLog(sessionID, caseID, 'Execute refresh procedure', '', '', '')
          if not itast.client.reset(dutID, stop, start, resetsupport):
              raiseEx('reset failure')
          response = f(*args, **kwargs)
          if response[0] != '00':
              raiseEx('Cannot receive proper response even after reset procedure.')
      return response
  return exec_vcasCommand

@watchdog
def sdkGetConfig(d):
    return requestJson('/sdk/getconfig'+d)

@watchdog
def sdkSetConfigToDefault(d):
    return requestJson('/sdk/setconfigtodefault' + d)

@watchdog
def sdkSetConfig(tag, value, d):
    return requestJson('/sdk/setconfig' + d + '?' + 'tag=' + str(tag) + '&' + 'value=' + str(value))


def sdkPrepareTransaction(tx,d):
    return requestJson('/sdk/preparetransaction' + d + '?' + urlencode(tx))


def sdkStartTransaction(amount, tx, d):  # changed for asyn way
    return requestJson('/sdk/starttransaction' + d + '?' + 'amount=' + str(amount) + '&' + urlencode(tx))

@watchdog
def sdkStartTransactionAsync(amount, tx, d, pos):
    from itast.robot import goto_DUT_tx, goto_DUT, leave
    max_waiting_rffield = conf['deviceWaitingTime']
    err_response = ['01', '']  # simulate return code 01 and no return value
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
                raiseEx(e)
    def start_tx():
        results = sdkStartTransaction(amount, tx, d)
        return results
    def stop_tx():
        sdkStopCurrentTransaction(tx, d)

    goto_DUT(pos, d)  # Goto test positions
    if sdkPrepareTransaction(tx, d)[0] != '00':
      return err_response
    t1 = MyThread(start_tx, args='')
    t2 = threading.Thread(target=stop_tx, args='')
    t1.start()
    t1.join(max_waiting_rffield)
    goto_DUT_tx(pos[3], d)  # Card falls down
    down_time1 = time.time()
    t1.join(1)
    down_time2 = time.time()
    leave()
    print 'Down Time in test position is: ' + str(down_time2 - down_time1) + ' seconds'
    if t1.isAlive():
        t1.join(13 - 1 - max_waiting_rffield)  # shall be improved: refer to timeout time
        if t1.isAlive():
            t2.start()
            t1.join()
            if t2.isAlive():
                t2.join()
    response = t1.get_result()
    # Deal with EF05: Request reset
    if response[1][5:9] == 'EF05':
        if conf["resetsupport"] == "01":
            raw_input('Please reset the device manually and reconnect the device and webservice!\n')
        else:
            itast.client.sdkResetDevice(d)
            time.sleep(20)
    # GetDebugLogs from last transaction
    if itast.client.sdkGetDebugLog(tx, d)[0] != '00':  # Getdebuglog from last transaction
        return err_response
    return t1.get_result()


def sdkStopCurrentTransaction(tx, d):
    return requestJson('/sdk/stopcurrenttransaction' + d + '?' + urlencode(tx))

def sdkGetDebugLog(tx, d):
    return requestJson('/sdk/getdebuglog' + d + '?' + urlencode(tx))

@watchdog
def sdkClearLogs(tx, d):
    return requestJson('/sdk/clearlogs' + d + '?' + urlencode(tx))

def sdkGetDeviceState(d):
    return requestJson('/sdk/getdevicestate' + d)

def sdkResetDevice(d):
    return requestJson('/sdk/resetdevice' + d)

# case verdict calculation
def genVerdict(amount, result, posVerdict, changeamount, config):  # TODO: EF00
    devicetype = config[1].split('\n')[0][5:]
    if (result == '5931') or (result == '3030'):
        posVerdict.append('PASS')
    elif (result == 'EF03') or (result == 'EF04') or (result == 'EF05') or (result == 'EF00'):
        posVerdict.append('CF')
    elif (result == 'EF01') or (result == 'EF02') or (result == 'EF06'):
        posVerdict.append('TF')
    elif result == '5A31':
        # TODO: use better way get online
        # check if the device is online-capable device
        bstr = bin(int(devicetype[1], 16))[2:]
        l = len(bstr) % 4
        if l > 0:
            bstr = ('0' * (4 - l)) + bstr
        if bstr[0] == '0':
            amtzeroCheck = config[1].split('\n')[9][5:]
            statusCheck = config[1].split('\n')[2][5:]
            floorlimitAmt = config[1].split('\n')[6][5:]
            # check if transaction amount has been changed on this card against device
            if changeamount == 0:
                changeamount = 1
                if amtzeroCheck == '01':
                    amount = 0.00
                elif statusCheck == '00':
                    amount = int(floorlimitAmt)/100 + 1
                else:
                    amount = 1.00
                posVerdict = []
            else:
                posVerdict.append('NT')
    else:
        raiseEx('improper result: ' + str(result))
    return [changeamount, amount, posVerdict]


def reset(d, stop, start, resetsupport):  # Input data: device number, startservice and stopservice address, reset support or not
    for resetChance in range(3):
        if resetsupport == '00':
            resetTime = conf['resetTime']
            resetRes = sdkResetDevice(d)[0]
            time.sleep(resetTime)
            if resetRes != '00':
                pass
            elif sdkGetDeviceState(d)[0] != '00':
                pass
            else:
                return True
        # common process
        raw_input('Please reset the device manually and reconnect the device and webservice!\n')
        if sdkGetDeviceState(d)[0] != '00':
            win32api.ShellExecute(0, 'open', stop, '', '', 1)  # shall be run stop and start executable and then getdevicestate
            time.sleep(4)
            win32api.ShellExecute(0, 'open', start, '', '', 1)  # TODO: connect host with device
            time.sleep(15)
            if sdkGetDeviceState(d)[0] == '00':
                return True
        else:
            return True
    return False

#dispenser
def dispenserInitial(d1, d2, d3, d4):
    initial = {'d1': d1, 'd2': d2, 'd3': d3, 'd4': d4}
    return requestJson('/dispenser/initiate' + '?' + urlencode(initial))

def dispenserMov(id, dis, dir):
    return requestJson('/dispenser/rack' + id + dir + '?' + 'distance=' + dis)

if __name__ == '__main__':
    sdkSetConfig('1', '2', '', {}, 3, 1, '1')
    #sdkPrepareTransaction('1', '2', '', {}, {}, '1')