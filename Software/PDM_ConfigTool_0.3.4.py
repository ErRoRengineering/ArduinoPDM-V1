# PDM Config Tool (GUI version) 
# Författare: Jan Lindvall / ErRoR Engineering
# Version: 0.3.4

import tkinter as tk
from tkinter import ttk, messagebox
import can
import time
import threading

CONFIG_ID = 0x660
REPLY_ID = 0x661
FW_REPLY_ID = 0x661  # Samma som övriga svar än så länge
DEFAULT_STATUS_ID = 0x650

bus = None

class PDMTool:
    def __init__(self, root):
        self.root = root
        root.title("PDM Config Tool v0.3.4")
        root.geometry("400x540")

        # Försök initiera CAN
        global bus
        try:
            bus = can.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=1000000)
        except can.CanError as e:
            messagebox.showerror("CAN-fel", f"Kunde inte öppna CAN-kanalen:\n{e}\n\nÄr ett annat program igång?")
            root.destroy()
            return

        self.toggle_vars = [tk.IntVar() for _ in range(8)]
        self.status_vars = [tk.StringVar(value="?") for _ in range(8)]
        self.status_labels = []
        self.canid_var = tk.StringVar()
        self.statusrate_var = tk.StringVar()
        self.statuscanid_var = tk.StringVar(value=f"{DEFAULT_STATUS_ID:03X}")
        self.status_text = tk.StringVar()
        self.fw_version = tk.StringVar(value="-")

        self.received_fw = False
        self.received_config = False

        self.running = True
        self.status_thread = threading.Thread(target=self.poll_status_loop, daemon=True)
        self.status_thread.start()

        frame = ttk.Frame(root)
        frame.pack(pady=5)
        ttk.Label(frame, text="Toggle för reläer").grid(row=0, column=0, columnspan=4)
        for i in range(8):
            ttk.Checkbutton(frame, text=f"R{i+1}", variable=self.toggle_vars[i]).grid(row=1+i//4, column=i%4, padx=5, pady=2)

        ttk.Label(root, text="Lyssnings-CAN ID (hex)").pack(pady=5)
        ttk.Entry(root, textvariable=self.canid_var).pack()

        ttk.Label(root, text="Statusintervall (ms)").pack(pady=5)
        ttk.Entry(root, textvariable=self.statusrate_var).pack()

        ttk.Label(root, text="Status-CAN ID (hex)").pack(pady=5)
        ttk.Entry(root, textvariable=self.statuscanid_var).pack()

        ttk.Button(root, text="Läs från enhet", command=self.get_config).pack(pady=10)
        ttk.Button(root, text="Skicka tillfällig konfig", command=self.send_config).pack()
        ttk.Button(root, text="Spara till EEPROM", command=self.save_config).pack(pady=5)

        status_frame = ttk.LabelFrame(root, text="Relästatus")
        status_frame.pack(pady=5, fill="x", padx=10)
        for i in range(8):
            ttk.Label(status_frame, text=f"R{i+1}:").grid(row=i//4, column=(i%4)*2, sticky="e")
            label = ttk.Label(status_frame, textvariable=self.status_vars[i], foreground="gray")
            label.grid(row=i//4, column=(i%4)*2+1, sticky="w")
            self.status_labels.append(label)

        ttk.Label(root, textvariable=self.status_text, foreground="blue").pack(pady=5)
        ttk.Label(root, text="Firmwareversion:").pack()
        ttk.Label(root, textvariable=self.fw_version, foreground="darkblue").pack()

        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initiera direkt vid start
        self.initialize_device()

    def on_close(self):
        self.running = False
        if bus:
            bus.shutdown()
        self.root.destroy()

    def send_command(self, cmd_id, data=[]):
        msg_data = [cmd_id] + data + [0]*(8-len(data)-1)
        timeout = time.time() + 2.0
        last_send = 0
        send_interval = 0.2

        while time.time() < timeout:
            now = time.time()
            if now - last_send > send_interval:
                msg = can.Message(arbitration_id=CONFIG_ID, data=msg_data, is_extended_id=False)
                try:
                    bus.send(msg)
                except can.CanError:
                    pass
                last_send = now

            reply = bus.recv(timeout=0.1)
            if reply and reply.arbitration_id == REPLY_ID:
                return reply.data
        return None

    def initialize_device(self):
        threading.Thread(target=self.delayed_init, daemon=True).start()

    def delayed_init(self):
        config_reply = self.send_command(0x03)
        if config_reply and config_reply[0] == 0x00:
            self.received_config = True
            toggle_mask = config_reply[2]
            for i in range(8):
                self.toggle_vars[i].set((toggle_mask >> i) & 0x01)
            canid = config_reply[3] | (config_reply[4] << 8)
            self.canid_var.set(f"{canid:03X}")
            rate = config_reply[5] | (config_reply[6] << 8)
            self.statusrate_var.set(str(rate))
            self.status_text.set("Konfiguration hämtad")

        fw_reply = self.send_command(0x06)
        if fw_reply and fw_reply[0] == 0x00 and fw_reply[1] == 0x06:
            self.received_fw = True
            version = bytes(fw_reply[2:8]).decode(errors='ignore').strip('\x00')
            self.fw_version.set(version)
            self.status_text.set("Firmwareversion hämtad")

        if not self.received_config or not self.received_fw:
            self.root.after(0, lambda: messagebox.showerror("Ingen kontakt", "Ingen kontakt med enheten."))

    def get_config(self):
        reply = self.send_command(0x03)
        if reply and reply[0] == 0x00:
            toggle_mask = reply[2]
            for i in range(8):
                self.toggle_vars[i].set((toggle_mask >> i) & 0x01)
            canid = reply[3] | (reply[4] << 8)
            self.canid_var.set(f"{canid:03X}")
            rate = reply[5] | (reply[6] << 8)
            self.statusrate_var.set(str(rate))
            self.status_text.set("Konfiguration hämtad")

        fw_reply = self.send_command(0x06)
        if fw_reply and fw_reply[0] == 0x00 and fw_reply[1] == 0x06:
            version = bytes(fw_reply[2:8]).decode(errors='ignore').strip('\x00')
            self.fw_version.set(version)
            self.status_text.set("Firmwareversion hämtad")

    def send_config(self):
        try:
            toggle = sum((var.get() << i) for i, var in enumerate(self.toggle_vars))
            canid = int(self.canid_var.get(), 16)
            rate = int(self.statusrate_var.get())
        except ValueError:
            messagebox.showerror("Fel", "Ogiltigt inmatningsformat")
            return

        self.send_command(0x01, [toggle])
        self.send_command(0x04, [canid & 0xFF, (canid >> 8) & 0xFF])
        self.send_command(0x05, [rate & 0xFF, (rate >> 8) & 0xFF])
        self.status_text.set("Konfiguration skickad (ej sparad)")

    def save_config(self):
        self.send_command(0x02)
        self.status_text.set("Konfiguration sparad i EEPROM")

    def poll_status_loop(self):
        while self.running:
            try:
                status_id = int(self.statuscanid_var.get(), 16)
            except ValueError:
                status_id = DEFAULT_STATUS_ID

            msg = bus.recv(timeout=0.5)
            if msg and msg.arbitration_id == status_id and len(msg.data) >= 1:
                status_mask = msg.data[0]
                for i in range(8):
                    if (status_mask >> i) & 1:
                        self.status_vars[i].set("ON")
                        self.status_labels[i].config(foreground="green")
                    else:
                        self.status_vars[i].set("OFF")
                        self.status_labels[i].config(foreground="red")
                self.status_text.set("Relästatus uppdaterad")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDMTool(root)
    root.mainloop()
