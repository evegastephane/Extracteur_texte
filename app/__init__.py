from threading import Lock
import json
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .ocr import MAX_BYTES, OCRError, extract, readiness
from .paddle_engine import status as paddle_status, zone_status
from .cni import PROFILE, PROFILE_ID, align_card, decode_image, read_cni
import base64
import io


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2 * MAX_BYTES + 128 * 1024,
        # Werkzeug's multipart decoder buffers file chunks too. A 16 KiB
        # limit rejected ordinary uploads before the 10 MiB file check.
        MAX_FORM_MEMORY_SIZE=512 * 1024,
        MAX_FORM_PARTS=5,
        TRUSTED_HOSTS=["127.0.0.1", "localhost", "[::1]"],
    )
    if test_config:
        app.config.update(test_config)
    ocr_lock = Lock()

    @app.before_request
    def protect_local_service():
        # Reject foreign browser origins and DNS rebinding; no permissive CORS.
        origin = request.headers.get("Origin")
        if origin:
            try:
                parsed = urlsplit(origin)
            except ValueError:
                return jsonify(error={"code": "foreign_origin", "message": "Origine de requête invalide."}), 403
            if parsed.scheme != request.scheme or parsed.netloc != request.host:
                return jsonify(error={"code": "foreign_origin", "message": "Ouvrez l’application directement dans votre navigateur local."}), 403
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            return jsonify(error={"code": "foreign_origin", "message": "Requête externe refusée."}), 403

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        state = cni_state()
        return jsonify(state), 200 if state["ready"] else 503

    @app.post("/api/ocr")
    def ocr():
        image = request.files.get("image")
        if image is None:
            raise OCRError("missing_image", "Choisissez une image avant de lancer l’extraction.")
        if not ocr_lock.acquire(blocking=False):
            raise OCRError("busy", "Une extraction est déjà en cours. Réessayez dans un instant.", 429)
        try:
            language = request.form.get("language", "fra")
            engine = request.form.get("engine", "tesseract")
            if engine not in {"tesseract", "paddleocr"}:
                raise OCRError("invalid_engine", "Choisissez Tesseract ou PaddleOCR.")
            raw_options = request.form.get("options")
            structured = request.form.get("structured", "true")
            if structured not in {"true", "false"}:
                raise OCRError("invalid_options", "Mode d’extraction invalide.")
            if structured == "true" or engine == "paddleocr":
                try:
                    options = json.loads(raw_options) if raw_options is not None else {}
                except ValueError:
                    raise OCRError("invalid_options", "Réglages d’image invalides.") from None
                if not isinstance(options, dict):
                    raise OCRError("invalid_options", "Réglages d’image invalides.")
                if structured == "true":
                    result = extract(image.read(MAX_BYTES + 1), language, options, engine=engine, structured=True)
                    return jsonify(**result, language=language, engine=engine)
                text = extract(image.read(MAX_BYTES + 1), language, options, engine=engine)
            elif raw_options is None:
                text = extract(image.read(MAX_BYTES + 1), language)
            else:
                try:
                    options = json.loads(raw_options)
                except (ValueError, TypeError):
                    raise OCRError("invalid_options", "Réglages d’image invalides.") from None
                if not isinstance(options, dict):
                    raise OCRError("invalid_options", "Réglages d’image invalides.")
                text = extract(image.read(MAX_BYTES + 1), language, options)
            return jsonify(text=text, language=language)
        finally:
            ocr_lock.release()

    @app.get("/api/engines")
    def engines():
        return jsonify(tesseract=readiness(), paddleocr=paddle_status())

    def cni_state():
        return {"engine": "paddleocr", "ready": zone_status()["ready"],
                "profile": PROFILE_ID, "profile_status": PROFILE["status"],
                "classification": "deferred", "verso_zones": bool(PROFILE.get("back", {}).get("regions")), "verso_ocr": False}

    @app.get("/api/cni/status")
    def cni_status():
        return jsonify(cni_state())

    @app.post("/api/cni/align")
    def cni_align():
        upload = request.files.get("image")
        if upload is None:
            raise OCRError("missing_image", "Ajoutez une photo de la carte.")
        with decode_image(upload.read(MAX_BYTES + 1)) as image:
            aligned, details = align_card(image)
        with aligned:
            output = io.BytesIO()
            aligned.save(output, format="PNG")
        return jsonify(image=base64.b64encode(output.getvalue()).decode("ascii"), alignment=details)

    @app.post("/api/cni/read")
    def cni_read():
        front, back = request.files.get("recto"), request.files.get("verso")
        if front is None or back is None:
            raise OCRError("missing_sides", "Ajoutez le recto et le verso avant de lancer la lecture.")
        if not ocr_lock.acquire(blocking=False):
            raise OCRError("busy", "Une lecture est déjà en cours. Réessayez dans un instant.", 429)
        try:
            result = read_cni(front.read(MAX_BYTES + 1), back.read(MAX_BYTES + 1))
            return jsonify(result)
        finally:
            ocr_lock.release()

    @app.errorhandler(OCRError)
    def ocr_error(error):
        return jsonify(error={"code": error.code, "message": error.message}), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return jsonify(error={"code": "request_too_large", "message": "Le fichier est trop volumineux. Limite : 10 Mio."}), 413

    @app.errorhandler(Exception)
    def unexpected(error):
        if isinstance(error, HTTPException):
            return jsonify(error={"code": "http_error", "message": "Requête non prise en charge."}), error.code
        # Do not log exception strings: OCR errors can contain document data.
        app.logger.error("Unexpected OCR service failure (%s)", type(error).__name__)
        return jsonify(error={"code": "internal_error", "message": "L’extraction a échoué. Réessayez avec une autre image."}), 500

    return app
