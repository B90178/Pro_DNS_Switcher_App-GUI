import tkinter as tk
from tkinter import messagebox
import platform
import subprocess
import re
import threading
import socket
import time

# ---------- DNS Presets ----------
DNS_OPTIONS = {
    "Google DNS": ("8.8.8.8", "8.8.4.4"),
    "Cloudflare DNS": ("1.1.1.1", "1.0.0.1"),
    "OpenDNS": ("208.67.222.222", "208.67.220.220")
}

current_os = platform.system()

# ---------- OS-Specific Utilities ----------

def get_adapters():
    adapters = []
    try:
        if current_os == "Windows":
            result = subprocess.run(["netsh", "interface", "show", "interface"], capture_output=True, text=True)
            for line in result.stdout.splitlines()[3:]:
                parts = line.split()
                if len(parts) >= 4:
                    adapters.append(parts[3])
        elif current_os == "Linux":
            result = subprocess.run(["nmcli", "device", "status"], capture_output=True, text=True)
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 1:
                    adapters.append(parts[0])
        elif current_os == "Darwin":
            result = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
            for line in result.stdout.splitlines()[1:]:
                if line.strip() != "":
                    adapters.append(line.strip())
    except Exception as e:
        messagebox.showerror("Error", str(e))
    return adapters

def get_current_dns(adapter):
    try:
        if current_os == "Windows":
            result = subprocess.run(["netsh", "interface", "ip", "show", "dns"], capture_output=True, text=True)
            dns_lines = re.findall(r"Statically Configured DNS Servers:\s*(.*)", result.stdout)
            return dns_lines[0] if dns_lines else "Automatic/DHCP"
        elif current_os == "Linux":
            result = subprocess.run(["nmcli", "device", "show", adapter], capture_output=True, text=True)
            dns_lines = re.findall(r"IP4.DNS\[.*\]:\s*(.*)", result.stdout)
            return ", ".join(dns_lines) if dns_lines else "Automatic/DHCP"
        elif current_os == "Darwin":
            result = subprocess.run(["networksetup", "-getdnsservers", adapter], capture_output=True, text=True)
            if "There aren't any DNS Servers set" in result.stdout:
                return "Automatic/DHCP"
            return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def set_dns(adapter, primary, secondary):
    try:
        if current_os == "Windows":
            subprocess.run(["netsh", "interface", "ip", "set", "dns", adapter, "static", primary], check=True)
            subprocess.run(["netsh", "interface", "ip", "add", "dns", adapter, secondary, "index=2"], check=True)
        elif current_os == "Linux":
            subprocess.run(["nmcli", "con", "mod", adapter, "ipv4.dns", f"{primary},{secondary}"], check=True)
            subprocess.run(["nmcli", "con", "up", adapter], check=True)
        elif current_os == "Darwin":
            subprocess.run(["networksetup", "-setdnsservers", adapter, primary, secondary], check=True)
        messagebox.showinfo("Success", f"DNS changed to {primary}, {secondary} for {adapter}")
        update_current_dns()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", str(e))

def reset_dns(adapter):
    try:
        if current_os == "Windows":
            subprocess.run(["netsh", "interface", "ip", "set", "dns", adapter, "dhcp"], check=True)
        elif current_os == "Linux":
            subprocess.run(["nmcli", "con", "mod", adapter, "ipv4.ignore-auto-dns", "no"], check=True)
            subprocess.run(["nmcli", "con", "up", adapter], check=True)
        elif current_os == "Darwin":
            subprocess.run(["networksetup", "-setdnsservers", adapter, "Empty"], check=True)
        messagebox.showinfo("Success", f"DNS reset to automatic for {adapter}")
        update_current_dns()
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", str(e))

# ---------- DNS Monitoring / Ping ----------

def ping_dns(dns, var):
    try:
        socket.setdefaulttimeout(2)
        host = socket.gethostbyname(dns)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host, 53))
        sock.close()
        var.set(f"{dns} ✅ reachable")
    except:
        var.set(f"{dns} ❌ unreachable")

def start_ping_test(primary, secondary):
    primary_var.set("Testing...")
    secondary_var.set("Testing...")
    threading.Thread(target=ping_dns, args=(primary, primary_var), daemon=True).start()
    threading.Thread(target=ping_dns, args=(secondary, secondary_var), daemon=True).start()

