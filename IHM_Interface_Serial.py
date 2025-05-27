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
import time

class App:
    def __init__(self, root, maxPoint, simulation):

        #Définition des variable d'instance
        self.root = root
        self.maxPoint = maxPoint    #Nombre de point maximal affiché
        self.theta = []             #Coordonées theta des points
        self.r = []                 #Coordonées r des points
        self.rmax = 50               #Coordonée r maximum affichée
        self.simulation = simulation

        #A but de test uniquement ===# 
        self.current_angle = 0       #
        self.scan_direction = 1      #
        #============================#
        
        # CONFIGURATION DE LA FENETRE
        root.title("RadarTagnan")
        root.bind('<Key>', self.keyRouter) #Routage des évènements vers des fonctions
        root.configure(background='grey')
        root.geometry("600x500")
        root.resizable(width=False, height=False)
        ft = tkFont.Font(size=15)

        #Initialisation des widgets
            #Canva principal
        fig = self.initPlot()
        RadarCanvas = FigureCanvasTkAgg(fig,master = root)
        RadarCanvas.draw()
        RadarCanvas.get_tk_widget().grid(row=0, column=1, rowspan=3)

            #Bouton ZoomIn
        ZoomInButton = tk.Button(root, text="+", font = ft, command=self.zoomIn)
        ZoomInButton.grid(row=0,column=0,sticky="sew")

            #Bouton ZoomOut
        ZoomOutButton = tk.Button(root, text="-", font=ft, command=self.zoomOut)
        ZoomOutButton.grid(row=1,column=0, sticky="new")

        if simulation :
            simuLabel = tk.Label(root, text="Mode Simulation", fg='#ff0000',bg='#fff')
        else:
            simuLabel = tk.Label(root, text="Mode Réel", fg='#00ff00',bg='#fff')

        simuLabel.grid(row=2,column=0)

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
        if ser:
            ser.close()
        self.stopReception()
        self.root.destroy()
    
    def udpPlot(self):
        self.radarLine[0].set_data([self.theta[-1],self.theta[-1]], [0,self.rmax]) #Anime la ligne verte du radar. Purement cosmétique.
        self.scat.set_offsets(np.c_[self.theta, self.r]) #Met à jour la position des points
        self.scat.set_array(np.array(self.r))  # Met à jour la couleur si liée à r
        self.scat.figure.canvas.draw_idle() #On redessine le graphique
        
    def keyRouter(self,event):
        #Routage des touche tappées par l'utilisateur vers les fonctions associées
        if event.char == 'p': self.zoomIn()
        if event.char == 'o': self.zoomOut()

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

    def zoomIn(self): #Déclanchée par p, ou bouton "+"
        self.rmax = self.rmax * 0.5
        self.polarPlot.set_rlim(0,self.rmax)
        self.udpPlot()

    def zoomOut(self): #Déclanchée par o, ou bouton "-"
        self.rmax = self.rmax * 1.5
        self.polarPlot.set_rlim(0,self.rmax)
        self.udpPlot()

    def startReception(self, simulation = False, interval_ms=50):
        self.scan_direction = 1
        self.current_angle = 0
        self.run = True
        print(simulation)
        if simulation: self.simulatedTick(interval_ms)
        else : self.Tick(interval_ms)

    def stopReception(self):
        self.run = False

    def Tick(self, interval_ms):
        if not self.run:
            return

        if ser and ser.in_waiting > 0:
            try:
                ligne = ser.readline().decode('utf-8', errors='ignore').strip()
                #print(ligne)
                angle = int(ligne.split(",")[0].strip())
                distance = float(ligne.split(",")[1].strip())
                print(angle,distance)
                self.addOnePoint(deg2rad(angle),distance)
            except(ValueError):
                pass
        
        self.root.after(interval_ms, lambda: self.Tick(interval_ms)) #Callback

    def simulatedTick(self, interval_ms): #Fonction test uniquement
        if not self.run:
            return

        angle = self.current_angle
        distance = randint(0, 100) / 100

        self.addOnePoint(angle, distance)
        self.current_angle += deg2rad(self.scan_direction)

        if self.current_angle >= deg2rad(180):
            self.current_angle = deg2rad(180)
            self.scan_direction = -1
        elif self.current_angle <= 0:
            self.current_angle = 0
            self.scan_direction = 1

        # Replanifie l'appel
        self.root.after(interval_ms, lambda: self.simulatedTick(interval_ms)) #Callback
            
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

if __name__ == "__main__":

    AppVersion = "1.2"
    AppDev = "Mesner/Poulette"
    maxPoint = 50
    portSerie = "COM14"

    print(f"RadarTagnan - ver{AppVersion}")
    print(f"Author(s) : {AppDev}")
    print("== Default Parameters ==")
    print(f"maxPoint = {maxPoint}")
    print("\n")
    print(f"[~] Tentative de connexion au port série {portSerie}")
    try:
        ser = serial.Serial(portSerie, 115200, timeout=1)
        simulation = False
        print(f"[+] Connexion au port série {portSerie} réussie.")

    except:
        print(f"[-] Impossible de se connecter au port série {portSerie}. Vérifiez la connexion.")
        print(f"[+] Passage en données simulées")
        simulation = True
        ser = None

    print("[~] Création de la fenetre")
    root = tk.Tk()
    app = App(root, maxPoint, simulation)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    print("[+] Fenêtre créee")

    print(f"[~] Initialisation de la boucle données")
    app.startReception(simulation=simulation)
    print("[+] Boucle données initialisée")
    print("[+] Lancement de la boucle applicative principale")
    root.mainloop()
    print("[-] Fermeture de l'application")
