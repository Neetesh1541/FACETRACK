
from pathlib import Path

import cv2
import numpy as np


# AI model files
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "face_models"

DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"


class FaceEngine:

    def __init__(self):
        if not DETECTOR_MODEL.exists():
            raise FileNotFoundError(f"Detector model missing: {DETECTOR_MODEL}")

        if not RECOGNIZER_MODEL.exists():
            raise FileNotFoundError(f"Recognizer model missing: {RECOGNIZER_MODEL}")

        self.detector = cv2.FaceDetectorYN_create(
            str(DETECTOR_MODEL),
            "",
            (320, 320),
            0.9,
            0.3,
            5000
        )

        self.recognizer = cv2.FaceRecognizerSF_create(
            str(RECOGNIZER_MODEL),
            ""
        )

    def detect_faces(self, image):
        if image is None or image.size == 0:
            raise ValueError("Invalid image")

        height, width = image.shape[:2]

        self.detector.setInputSize((width, height))

        _, faces = self.detector.detect(image)

        if faces is None:
            return []

        return faces

    def generate_embedding(self, image):
        faces = self.detect_faces(image)

        if len(faces) == 0:
            raise ValueError("No face detected")

        if len(faces) > 1:
            raise ValueError("Multiple faces detected. Only one person should be visible.")

        aligned_face = self.recognizer.alignCrop(image, faces[0])

        embedding = self.recognizer.feature(aligned_face)

        embedding = embedding.flatten().astype(np.float32)

        return embedding

    def compare_faces(self, embedding1, embedding2):
        embedding1 = np.asarray(embedding1, dtype=np.float32).reshape(1, -1)
        embedding2 = np.asarray(embedding2, dtype=np.float32).reshape(1, -1)

        if embedding1.shape != embedding2.shape:
            raise ValueError("Face embeddings have different dimensions")

        similarity = float(
            np.dot(embedding1, embedding2.T)[0][0]
            / (
                np.linalg.norm(embedding1)
                * np.linalg.norm(embedding2)
                + 1e-10
            )
        )

        return similarity


face_engine = FaceEngine()
