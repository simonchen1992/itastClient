import threading
import time
from suds.client import Client

# class MyThread(threading.Thread):
#     def __init__(self,func,args=()):
#         super(MyThread,self).__init__()
#         self.func = func
#         self.args = args
#         print type(self.args), self.args
#     def run(self):
#         self.result = self.func(*self.args)
#     def get_result(self):
#         try:
#             return self.result
#         except Exception:
#             return None
#
#
# def foo(a,b,c):
#     time.sleep(5)
#     return a*2,b*2,c*2
# def haha(name):
#     print name
#     print 'function 2 start:', time.ctime()
#
# st = time.ctime()
#
# t = MyThread(foo,args=(1,2,3))
# h = MyThread(haha,args=('movep',))
# t.start()
# print 'function 1 start:',time.ctime()
# t.join(1)
# if t.isAlive():
#     h.start()
# print t.isAlive()
# t.join(9.5)
# print 'function 1 finished:',time.ctime()
# print t.get_result()

#-----------------------------------------------------------------------------------
# url = 'http://localhost:50001/TestService?wsdl'
#
# client = Client(url)
# #print client
# def ResCodetoString(retData):
#     if retData.ReturnCode == 'Successful':
#         return '00'
#     else:
#         return '01'
# import sys
# import logging
# logger = logging.getLogger('suds')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler(sys.stdout))
# print ResCodetoString(client.service.ClearLogs())

#print 'last sent:\n', client.last_sent()
#print 'last recv:\n', client.last_received()
#print client

#-----------------------------------------------------------------------------------
# import random
# def decro(func):
#     def wrapper(b,c,*args):
#         i = 0
#         a = func(*args)
#         while a != 'a' and i < 5:
#             print b,c
#             print a
#             print reset()
#             a = func(*args)
#             i += 1
#         print a
#     return wrapper
# @decro
# def starttx(a,b):
#     print a + b
#     return random.choice('ab')
# def reset():
#     return 'reset'
# starttx(2,3,4,5)

import time

a = time.time()
time.sleep(1)
b = time.time()
print b-a