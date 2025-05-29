import tkinter as tk
import tkinter.font as tkFont
from tkinter.filedialog import asksaveasfile

from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)

import numpy as np
from numpy import deg2rad

from random import randint
from random import uniform

import json
import serial
import serial.tools.list_ports

import time
import tk_tools

class App:
    def __init__(self, root, maxPoint):

        #Définition des variable d'instance
        self.root = root
        self.maxPoint = maxPoint    #Nombre de point maximal affiché
        self.theta = []             #Coordonées theta des points
        self.r = []                 #Coordonées r des points
        self.rmax = 50               #Coordonée r maximum affichée
        self.simulation = True
        self.radarSpeed = 10
        self.ser = None

        #A but de test uniquement ===# 
        self.current_angle = 0       #
        self.scan_direction = 1      #
        #============================#
        
        # CONFIGURATION DE LA FENETRE
        root.title("RadarTagnan")
        root.bind('<Key>', self.keyRouter) #Routage des évènements vers des fonctions
        root.configure(background='grey')
        root.geometry("700x550")
        root.resizable(width=False, height=False)
        ft = tkFont.Font(size=15)

        #Initialisation des widgets

                # Initialisation des widgets
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=3)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)
        root.rowconfigure(3, weight=1)

        # Canva principal
        fig = self.initPlot()
        RadarCanvas = FigureCanvasTkAgg(fig, master=root)
        RadarCanvas.draw()
        RadarCanvas.get_tk_widget().grid(row=0, column=1, rowspan=4, sticky="nsew", padx=10, pady=10)

        # --- portée ---
        zoom_frame = tk.LabelFrame(root, text="Portée", font=ft, bg="lightgrey")
        zoom_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        zoom_frame.columnconfigure((0, 1), weight=1)

        self.zoomVar = tk.StringVar()
        self.zoomVar.set(str(self.rmax)+" cm")
        zoomLabel = tk.Label(zoom_frame, textvariable=self.zoomVar, fg='red', bg='white', font=ft)
        zoomLabel.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        zoomOutButton = tk.Button(zoom_frame, text="-", font=ft, command=self.zoomOut)
        zoomOutButton.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        zoomInButton = tk.Button(zoom_frame, text="+", font=ft, command=self.zoomIn)
        zoomInButton.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # --- Mode Simulation ---
        mode_frame = tk.LabelFrame(root, text="Mode", font=ft, bg="lightgrey")
        mode_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        mode_frame.columnconfigure(0, weight=1)

        mode_label = tk.Label(mode_frame,
                              text="Simulation",fg='red',bg='white',font=ft)
        mode_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- Vitesse Radar ---
        speed_frame = tk.LabelFrame(root, text="Vitesse Radar", font=ft, bg="lightgrey")
        speed_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        speed_frame.columnconfigure((0, 1), weight=1)

        self.speed_gauge = tk_tools.Gauge(speed_frame, width=200, height=100,
                                          min_value=0.0, max_value=180.0,
                                          label='', unit='°/s', divisions=8,
                                          yellow=50, red=80,
                                          yellow_low=0, red_low=0,
                                          bg='lightgrey')
        self.speed_gauge.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.speed_gauge.set_value(self.radarSpeed)

        slowDownButton = tk.Button(speed_frame, text="<<<<<", font=ft, command=self.slowDown)
        slowDownButton.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        speedUpButton = tk.Button(speed_frame, text=">>>>>", font=ft, command=self.speedUp)
        speedUpButton.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # --- Menu sélection du port COM ---
        self.port_frame = tk.LabelFrame(root, text="Connexion", font=ft, bg="lightgrey")
        self.port_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        self.port_frame.columnconfigure(0, weight=1)
        self.port_frame.columnconfigure(1, weight=1)

        self.available_ports = self.get_available_ports()
        self.selected_port = tk.StringVar()
        self.selected_port.set(self.available_ports[0])

        self.port_menu = tk.OptionMenu(self.port_frame, self.selected_port, *self.available_ports)
        self.port_menu.config(font=ft)
        self.port_menu.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.connect_button = tk.Button(self.port_frame, text="Connecter", font=ft, command=self.try_connection)
        self.connect_button.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    def initPlot(self): #Fonction d'initialisation du graphique matplotlib
        plt.style.use('dark_background')
        fig = Figure(figsize = (5, 5),dpi = 100)
        self.polarPlot = fig.add_subplot(111, polar=True) #Création du graphique polaire
        self.polarPlot.set_thetamin(0)
        self.polarPlot.set_thetamax(180) #Attention, on définit l'échelle en degré, mais on doit utiliser des radians dans le code ! 
        self.polarPlot.set_rlim(0,self.rmax)
        
        self.scat = self.polarPlot.scatter(self.theta, self.r, c=self.r, s=5, cmap='Wistia', alpha=0.75)
        self.radarLine = self.polarPlot.plot([0.2,0.2],[0,100], color="green")
        return fig
    
    def on_closing(self):
        global running
        running = False
        if self.ser:
            self.ser.close()
        self.stopReception()
        self.root.destroy()

    def get_available_ports(self,testTimeout=0.25, baudrate=115200):
        working_ports = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            try:
                with serial.Serial(port.device, baudrate=baudrate, timeout=testTimeout) as test_ser:
                    test_ser.reset_input_buffer()
                    data = test_ser.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        print(f"[+] Données détectées sur {port.device} : {data}")
                        working_ports.append(port.device)
            except Exception as e:
                print(f"[-] Erreur sur {port.device} : {e}")
        
        if not working_ports:
            print("[-] Aucun port série actif détecté.")
            return ["None"]

        return working_ports

    def try_connection(self):
        port = self.selected_port.get()
        print(f"[~] Tentative de connexion au port {port}")
        try:
            self.ser = serial.Serial(port, 115200, timeout=1)
            self.simulation = False
            print(f"[+] Connexion à {port} réussie.")
            self.startReception(simulation=False)
        except Exception as e:
            print(f"[-] Échec de connexion : {e}")
            self.simulation = True
            self.ser = None
            print("[+] Passage en mode simulation")
            self.startReception(simulation=True)


    def udpPlot(self):
        self.radarLine[0].set_data([self.theta[-1],self.theta[-1]], [0,self.rmax]) #Anime la ligne verte du radar. Purement cosmétique.
        self.scat.set_offsets(np.c_[self.theta, self.r]) #Met à jour la position des points
        self.scat.set_array(np.array(self.r))  # Met à jour la couleur si liée à r
        self.scat.figure.canvas.draw_idle() #On redessine le graphique
        
    def keyRouter(self,event):
        #Routage des touche tappées par l'utilisateur vers les fonctions associées
        if event.char == 'p': self.zoomIn()
        if event.char == 'o': self.zoomOut()
        if event.char == 'l': self.slowDown()
        if event.char == 'm': self.speedUp()
        

    def addOnePoint(self,t,r):
        #Gestion de l'ajout d'un seul point
        #Si il y a trop de points (> maxPoint), on supprime le premier
        #Puis, on appelle updPlot pour mettre à jour le graphique
        self.theta.append(t)
        self.r.append(r)
        if len(self.theta) > self.maxPoint:
            self.theta.pop(0)
            self.r.pop(0)
        self.udpPlot()

    def startReception(self, simulation = False, interval_ms=50):
        self.scan_direction = 1
        self.current_angle = 0
        self.run = True
        if self.simulation: self.simulatedTick()
        else : self.Tick()

    def stopReception(self):
        self.run = False

    def Tick(self, ):
        if not self.run:
            self.root.after(100, lambda: self.simulatedTick())
        else:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    ligne = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    #print(ligne)
                    angle = int(ligne.split(",")[0].strip())
                    distance = float(ligne.split(",")[1].strip())
                    print(angle,distance)
                    self.addOnePoint(deg2rad(angle),distance)
                except(ValueError):
                    pass
            
            self.root.after(speedToInterval(self.radarSpeed), lambda: self.Tick())

    def simulatedTick(self): #Fonction test uniquement
        if not self.run:
            self.root.after(100, lambda: self.simulatedTick())
        else:
            angle = self.current_angle
            distance = (randint(0, 100) / 100)*self.rmax

            self.addOnePoint(angle, distance)
            self.current_angle += deg2rad(self.scan_direction)

            if self.current_angle >= deg2rad(180):
                self.current_angle = deg2rad(180)
                self.scan_direction = -1
            elif self.current_angle <= 0:
                self.current_angle = 0
                self.scan_direction = 1

            # Replanifie l'appel
            self.root.after(speedToInterval(self.radarSpeed), lambda: self.simulatedTick())

    def zoomIn(self): #Déclanchée par p, ou bouton "+"
        self.rmax = self.rmax * 1.5
        self.polarPlot.set_rlim(0,self.rmax)
        self.zoomVar.set(str(round(self.rmax,1))+" cm")
        self.udpPlot()

    def zoomOut(self): #Déclanchée par o, ou bouton "-"
        self.rmax = self.rmax * 0.5
        self.polarPlot.set_rlim(0,self.rmax)
        self.zoomVar.set(str(round(self.rmax,1))+" cm")
        self.udpPlot()

    def speedUp(self):
        self.radarSpeed += 1
        self.speed_gauge.set_value(self.radarSpeed)
        if self.radarSpeed > 0: self.run = True
        if not self.simulation: self.ser.write(str(self.radarSpeed).encode())

    def slowDown(self):
        self.radarSpeed -= 1
        if self.radarSpeed <= 0:
            self.radarSpeed = 0
            self.run = False
        self.speed_gauge.set_value(self.radarSpeed)
        if not self.simulation: self.ser.write(str(self.radarSpeed).encode())
        
            
def linspace(start, stop, num=50, endpoint=True):
    #Simule la fonciton linspace de numpy
    #Uniquement utilisée par les fonctions test
    if num <= 0:
        return []
    if num == 1:
        return [float(start)]
    start = float(start)
    stop = float(stop)
    step = (stop - start) / (num - 1) if endpoint else (stop - start) / num
    result = [start + i * step for i in range(num)]
    if endpoint:
        result[-1] = stop
    return result

def speedToInterval(speed):
    if speed == 0: pass
    return int((1/speed) * 1000)

if __name__ == "__main__":

    AppVersion = "2.0"
    AppDev = "Mesner/Poulette"
    maxPoint = 50

    print(f"RadarTagnan - ver{AppVersion}")
    print(f"Author(s) : {AppDev}")
    print("== Default Parameters ==")
    print(f"maxPoint = {maxPoint}")
    print("\n")

    print("[~] Création de la fenetre")
    root = tk.Tk()
    app = App(root, maxPoint)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    print("[+] Fenêtre créee")

    print(f"[~] Initialisation de la boucle données")
    app.startReception()
    print("[+] Boucle données initialisée")
    print("[+] Lancement de la boucle applicative principale")
    root.mainloop()
    print("[-] Fermeture de l'application")
