import serial
import threading
import queue
import numpy as np
import time

class SerialController:
    def __init__(self):
        self.serial = None
        self.running = threading.Event()
        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()
        self.recv_buffer = bytearray()
        self.recv_cond = threading.Condition()

    def _send_worker(self):
        while self.running.is_set():
            item = self.send_queue.get()
            if (not self.running.is_set()) or (not self.serial.isOpen()):
                break
            try:
                self.serial.write(item)
            except Exception as ex:
                print("send worker exception: ", ex)
                break
    
    def _recv_worker(self):
        # wait for frame start mark
        self.serial.reset_input_buffer()
        while True:
            rxbuf = self.serial.read_all()
            if len(rxbuf) > 0:
                self.recv_buffer.extend(rxbuf)
                #print("PSIZE: ", len(rxbuf), "\t|\tQSIZE: ", len(self.recv_buffer))
                with self.recv_cond:
                    self.recv_cond.notify()
            else:
                time.sleep(0.001)
            #self.recv_queue.put(rxbuf)
            #self.recv_pipe_w.send_bytes(rxbuf)
            
    def connect(self, device, baudrate):
        try:
            self.serial = serial.Serial(device, baudrate=baudrate)
            if self.serial.isOpen():
                self.running.set()
                self.send_thread = threading.Thread(target=self._send_worker)
                #self.recv_thread = threading.Thread(target=self._recv_worker)
                self.send_thread.start()
                #self.recv_thread.start()
                return True
            else:
                return False
        except Exception as ex:
            print("serial error: ", ex)
            return False
    
    def disconnect(self):
        if self.serial is not None:
            self.running.clear()
            self.serial.close()
            return not self.serial.isOpen()
        return False
    
    def is_connected(self):
        return (self.serial is not None) and self.serial.isOpen()
    
    def send_noblock(self, message):
        self.send_queue.put(message)
    
    def read_bytes(self, n=1):
        with self.recv_cond:
            self.recv_cond.wait_for(lambda: len(self.recv_buffer) >= n)
        buf = bytearray(n)
        buf[:] = self.recv_buffer[:n]
        self.recv_buffer[:n] = b''
        return buf
        
