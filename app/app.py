import binascii
import logging
import hmac
import hashlib
import base64
from Adyen.util import is_valid_hmac_notification
from functools import wraps
from flask import Flask, render_template, send_from_directory, request, jsonify

from main.config import *

VALIDATE_HMAC = False
VALIDATE_BASIC_AUTH = False

webhooks = []


def check_hmac(payload, hmac_key, hmac_sig):
    """
    Receives outcome of each payment
    :param payload: Request body represented as a string
    :param hmac_key: Hmac Key as generated in the BPCA and stored as gitpod secret variable
    :param hmac_sig: HMAC signature from notification header
    :return: True if HMAC secret key matches key in notification header. False otherwise
    """

    hmac_key = binascii.a2b_hex(hmac_key)
    # Calculate signature
    calculated_hmac = hmac.new(hmac_key, payload.encode('utf-8'), hashlib.sha256).digest()
    calculated_hmac_b64 = base64.b64encode(calculated_hmac)
    received_hmac_b64 = hmac_sig.encode('utf-8')
    valid_signature = hmac.compare_digest(received_hmac_b64, calculated_hmac_b64)

    if not valid_signature:
        logging.debug('HMAC is invalid: {} {}'.format(received_hmac_b64, calculated_hmac_b64))
        return False

    return True


def check_auth(username, password):
    """
    Checks basic auth credentials.
    :param username: Username as configured in the BPCA and stored as gitpod secret variable
    :param password: Password as configured in the BPCA and stored as gitpod secret variable
    :return: True if basic auth information is valid. False otherwise
    """
    adyen_username, adyen_password = get_adyen_relayed_basic_auth()
    if not (adyen_username == username and adyen_password == password):
        return False
    return True


def basic_auth_required(f):
    @wraps(f)
    def wrapped_view(**kwargs):
        if VALIDATE_BASIC_AUTH:
            auth = request.authorization
            if not (auth and check_auth(auth.username, auth.password)):
                logging.info("Invalid auth credentials or auth credentials not provided. Declining")
                return ('Unauthorized', 401, {
                    'WWW-Authenticate': 'Basic realm="Login Required"'
                })
        return f(**kwargs)

    return wrapped_view


def create_app():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    app = Flask('app')

    # Register 404 handler
    app.register_error_handler(404, page_not_found)

    # Routes:
    @app.route('/')
    def home():
        return render_template('home.html')

    # Relayed Auth Behavior
    @app.route('/api/webhooks/relayedAuth', methods=['POST'])
    @basic_auth_required
    def relayedAuth_notification():
        """
        Receives outcome of each payment, logs it, and makes authorisation decision. Checks HMAC and Basic Auth on
        Webhook if toggles enabled. Amount = 9.99 is the 'magic amount' which results in a relayed auth decline.
        All other amounts will be approved.
        :return: Approve or Decline relayed auth response body depending on auth amount sent in request.
        """
        APPROVE = {
            "authorisationDecision": {
                "status": "Authorised"
            },
            "reference": "relayed_auth_approve_12345",
            "metadata": {
                "transactionId": "relayed_auth_approve_metadata-123"
            }
        }

        DECLINE = {
            "authorisationDecision": {
                "status": "Refused"
            },
            "reference": "relayed_auth_decline_123",
            "metadata": {
                "transactionId": "relayed_auth_decline_metadata-123"
            }
        }
        relayed_auth_string = request.get_data(as_text=True)

        logging.debug(request.headers)
        relayed_auth_json = request.get_json()
        webhooks.insert(0, relayed_auth_json)
        logging.info(f"Relayed Auth body:\n{relayed_auth_json}")

        if VALIDATE_HMAC:
            hmac_request_header = request.headers["Hmacsignature"]
            if not check_hmac(relayed_auth_string, get_adyen_relayed_auth_hmac_key(), hmac_request_header):
                logging.info("Invalid HMAC signature in RelayedAuth")
                return DECLINE

        if abs(int(relayed_auth_json["amount"]["value"])) == 999:
            logging.info("Declining transaction as magic value was used")
            return DECLINE
        else:
            logging.info("Approving transaction")
            return APPROVE

    @app.route('/api/webhooks/bp-notifications', methods=['POST'])
    def webhook_bp_notifications():
        """
        Process Balance Platform Webhook. checks HMAC and Basic Auth on Webhook if toggles enabled.
        :return: Accept webhook response body for properly authenticated webhooks.
        """
        webhook_string = request.get_data(as_text=True)

        logging.debug(request.headers)
        webhook_json = request.get_json()
        webhooks.insert(0, webhook_json)
        logging.info(f"BP Webhook body:\n{webhook_json}")

        if VALIDATE_HMAC:
            hmac_request_header = request.headers["Hmacsignature"]
            if not check_hmac(webhook_string, get_adyen_hmac_key(), hmac_request_header):
                logging.info("Invalid HMAC signature in BP Webhook")
                return 'Failed HMAC validation'
        else:
            logging.info("Accepting Webhook")
            return '[accepted]'

    # Process incoming webhook notifications
    @app.route('/api/webhooks/old-notifications', methods=['POST'])
    def webhook_old_notifications():
        """
        Receives outcome of each payment. HMAC and Basic Auth NOT implemented on old webhook
        :return:
        """
        notifications = request.json['notificationItems']
        # fetch first( and only) NotificationRequestItem
        notification = notifications[0]

        if is_valid_hmac_notification(notification['NotificationRequestItem'], get_adyen_hmac_key()):
            # consume event asynchronously
            consume_event(notification)
        else:
            # invalid hmac: do not send [accepted] response
            raise Exception("Invalid HMAC signature")

        return '[accepted]'

    @app.route('/get_webhooks', methods=['GET'])
    def get_webhooks():
        # Return the webhooks as JSON
        return jsonify(webhooks), 200

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'img/favicon.ico')

    return app


#  process payload asynchronously
def consume_event(notification):
    logging.info(f"consume_event merchantReference: {notification['NotificationRequestItem']['merchantReference']} "
                 f"result? {notification['NotificationRequestItem']['success']}")

    # add item to DB, queue or run in a different thread


def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    web_app = create_app()

    logging.info(f"Running on http://localhost:{get_port()}")
    web_app.run(debug=True, port=get_port(), host='0.0.0.0')
