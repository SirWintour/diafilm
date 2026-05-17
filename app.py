import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtGui import QPalette, QColor, QPixmap, QImage, QShortcut
from PySide6.QtCore import QThreadPool, QSize, Signal, Qt
import cv2
from videoworker import VideoWorker
from audioworker import AudioWorker
from settings import SettingsControls
from filesaver import Filesaver
from config import video_device, output_dir, inverted, zoom_level
from pathlib import Path

class MainWindow(QMainWindow):

	def __init__(self):
		super().__init__()

		self.setWindowTitle("diafilm")
		self.resize(900, 700)
		
		self.filesaver = Filesaver()

		main_layout = QVBoxLayout()

		preview = QHBoxLayout()

		# Left: last shot
		last_shot_layout = QVBoxLayout()
		self.last_shot_no = -1
		self.ls = "Last shot"
		self.last_shot_label = QLabel(f"{self.ls} -1")
		self.last_shot_label.setAlignment(Qt.AlignCenter)
		self.last_shot_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
		self.last_shot_label.setStyleSheet("font-size:12px;")
		self.last_shot = LiveImageView('lime')
		self.last_shot.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
		last_shot_layout.addWidget(self.last_shot_label)
		last_shot_layout.addWidget(self.last_shot)

		# Right: Live preview
		video_layout = QVBoxLayout()
		self.lp = "Live preview"
		self.video_label = QLabel(f"{self.lp} -1")
		self.video_label.setAlignment(Qt.AlignCenter)
		self.video_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
		self.video_label.setStyleSheet("font-size:12px;")
		self.video = ToggleImageView('purple')
		self.video.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
		control_bar = QHBoxLayout()
		increment_button = IncrementButton(self)
		control_bar.addWidget(self.video_label)
		control_bar.addWidget(increment_button)
		video_layout.addLayout(control_bar)
		video_layout.addWidget(self.video)

		preview.addLayout(last_shot_layout)
		preview.addLayout(video_layout)

		main_layout.addLayout(preview)

		# Pass the new_image function, so the buttons know what to do when an image is taken.
		self.controls = SettingsControls(self.new_image)

		self.controls.switch_tabs.connect(self.video.show_view)

		main_layout.addWidget(self.controls)
		
		widget = QWidget()
		widget.setLayout(main_layout)
		self.setCentralWidget(widget)

		# initialize ThreadPool
		self.threadpool = QThreadPool()

		# start VideoWorker
		self.video_worker = VideoWorker(video_device, self.width()//2-50, self.controls.image_settings)
		self.video_worker.signals.update_preview.connect(self.update_preview)
		self.video_worker.signals.update_analysis.connect(self.update_analysis)

		self.video_worker.analyzer.new_image.connect(self.new_image)
		self.video_worker.analyzer.update_progress.connect(self.update_progress)
		self.controls.threshold_changed.connect(self.video_worker.set_threshold)
		self.controls.interval_changed.connect(self.video_worker.set_interval)

		# Load image directory form config.
		if (self.controls.get_output_dir() == "" and output_dir != ""):
			print("Loading output dir from config.")
			# Make sure the path exists.
			Path(output_dir).mkdir(parents=True, exist_ok=True)
			self.controls.set_output_dir(output_dir)
		# Update the image number to the last image.
		if (self.controls.get_output_dir() != ""):
			self.controls.set_no(self.filesaver.get_last_file_number(self.controls.get_output_dir()))
			# Load previous image from storage.
			if self.controls.no > 0:
				self.last_shot_no = self.controls.no
				loaded_frame = self.filesaver.load(self.controls.get_output_dir(), self.controls.get_prefix(), self.controls.no)
				if loaded_frame is not None:
					image = self.video_worker.resize_image(loaded_frame)
					self.last_shot.update(image)
		self.controls.prefix_text.textChanged.connect(self.update_video_number)
		self.update_video_number()
		# Setup camera settings
		if inverted:
			self.controls.image_settings.invert_button.click()
		self.controls.image_settings.zoom_changed.connect(self.video_worker.set_zoom)
		self.controls.image_settings.zoom.setValue(zoom_level)
		
		self.threadpool.start(self.video_worker)
		
		self.audio_worker = AudioWorker()
		
		self.mute = False
		
		self.redo_shortcut = QShortcut(self)
		self.redo_shortcut.setKey('r')
		self.redo_shortcut.activated.connect(self.controls.retake_picture_button.take_picture)
		
		self.take_shortcut = QShortcut(self)
		self.take_shortcut.setKey('t')
		self.take_shortcut.activated.connect(self.controls.take_picture_button.take_picture)
		
		self.mute_shortcut = QShortcut(self)
		self.mute_shortcut.setKey('m')
		self.mute_shortcut.activated.connect(self.toggle_mute)
		
		self.run_shortcut = QShortcut(self)
		self.run_shortcut.setKey('s')
		self.run_shortcut.activated.connect(self.controls.run_button.toggle_shortcut)
		
	def update_video_number(self):
		self.last_shot_label.setText(f"{self.ls} {self.last_shot_no}")
		self.video_label.setText(f"{self.lp} {self.controls.no+1}")
		pass

	def toggle_mute(self):
		self.mute = not self.mute

	def closeEvent(self, event):
		self.video_worker.stop()

	def new_image(self, redo=False, manual=False):
		# Make sure we actually want to take a picture.
		if not self.controls.is_paused() or manual:
			# If we try and redo, while no image is selected, just return.
			if redo and self.last_shot_no < 1:
				print("Unable to redo, as no previous image was taken!")
				return

			if not self.mute:
				self.audio_worker.start()
			self.last_shot.update(self.video_worker.get_last_preview())
			if redo:
				shot_no = self.last_shot_no
			else:
				self.controls.no += 1
				shot_no = self.controls.no
				self.last_shot_no = shot_no
			self.filesaver.save(self.controls.get_output_dir(), self.controls.get_prefix(), shot_no, self.video_worker.get_last_frame())
			self.update_video_number()
		
	def update_progress(self, progress, max_progress, status):
		self.controls.update_progress(progress, max_progress)
		pass

	def update_preview(self, frame):
		self.video.update_main(frame)

	def update_analysis(self, frame, percent):
		self.video.update_secondary(frame)
		self.controls.update_percentage(percent)


class LiveImageView(QLabel):

	def __init__(self, color):
		super().__init__()
		self.setAutoFillBackground(True)
		self.setScaledContents(True)

		palette = self.palette()
		palette.setColor(QPalette.Window, QColor(color))
		self.setPalette(palette)

	def update(self, frame):
		img = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
		self.setPixmap(QPixmap.fromImage(img))
		
	def flash(self):
		white_frame = QPixmap()
		white_frame.fill()
		self.setPixmap(white_frame)

class ToggleImageView(LiveImageView):

	def __init__(self, color):
		super().__init__(color)
		self._main_view = True
		
	def get_pixmap(self):
		return super().pixmap

	def update_secondary(self, frame):
		if not self._main_view:
			super().update(frame)

	def update_main(self, frame):
		if self._main_view:
			super().update(frame)

	def show_view(self, show_main_view):
		self._main_view = show_main_view

class IncrementButton(QPushButton):
	
	def __init__(self, main_window: MainWindow):
		super().__init__()
		self.setText("Increment +")
		self.setCheckable(False)
		self.main_window = main_window
		self.clicked.connect(self.increment)

	def increment(self):
		self.main_window.controls.no+=1
		self.main_window.update_video_number()
		
	# def toggle_shortcut(self):
	# 	self.animateClick()

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()
