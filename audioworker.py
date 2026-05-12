from PySide6.QtCore import QThread
import pygame

class AudioWorker(QThread):

	def __init__(self):
		super().__init__()
		pygame.mixer.init()
		pygame.mixer.music.load("media/camera-shutter.oga")
		pass
		
	def run(self):
		pygame.mixer.music.play()
		pass