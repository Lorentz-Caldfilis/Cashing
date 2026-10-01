"""Local background copy and shared, legible painting beneath both spaces."""
from pathlib import Path
import logging
from PySide6.QtCore import QSaveFile, QIODevice, QRectF, Qt
from PySide6.QtGui import QImageReader, QImage, QPainter, QColor
from PySide6.QtWidgets import QWidget
from ui import theme

BACKGROUND_FILE = "appearance-background.png"
MAX_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 25_000_000


def read_image(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("图片过大，请选择小于 64 MB 的图片。")
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > MAX_PIXELS:
        raise ValueError("无法读取图片，或图片超过 2500 万像素。")
    if max(size.width(), size.height()) > 4096:
        reader.setScaledSize(size.scaled(4096, 4096, Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        raise ValueError("图片无法解码，请选择 PNG、JPEG、WebP 或 BMP 图片。")
    return image


class BackgroundStore:
    def __init__(self, directory):
        self.path = Path(directory) / BACKGROUND_FILE

    def load(self):
        if not self.path.exists():
            return QImage()
        try:
            return read_image(self.path)
        except (OSError, ValueError):
            logging.warning("Could not load local background; using default")
            return QImage()

    def import_image(self, source):
        image = read_image(source)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        output = QSaveFile(str(self.path))
        if not output.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError("无法保存背景，请检查数据目录权限。")
        if not image.save(output, "PNG"):
            output.cancelWriting()
            raise OSError("无法保存背景图片。")
        if not output.commit():
            raise OSError("无法替换背景，原背景仍然保留。")
        return image

    def reset(self):
        self.path.unlink(missing_ok=True)


class BackgroundCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("backgroundCanvas")
        self.image = QImage()
        self._scaled = QImage()

    def set_image(self, image):
        self.image = image
        self._scaled = QImage()
        self.update()

    def resizeEvent(self, event):
        self._scaled = QImage()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.BG))
        if self.image.isNull():
            return
        if self._scaled.isNull():
            self._scaled = self.image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                              Qt.TransformationMode.SmoothTransformation)
        painter.drawImage((self.width() - self._scaled.width()) // 2,
                          (self.height() - self._scaled.height()) // 2, self._scaled)
        painter.fillRect(self.rect(), QColor(247, 248, 250, 55))
        painter.fillRect(0, 0, self.width(), 88, QColor(247, 248, 250, 245))
        painter.fillRect(0, self.height() - 64, self.width(), 64, QColor(247, 248, 250, 245))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = min(720, self.width() - 32)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(247, 248, 250, 245))
        painter.drawRoundedRect(QRectF((self.width() - width) / 2, 96, width,
                                      max(0, self.height() - 172)), 20, 20)
