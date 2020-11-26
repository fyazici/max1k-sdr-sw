
import serial
import sys
import time
import threading

class SerialPipe:
    def __init__(self, in_stream, out_stream, recv_bufsize=1024*1024*16, recv_deadline=0.001, write_chunksize=4096):
        self.serial_ = None
        self.in_stream = in_stream
        self.out_stream = out_stream
        self.recv_buffer = bytearray()
        self.recv_cond = threading.Condition()
        self.recv_bufsize = recv_bufsize
        self.recv_deadline = recv_deadline
        self.write_chunksize = write_chunksize
        self.receiver_thread = threading.Thread(target=self.receiver_worker)
        self.writer_thread = threading.Thread(target=self.writer_worker)
        self.sender_thread = threading.Thread(target=self.sender_worker)
        self.stop_flag = threading.Event()
    
    def open(self, port, baudrate):
        self.serial_ = serial.Serial(port, baudrate)
    
    def start(self):
        self.writer_thread.start()
        self.receiver_thread.start()
        self.sender_thread.start()
    
    def join(self):
        self.sender_thread.join()
        self.receiver_thread.join()
        self.writer_thread.join()
    
    def sender_worker(self):
        while not self.stop_flag.is_set():
            cmd = self.in_stream.read(1)
            if cmd == b"\xFF":      # stop reading and exit
                self.stop_flag.set()
            elif cmd == b"\xFE":    # send new phase divider
                phase = self.in_stream.read(4)
                self.serial_.write(phase)

    def receiver_worker(self):
        while not self.stop_flag.is_set():
            buf = self.serial_.read_all()
            if len(buf) != 0:
                if len(self.recv_buffer) < self.recv_bufsize:
                    self.recv_buffer.extend(buf)
                    with self.recv_cond:
                        self.recv_cond.notify()
                    time.sleep(0)
                else:
                    print("PIPE BUFFER OVERFLOW", file=sys.stderr)
            else:
                time.sleep(self.recv_deadline)
        with self.recv_cond:
            self.recv_cond.notify()
    
    def writer_worker(self):
        while not self.stop_flag.is_set():
            with self.recv_cond:
                while not self.stop_flag.is_set() and len(self.recv_buffer) < self.write_chunksize:
                    self.recv_cond.wait(timeout=1)
            
            if not self.stop_flag.is_set():
                self.out_stream.write(self.recv_buffer[:self.write_chunksize])
                self.recv_buffer[:self.write_chunksize] = b""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port")
    parser.add_argument("baudrate")
    args = parser.parse_args()

    s = SerialPipe(sys.stdin.buffer, sys.stdout.buffer)
    s.open(args.port, args.baudrate)
    s.start()
    s.join()
