"""Encode the original generated bitmap as PNG and a multi-resolution Windows ICO."""
from pathlib import Path
import struct
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = QImage(str(ROOT / "assets/cashing-icon-source.png"))
    if source.isNull():
        raise RuntimeError("Missing original icon")
    source.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio,
                  Qt.TransformationMode.SmoothTransformation).save(str(ROOT / "assets/cashing-icon.png"))
    frames = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image = source.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Icon encoding failed")
        frames.append((size, bytes(data)))
    offset = 6 + 16 * len(frames)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    payload = bytearray()
    for size, data in frames:
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        payload.extend(data)
        offset += len(data)
    (ROOT / "assets/cashing-icon.ico").write_bytes(directory + payload)


if __name__ == "__main__":
    main()
