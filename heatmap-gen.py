import customtkinter as ctk
import threading
import time
import csv
import os
from pynput import mouse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


class AuditLogger:
    def __init__(self, filepath="ux_log.csv", buffer_size=500):
        self.filepath = filepath
        self.buffer_size = buffer_size
        self.buffer = []
        self.running = False
        self._initialize_file()

    def _initialize_file(self):
        with open(self.filepath, 'w', newline='') as f:
            csv.writer(f).writerow(['timestamp', 'event_type', 'x', 'y', 'meta_data'])

    def _flush_buffer(self):
        if not self.buffer: return
        try:
            with open(self.filepath, 'a', newline='') as f:
                csv.writer(f).writerows(self.buffer)
            self.buffer.clear()
        except IOError as e:
            print(f"Erro de I/O: {e}")

    def _log(self, event_type, x, y, meta_data=None):
        if not self.running: return
        self.buffer.append([time.time(), event_type, x, y, meta_data])
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()

    def start(self):
        self.running = True
        self._initialize_file() 
        with mouse.Listener(
            on_move=lambda x,y: self._log('move', x, y),
            on_click=lambda x,y,b,p: self._log('click', x, y, f"{b}.{'pressed' if p else 'released'}"),
            on_scroll=lambda x,y,dx,dy: self._log('scroll', x, y, f"dx:{dx}|dy:{dy}")
        ) as listener:
            self.listener = listener
            listener.join()
    
    def stop(self):
        self.running = False
        if hasattr(self, 'listener'): 
            self.listener.stop()
        self._flush_buffer()


class DataVisualizer:
    @staticmethod
    def generate_reports(input_file="ux_log.csv"):
        if not os.path.exists(input_file):
            return "Erro-- qrquivo de log não encontrado."

        try:
            df = pd.read_csv(input_file, skipinitialspace=True)
        except pd.errors.EmptyDataError:
            return "Erro-- log vazio."

        df['x'] = pd.to_numeric(df['x'], errors='coerce')
        df['y'] = pd.to_numeric(df['y'], errors='coerce')
        df = df.dropna(subset=['x', 'y'])

        SCREEN_W = 1920
        SCREEN_H = 1080
        
        STYLE_TEXT = 'white'
        STYLE_CMAP = 'inferno' 

        hover_data = df[df['event_type'] == 'move']
        
        if not hover_data.empty:
            plt.figure(figsize=(16, 9), dpi=120)
            
            ax = plt.gca()
            ax.set_facecolor('none') 
            
            sns.kdeplot(
                x=hover_data['x'], 
                y=hover_data['y'], 
                cmap=STYLE_CMAP, 
                fill=True, 
                thresh=0.05,   
                levels=30,     
                bw_adjust=0.5, 
                alpha=0.9      
            )
            
            plt.xlim(0, SCREEN_W)
            plt.ylim(SCREEN_H, 0)
            plt.axis('off')
            
            plt.title("Hover Density Map", color=STYLE_TEXT, fontsize=14, pad=10)
            plt.tight_layout()
            
            plt.savefig("output_hover_map.png", transparent=True, bbox_inches='tight', pad_inches=0)
            plt.close()
            
            return "sucesso!"
        else:
            return "sem dados para plotar o mapa"

class heatmapgenerator:
    def __init__(self, root):
        self.root = root
        self.root.title(" ")
        self.root.geometry("400x220")
        self.root.resizable(False, False)
        
        self.logger = AuditLogger()
        self.is_recording = False
        
        self.COLORS = {
            "bg": "#1a1c19", "success": "#3d54ac", "success_hover": "#2c3d7c",
            "danger": "#E33B3E", "danger_hover": "#C0392B", "text": "#ffffff", "dim": "#888888"
        }

        self.main_frame = ctk.CTkFrame(root, corner_radius=0, fg_color=self.COLORS["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.lbl_title = ctk.CTkLabel(self.main_frame, text="seeker", font=("Manrope", 22, "bold"), text_color="white")
        self.lbl_title.pack(pady=(0, 3))

        self.progress = ctk.CTkProgressBar(self.main_frame, width=350, height=8, corner_radius=4, progress_color="#3b86e3")
        self.progress.set(0)

        self.status_var = ctk.StringVar(value=" ")
        self.lbl_status = ctk.CTkLabel(self.main_frame, textvariable=self.status_var, font=("Manrope", 12), text_color=self.COLORS["success"])
        self.lbl_status.pack(pady=0.1)

        self.btn_record = ctk.CTkButton(self.main_frame, text="iniciar", command=self.handle_record, font=("Manrope", 13, "bold"), corner_radius=8, height=45, width=280, fg_color=self.COLORS["success"], hover_color=self.COLORS["success_hover"])
        self.btn_record.pack(pady=(5, 5))

        self.btn_report = ctk.CTkButton(self.main_frame, text="plotar heatmap", command=self.handle_reports, font=("Manrope", 12, "bold"), corner_radius=8, height=35, width=280, fg_color="transparent", border_width=1, border_color=self.COLORS["dim"], text_color=self.COLORS["dim"], state="disabled")
        self.btn_report.pack(pady=5)

    def handle_record(self):
        if self.is_recording:
            self.logger.stop()
            self.is_recording = False
            self.status_var.set("sessão finalizada.")
            self.lbl_status.configure(text_color=self.COLORS["success"])
            self.btn_record.configure(text="gravar nova sessão", fg_color=self.COLORS["success"], hover_color=self.COLORS["success_hover"])
            self.btn_report.configure(state="normal", border_color="white", text_color="white")
        else:
            self.btn_record.configure(state="disabled")
            self.btn_report.configure(state="disabled")
            self.progress.pack(pady=5)
            threading.Thread(target=self._countdown_logic, daemon=True).start()

    def _countdown_logic(self):
        for i in range(5, 0, -1):
            self.progress.set((5-i)/5)
            self.status_var.set(f"iniciando em {i}s...")
            time.sleep(1)
        self.root.after(0, self.start_recording_actual)

    def start_recording_actual(self):
        self.is_recording = True
        self.progress.pack_forget()
        self.status_var.set("● logando eventos")
        self.lbl_status.configure(text_color=self.COLORS["danger"])
        self.btn_record.configure(text="parar e salvar", state="normal", fg_color=self.COLORS["danger"], hover_color=self.COLORS["danger_hover"])
        self.log_thread = threading.Thread(target=self.logger.start, daemon=True)
        self.log_thread.start()

    def handle_reports(self):
        self.status_var.set("gerando heatmaps")
        self.btn_report.configure(state="disabled")
        threading.Thread(target=self._process_reports_thread, daemon=True).start()

    def _process_reports_thread(self):
        result_msg = DataVisualizer.generate_reports()
        self.root.after(0, lambda: self._finish_reports(result_msg))

    def _finish_reports(self, msg):
        self.status_var.set(msg)
        self.btn_report.configure(state="normal")
        try: os.startfile(os.getcwd()) 
        except: pass

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app_window = ctk.CTk(fg_color="#1a1c19")
    app = heatmapgenerator(app_window)
    app_window.mainloop()