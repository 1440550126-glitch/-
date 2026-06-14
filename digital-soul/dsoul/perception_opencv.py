"""树莓派友好的人脸识别后端：OpenCV Haar 检测 + LBPH 识别，**无需 dlib**。

需要 opencv-contrib-python（含 cv2.face）。比 face_recognition 轻得多、装得快，
精度略低——每个人多放几张照片可显著提升：
  data/faces/<face_id>.jpg            单张
  data/faces/<face_id>/*.jpg          多张（推荐）
接口与 dsoul.perception.Perception 对齐，可直接互换。
"""

from __future__ import annotations

from pathlib import Path


class OpenCVPerception:
    def __init__(self, faces_dir, authority=None, threshold: float = 70.0) -> None:
        self.faces_dir = Path(faces_dir)
        self.authority = authority
        self.threshold = threshold  # LBPH 置信度阈值（越小越严格）
        self._cv2 = None
        self._detector = None
        self._recognizer = None
        self._labels: dict[int, str] = {}  # label_int -> face_id
        try:
            import cv2

            self._cv2 = cv2
            self._detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self._recognizer = cv2.face.LBPHFaceRecognizer_create()
            self._train()
        except Exception:
            self._cv2 = None

    @property
    def known(self) -> dict:
        return self._labels  # 兼容接口：非空表示有已登记的人

    @property
    def available(self) -> bool:
        return self._recognizer is not None and bool(self._labels)

    def _images(self):
        out = []
        if not self.faces_dir.exists():
            return out
        for p in self.faces_dir.iterdir():
            if p.is_dir():
                for img in p.glob("*.*"):
                    if img.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        out.append((p.name, img))
            elif p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                out.append((p.stem, p))
        return out

    def _train(self) -> None:
        cv2 = self._cv2
        import numpy as np

        faces, labels, id_to_label = [], [], {}
        for face_id, img in self._images():
            gray = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                continue
            for (x, y, w, h) in self._detector.detectMultiScale(gray, 1.1, 5)[:1]:
                roi = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
                id_to_label.setdefault(face_id, len(id_to_label))
                faces.append(roi)
                labels.append(id_to_label[face_id])
        if faces:
            self._recognizer.train(faces, np.array(labels))
            self._labels = {v: k for k, v in id_to_label.items()}

    def _face_id_to_name(self, face_id: str) -> str:
        if self.authority is not None:
            for p in self.authority.people.values():
                if p.get("face_id") == face_id:
                    return p["name"]
        return face_id

    def _predict_gray(self, gray) -> list[str]:
        cv2 = self._cv2
        names = []
        for (x, y, w, h) in self._detector.detectMultiScale(gray, 1.1, 5):
            roi = cv2.resize(gray[y:y + h, x:x + w], (200, 200))
            label, conf = self._recognizer.predict(roi)
            if conf <= self.threshold and label in self._labels:
                names.append(self._face_id_to_name(self._labels[label]))
        return names

    def identify_frame(self, rgb) -> list[str]:
        if not self.available:
            return []
        import numpy as np

        cv2 = self._cv2
        gray = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2GRAY)
        return self._predict_gray(gray)

    def identify(self, image_path) -> str | None:
        if not self.available:
            return None
        gray = self._cv2.imread(str(image_path), self._cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return None
        got = self._predict_gray(gray)
        return got[0] if got else None

    def identify_video(self, video_path, sample_every: int = 30) -> str | None:
        if not self.available:
            return None
        cap = self._cv2.VideoCapture(str(video_path))
        idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % sample_every == 0:
                    got = self.identify_frame(frame[:, :, ::-1])
                    if got:
                        return got[0]
                idx += 1
        finally:
            cap.release()
        return None
