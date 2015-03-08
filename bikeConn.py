#! /usr/bin/python
import serial

ser = serial.Serial('/dev/ttyUSB0')
print ser
while 1:
    s = ser.read(16)
    print s[:-2]
