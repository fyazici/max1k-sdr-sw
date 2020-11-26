
from tkinter import ttk
from ttkthemes import ThemedTk
import glob

import SerialController
import threading
import numpy as np
import time
import multiprocessing

class App(ttk.Frame):
    BAUDRATE_OPTIONS = (9600, 19200, 115200, 1000000, 2000000, 4000000, 12000000)
    BAUDRATE_DEFAULT_INDEX = 6
    FREQUENCY_UNIT_OPTIONS = {"Hz": 1.0, "kHz": 1000.0, "MHz": 1000000.0}
    FREQUENCY_UNIT_DEFAULT_INDEX = 1
    DDS_DEFAULT_PHASE_FREQ = "360"    # MHz
    DDS_DEFAULT_TARGET_FREQ = "1413"    # kHz
    
    WIDGET_OPTS = dict(padx=5, pady=5, sticky="nsew")

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        
        self.serial_ctrl = SerialController.SerialController()
        self.master.protocol("WM_DELETE_WINDOW", self.handle_cleanup)

        self.pack()
        self.create_widgets()
        self.handle_serial_devices_refresh()

    def handle_cleanup(self):
        self.serial_ctrl.disconnect()
        self.master.destroy()

    def create_widgets(self):

        # Window resize constraints
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Root grid resize constraints
        self.grid(sticky="nsew")
        self.rowconfigure(0, weight=0)  # port settings
        self.rowconfigure(1, weight=1)  # received text
        self.rowconfigure(2, weight=1)  # sent text
        self.rowconfigure(3, weight=0)  # to send
        self.columnconfigure(0, weight=1)

        ###
        # Serial port settings row
        self.nb_serial = ttk.Notebook(self)
        self.nb_serial.grid(row=0, column=0, **App.WIDGET_OPTS)
        self.serial_grid = ttk.Frame(self.nb_serial)
        self.nb_serial.add(self.serial_grid, text="Serial Port Settings")

        self.serial_grid.columnconfigure(0, weight=0)
        self.serial_grid.columnconfigure(1, weight=0)
        self.serial_grid.columnconfigure(2, weight=1)
        self.serial_grid.columnconfigure(3, weight=0)
        self.serial_grid.columnconfigure(4, weight=0)
        self.serial_grid.columnconfigure(5, weight=0)
        self.serial_grid.columnconfigure(6, weight=0)

        self.btn_refresh = ttk.Button(self.serial_grid)
        self.btn_refresh.grid(row=0, column=0, **App.WIDGET_OPTS)
        self.btn_refresh["text"] = "Refresh"
        self.btn_refresh["command"] = self.handle_serial_devices_refresh

        self.lbl_1 = ttk.Label(self.serial_grid, text="Serial Device:")
        self.lbl_1.grid(row=0, column=1, **App.WIDGET_OPTS)

        self.cbx_serial_device = ttk.Combobox(self.serial_grid)
        self.cbx_serial_device.grid(row=0, column=2, **App.WIDGET_OPTS)

        self.lbl_2 = ttk.Label(self.serial_grid, text="Baudrate:")
        self.lbl_2.grid(row=0, column=3, **App.WIDGET_OPTS)

        self.cbx_serial_baudrate = ttk.Combobox(self.serial_grid)
        self.cbx_serial_baudrate["values"] = App.BAUDRATE_OPTIONS
        self.cbx_serial_baudrate.current(App.BAUDRATE_DEFAULT_INDEX)
        self.cbx_serial_baudrate.grid(row=0, column=4, **App.WIDGET_OPTS)

        self.btn_connect = ttk.Button(self.serial_grid)
        self.btn_connect["text"] = "Connect"
        self.btn_connect["command"] = self.handle_connect
        self.btn_connect.grid(row=0, column=5, **App.WIDGET_OPTS)

        self.btn_disconnect = ttk.Button(self.serial_grid)
        self.btn_disconnect["text"] = "Disconnect"
        self.btn_disconnect["command"] = self.handle_disconnect
        self.btn_disconnect.grid(row=0, column=6, **App.WIDGET_OPTS)
        ###

        ###
        # DDS Frequency setting panel
        self.nb_dds = ttk.Notebook(self)
        self.nb_dds.grid(row=1, column=0, **App.WIDGET_OPTS)
        self.dds_grid = ttk.Frame(self.nb_dds)
        self.nb_dds.add(self.dds_grid, text="DDS Settings")
        
        self.lbl_3 = ttk.Label(self.dds_grid, text="DDS Phase Frequency:")
        self.lbl_3.grid(row=0, column=0, **App.WIDGET_OPTS)

        self.ent_dds_counter_freq = ttk.Entry(self.dds_grid)
        self.ent_dds_counter_freq.grid(row=0, column=1, **App.WIDGET_OPTS)
        self.ent_dds_counter_freq.insert(0, App.DDS_DEFAULT_PHASE_FREQ)

        self.lbl_4 = ttk.Label(self.dds_grid, text="MHz")
        self.lbl_4.grid(row=0, column=2, **App.WIDGET_OPTS)

        self.lbl_5 = ttk.Label(self.dds_grid, text="Phase Accumulator Width:")
        self.lbl_5.grid(row=1, column=0, **App.WIDGET_OPTS)
        
        self.ent_dds_counter_bits = ttk.Entry(self.dds_grid)
        self.ent_dds_counter_bits.insert(0, "32")
        self.ent_dds_counter_bits.grid(row=1, column=1, **App.WIDGET_OPTS)
        
        self.lbl_6 = ttk.Label(self.dds_grid, text="bits")
        self.lbl_6.grid(row=1, column=2, **App.WIDGET_OPTS)

        self.lbl_9 = ttk.Label(self.dds_grid, text="Target Output Frequency:")
        self.lbl_9.grid(row=2, column=0, **App.WIDGET_OPTS)

        self.ent_dds_target_freq = ttk.Entry(self.dds_grid)
        self.ent_dds_target_freq.insert(0, App.DDS_DEFAULT_TARGET_FREQ)
        self.ent_dds_target_freq.grid(row=2, column=1, **App.WIDGET_OPTS)

        self.cbx_dds_freq_unit = ttk.Combobox(self.dds_grid)
        self.cbx_dds_freq_unit["values"] = list(App.FREQUENCY_UNIT_OPTIONS.keys())
        self.cbx_dds_freq_unit.current(App.FREQUENCY_UNIT_DEFAULT_INDEX)
        self.cbx_dds_freq_unit.grid(row=2, column=2, **App.WIDGET_OPTS)
        self.cbx_dds_freq_unit["state"] = "readonly"

        self.lbl_7 = ttk.Label(self.dds_grid, text="Phase Step:")
        self.lbl_7.grid(row=3, column=0, **App.WIDGET_OPTS)

        self.lbl_dds_counter_reload = ttk.Label(self.dds_grid)
        self.lbl_dds_counter_reload.grid(row=3, column=1, **App.WIDGET_OPTS)

        self.lbl_10 = ttk.Label(self.dds_grid, text="Actual Output Frequency (Hz):")
        self.lbl_10.grid(row=3, column=2, **App.WIDGET_OPTS)

        self.lbl_dds_actual_freq = ttk.Label(self.dds_grid)
        self.lbl_dds_actual_freq.grid(row=3, column=3, **App.WIDGET_OPTS)

        self.btn_dds_commit = ttk.Button(self.dds_grid)
        self.btn_dds_commit["text"] = "Commit"
        self.btn_dds_commit["command"] = self.handle_dds_commit
        self.btn_dds_commit.bind()
        self.btn_dds_commit.grid(row=4, column=3, **App.WIDGET_OPTS)
        ###

        # Set disconnected GUI state
        self.btn_refresh["state"] = "normal"
        self.cbx_serial_device["state"] = "normal"
        self.cbx_serial_baudrate["state"] = "normal"
        self.btn_connect["state"] = "normal"
        self.btn_disconnect["state"] = "disabled"

    def enumerate_serial_devices(self):
        return glob.glob("/dev/tty*")

    def handle_serial_devices_refresh(self):
        serial_devices = self.enumerate_serial_devices()
        self.cbx_serial_device["values"] = serial_devices
        if len(serial_devices) > 0:
            self.cbx_serial_device.current(0)

    def handle_connect(self):
        device = self.cbx_serial_device.get()
        try:
            baudrate = int(self.cbx_serial_baudrate.get())
        except ValueError:
            print("Baudrate not number")
            return

        if self.serial_ctrl.connect(device, baudrate):
            self.btn_refresh["state"] = "disabled"
            self.cbx_serial_device["state"] = "disabled"
            self.cbx_serial_baudrate["state"] = "disabled"
            self.btn_connect["state"] = "disabled"
            self.btn_disconnect["state"] = "normal"

    def handle_disconnect(self):
        if self.serial_ctrl.disconnect():
            self.btn_refresh["state"] = "normal"
            self.cbx_serial_device["state"] = "normal"
            self.cbx_serial_baudrate["state"] = "normal"
            self.btn_connect["state"] = "normal"
            self.btn_disconnect["state"] = "disabled"

    def commit_dds_setting(self, counter_freq, counter_width, target_freq):
        counter_reload = int(counter_freq / target_freq / 4)
        actual_freq = counter_freq / counter_reload / 4
        if self.serial_ctrl.is_connected():
            self.serial_ctrl.send_noblock((counter_reload - 1).to_bytes((counter_width // 8), byteorder="big"))
        return counter_reload, actual_freq

    def handle_dds_commit(self):
        try:
            counter_freq = int(self.ent_dds_counter_freq.get()) * 1000000
            counter_width = int(self.ent_dds_counter_bits.get())
            target_freq_base = float(self.ent_dds_target_freq.get())
            target_freq_multiplier = App.FREQUENCY_UNIT_OPTIONS[self.cbx_dds_freq_unit.get()]
            target_freq = target_freq_base * target_freq_multiplier
        except ValueError:
            print("DDS settings invalid")
            return
        
        counter_reload, actual_freq = self.commit_dds_setting(counter_freq, counter_width, target_freq)
        self.lbl_dds_counter_reload["text"] = counter_reload
        self.lbl_dds_actual_freq["text"] = "{0:.2f}".format(actual_freq)
        

window = ThemedTk(theme="clearlooks")
app = App(master=window)
app.mainloop()
