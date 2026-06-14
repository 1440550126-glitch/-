"""感知层：通过图片 / 视频认人（人脸识别）。

可选依赖 face_recognition + opencv。没装时 identify() 返回 None（无法识别），
其余流程不受影响——可以改用 chat 里的 /as 手动指定说话人来测试。

人脸库约定：把每个人的照片放到 data/faces/<face_id>.jpg，
其中 <face_id> 要和 relationships.yaml 里某个人的 face_id 对应。
"""

from __future__ import annotations

from pathlib import Path


class Perception:
    def __init__(self, faces_dir, authority=None) -> None:
        self.faces_dir = Path(faces_dir)
        self.authority = authority
        self._fr = None
        self.known: dict = {}  # face_id -> encoding
        try:
            import face_recognition  # 可选重型依赖

            self._fr = face_recognition
            self._load_faces()
        except Exception:
            self._fr = None

    @property
    def available(self) -> bool:
        return self._fr is not None and bool(self.known)

    def _load_faces(self) -> None:
        if not self.faces_dir.exists():
            return
        for img in self.faces_dir.glob("*.*"):
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            try:
                encs = self._fr.face_encodings(self._fr.load_image_file(str(img)))
                if encs:
                    self.known[img.stem] = encs[0]
            except Exception:
                continue

    def _face_id_to_name(self, face_id: str) -> str:
        if self.authority is not None:
            for p in self.authority.people.values():
                if p.get("face_id") == face_id:
                    return p["name"]
        return face_id

    def identify(self, image_path) -> str | None:
        """识别一张图片里的人，返回其名字（已登记）或 None。"""
        if not self.available:
            return None
        encs = self._fr.face_encodings(self._fr.load_image_file(str(image_path)))
        if not encs:
            return None
        ids = list(self.known.keys())
        vecs = list(self.known.values())
        matches = self._fr.compare_faces(vecs, encs[0], tolerance=0.5)
        for fid, ok in zip(ids, matches):
            if ok:
                return self._face_id_to_name(fid)
        return None

    def identify_video(self, video_path, sample_every: int = 30) -> str | None:
        """从视频里抽帧认人，返回第一个识别到的人。需要 opencv。"""
        if not self.available:
            return None
        try:
            import cv2  # 可选
        except Exception:
            return None
        cap = cv2.VideoCapture(str(video_path))
        idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % sample_every == 0:
                    rgb = frame[:, :, ::-1]
                    encs = self._fr.face_encodings(rgb)
                    if encs:
                        matches = self._fr.compare_faces(
                            list(self.known.values()), encs[0], tolerance=0.5
                        )
                        for fid, m in zip(self.known.keys(), matches):
                            if m:
                                return self._face_id_to_name(fid)
                idx += 1
        finally:
            cap.release()
        return None
