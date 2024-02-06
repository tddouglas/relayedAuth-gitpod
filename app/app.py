import binascii
import logging
import hmac
import hashlib
import base64
from Adyen.util import is_valid_hmac_notification
from flask import Flask, render_template, send_from_directory, request

from main.config import *


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
    def relayedAuth_notification():
        """
        Receives outcome of each payment
        :return:
        """
        APPROVE = {
            "authorisationDecision": {
                "status": "Authorised"
            },
            "reference": "myBalancePlatformPayment_12345",
            "metadata": {
                "customId": "your-own-custom-field-12345"
            }
        }

        DECLINE = {
            "authorisationDecision": {
                "status": "Refused"
            },
            "reference": "myBalancePlatformPayment_12345",
            "metadata": {
                "customId": "your-own-custom-field-12345"
            }
        }
        relayed_auth_body = request.get_json()
        print(request.headers)
        hmac_request_header = request.headers["Hmacsignature"]
        if checkHmac(relayed_auth_body, get_adyen_relayed_auth_hmac_key(), hmac_request_header):
            print(relayed_auth_body)

            # 9.99 is magic amount to trigger relayed auth decline# 9.99 is magic amount to trigger relayed auth decline
            if abs(int(relayed_auth_body["amount"]["value"])) == 999:
                return DECLINE
            else:
                return APPROVE

    def checkHmac(payload, hmac_key, hmac_sig):
        # payload is the request body as it is
        # hmac_key is the secret
        # hmac_sig is the signature from the header
        hmac_key = binascii.a2b_hex(hmac_key)
        # Calculate signature
        calculatedHmac = hmac.new(hmac_key, payload.encode('utf-8'), hashlib.sha256).digest()
        calculatedHmac_b64 = base64.b64encode(calculatedHmac)

        receivedHmac_b64 = hmac_sig.encode('utf-8')
        validSignature = hmac.compare_digest(receivedHmac_b64, calculatedHmac_b64)

        if not validSignature:
            print('HMAC is invalid: {} {}'.format(receivedHmac_b64, calculatedHmac_b64))
            return False

    # Process incoming webhook notifications
    @app.route('/api/webhooks/notifications', methods=['POST'])
    def webhook_notifications():
        """
        Receives outcome of each payment
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

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'img/favicon.ico')

    return app


#  process payload asynchronously
def consume_event(notification):
    print(f"consume_event merchantReference: {notification['NotificationRequestItem']['merchantReference']} "
          f"result? {notification['NotificationRequestItem']['success']}")

    # add item to DB, queue or run in a different thread


def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    web_app = create_app()

    logging.info(f"Running on http://localhost:{get_port()}")
    web_app.run(debug=True, port=get_port(), host='0.0.0.0')
