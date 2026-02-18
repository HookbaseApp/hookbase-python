"""Verify incoming webhook signatures in your application."""

from hookbase import Webhook, WebhookVerificationError

# Initialize with the endpoint's signing secret
wh = Webhook("whsec_your_secret_here")


# --- Flask example ---
def flask_example():
    from flask import Flask, request, jsonify

    app = Flask(__name__)

    @app.route("/webhooks", methods=["POST"])
    def handle_webhook():
        try:
            payload = wh.verify(request.get_data(as_text=True), dict(request.headers))
        except WebhookVerificationError as e:
            return jsonify({"error": str(e)}), 400

        event_type = payload.get("eventType", "unknown")
        print(f"Received verified event: {event_type}")
        return jsonify({"received": True}), 200


# --- FastAPI example ---
def fastapi_example():
    from fastapi import FastAPI, Request, HTTPException

    app = FastAPI()

    @app.post("/webhooks")
    async def handle_webhook(request: Request):
        body = await request.body()
        headers = dict(request.headers)
        try:
            payload = wh.verify(body, headers)
        except WebhookVerificationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {"received": True, "event_type": payload.get("eventType")}


# --- Django example ---
def django_example():
    """
    # views.py
    import json
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    from hookbase import Webhook, WebhookVerificationError

    wh = Webhook("whsec_your_secret_here")

    @csrf_exempt
    def webhook_handler(request):
        if request.method != "POST":
            return JsonResponse({"error": "Method not allowed"}, status=405)
        try:
            payload = wh.verify(request.body, dict(request.headers))
        except WebhookVerificationError as e:
            return JsonResponse({"error": str(e)}, status=400)
        return JsonResponse({"received": True})
    """
    pass
