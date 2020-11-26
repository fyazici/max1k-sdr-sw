import threading

class BytesFIFO:
    def __init__(self, mem_size=65536):
        self.mem = bytearray(mem_size)
        self.mem_size = mem_size
        self.read_index = 0
        self.write_index = 0
        self._count = 0
        self.count_cond = threading.Condition()
    
    def count(self):
        return self._count

    def available(self):
        return self.mem_size - self._count

    def readinto(self, buf):
        n = len(buf)

        with self.count_cond:
            self.count_cond.wait_for(lambda: self.count() >= n)

        till_end = self.mem_size - self.read_index
        if n > till_end:
            buf[:till_end] = self.mem[self.read_index:]
            buf[till_end:n] = self.mem[0:(n - till_end)]
            self.read_index = n - till_end
        else:
            buf[0:n] = self.mem[self.read_index:(self.read_index + n)]
            self.read_index += n
        
        with self.count_cond:
            self._count -= n
            self.count_cond.notify()

        return n
    
    def write(self, buf):
        n = len(buf)

        # return immediately
        if self.available() < n:
            print("fifo full!!")
            return 0
        
        till_end = self.mem_size - self.write_index
        if n > till_end:
            self.mem[self.write_index:] = buf[:till_end]
            self.mem[0:(n - till_end)] = buf[till_end:n]
            self.write_index = n - till_end
        else:
            self.mem[self.write_index:(self.write_index + n)] = buf[0:n]
            self.write_index += n
        
        with self.count_cond:
            self._count += n
            self.count_cond.notify()

        return n
