import ctypes

class struct_pa_sample_spec(ctypes.Structure):
    __slots__ = [
        'format',
        'rate',
        'channels',
    ]

struct_pa_sample_spec._fields_ = [ ('format', ctypes.c_int), 
    ('rate', ctypes.c_uint32), ('channels', ctypes.c_uint8)]
    
pa_sample_spec = struct_pa_sample_spec
error = ctypes.c_int(0)

#TODO fix name showing up correctly
class pulseaudio():
    ss = struct_pa_sample_spec(3, 44100, 2)

    def __init__(self, samplerate=44100, channels=2):
        self.ss.rate = samplerate
        self.ss.channels = channels

        self.pa = ctypes.cdll.LoadLibrary('libpulse-simple.so.0')
        self.pa.strerror.restype = ctypes.c_char_p
        
        self.stream = self.pa.pa_simple_new(None,"Soundboard".encode("ascii"), 1, 
        None, "Soundboard playback".encode("ascii"), ctypes.byref(self.ss), None, None,
        ctypes.byref(error))
        self.pa.pa_simple_flush(self.stream)

    def write(self, buffer):
        self.pa.pa_simple_write(self.stream, buffer, len(buffer), ctypes.byref(error))
    
    def flush(self):
        self.pa.pa_simple_flush(self.stream)