# ---------- GUI Functions ----------

def switch_dns():
    adapter = adapter_var.get()
    dns_choice = dns_var.get()
    if adapter == "" or dns_choice == "":
        messagebox.showwarning("Input Error", "Please select an adapter and a DNS option.")
        return

    if dns_choice == "Custom":
        primary = custom_primary.get()
        secondary = custom_secondary.get()
        if primary == "" or secondary == "":
            messagebox.showwarning("Input Error", "Please enter both primary and secondary DNS for custom.")
            return
    elif dns_choice == "Automatic":
        reset_dns(adapter)
        primary_var.set("-")
        secondary_var.set("-")
        return
    else:
        primary, secondary = DNS_OPTIONS[dns_choice]

    set_dns(adapter, primary, secondary)
    start_ping_test(primary, secondary)

def update_current_dns(*args):
    adapter = adapter_var.get()
    if adapter != "":
        dns_label_var.set(f"Current DNS: {get_current_dns(adapter)}")
    else:
        dns_label_var.set("Current DNS: -")

def copy_dns():
    root.clipboard_clear()
    root.clipboard_append(dns_label_var.get().replace("Current DNS: ", ""))
    messagebox.showinfo("Copied", "DNS copied to clipboard!")

def auto_refresh():
    while True:
        adapter = adapter_var.get()
        if adapter:
            dns_label_var.set(f"Current DNS: {get_current_dns(adapter)}")
        time.sleep(10)

# ---------- GUI ----------

root = tk.Tk()
root.title("Ultimate Pro DNS Switcher")
root.geometry("550x520")
root.configure(bg="#1E1E1E")

font_label = ("Segoe UI", 11)
font_entry = ("Segoe UI", 10)

# Adapter selection
tk.Label(root, text="Select Network Adapter:", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack(pady=5)
adapter_var = tk.StringVar()
adapters = get_adapters()
adapter_menu = tk.OptionMenu(root, adapter_var, *adapters, command=update_current_dns)
adapter_menu.config(bg="#3C3F41", fg="#FFFFFF", width=35)
adapter_menu.pack()

# Current DNS
dns_label_var = tk.StringVar()
dns_label_var.set("Current DNS: -")
tk.Label(root, textvariable=dns_label_var, bg="#1E1E1E", fg="#00FF00", font=font_label).pack(pady=5)

# Copy button
tk.Button(root, text="Copy Current DNS", command=copy_dns, bg="#4CAF50", fg="white", font=font_entry).pack(pady=5)

# DNS selection
tk.Label(root, text="Select DNS:", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack(pady=5)
dns_var = tk.StringVar()
dns_menu = tk.OptionMenu(root, dns_var, *list(DNS_OPTIONS.keys()) + ["Custom", "Automatic"])
dns_menu.config(bg="#3C3F41", fg="#FFFFFF", width=35)
dns_menu.pack()

# Custom DNS
tk.Label(root, text="Custom DNS (if selected):", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack(pady=5)
tk.Label(root, text="Primary:", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack()
custom_primary = tk.Entry(root, font=font_entry, bg="#3C3F41", fg="#FFFFFF")
custom_primary.pack()
tk.Label(root, text="Secondary:", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack()
custom_secondary = tk.Entry(root, font=font_entry, bg="#3C3F41", fg="#FFFFFF")
custom_secondary.pack()

# Switch button
tk.Button(root, text="Switch DNS", command=switch_dns, bg="#4CAF50", fg="white", font=("Segoe UI", 12)).pack(pady=15)

# Ping test results
tk.Label(root, text="DNS Reachability Test:", bg="#1E1E1E", fg="#FFFFFF", font=font_label).pack(pady=5)
primary_var = tk.StringVar()
secondary_var = tk.StringVar()
primary_var.set("-")
secondary_var.set("-")
tk.Label(root, textvariable=primary_var, bg="#1E1E1E", fg="#00FFFF", font=font_label).pack()
tk.Label(root, textvariable=secondary_var, bg="#1E1E1E", fg="#00FFFF", font=font_label).pack()

# Start auto-refresh in background
threading.Thread(target=auto_refresh, daemon=True).start()

root.mainloop()
