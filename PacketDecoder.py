import numpy as np

class PacketDecoder:
    @staticmethod
    def byte_unstuff(frame: bytearray) -> bytearray:
        # check if frame length is correct
        frame2 = bytes(frame)
        if len(frame) != 256:
            print("frame length")
            return None
        
        # check if frame marker is correct
        if frame[255] != 0:
            print("frame format")
            return None
        
        # start unstuffing
        index = 0
        for _ in range(256):
            if index == 255:
                break
            new_index = frame[index]
            frame[index] = 0
            index = new_index
        else:
            print(frame2)
            print(frame)
            return None
        
        return frame[1:253]
    
    @staticmethod
    def decode_samples(frame_bytes: bytearray) -> np.uint16:
        if frame_bytes is None:
            return None

        # convert bytes to 12-bit samples
        x0, x1, x2 = np.reshape(np.frombuffer(frame_bytes, dtype=np.uint8), (84, 3)).astype(np.uint16).T
        y0 = (x0 << 4) | (x1 >> 4)
        y1 = ((x1 & 0x0F) << 8) | x2
        
        return np.array((y1, y0))
        
