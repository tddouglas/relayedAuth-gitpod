# Adyen [online payment](https://docs.adyen.com/online-payments) integration demos

## Run this integration in seconds using [Gitpod](https://gitpod.io/)

* Open your [Adyen Test Account](https://ca-test.adyen.com/ca/ca/overview/default.shtml) and create a set of [API keys](https://docs.adyen.com/user-management/how-to-get-the-api-key).
* Go to [Gitpod account variables](https://gitpod.io/variables).
* Set the `ADYEN_HMAC_KEY` and `ADYEN_BALANCE_PLATFORM` variables. Currently, HMAC isn't used for relayedAuth so add a dummy value.
* Click the button below.

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/tddouglas/relayedAuth-gitpod)

## Details
A simple relayed auth listener - intended to be launched via gitpod and hardcoded to approve relayed auth transactions.

## Requirements

- Python 3.5 or greater
- Python libraries:
  - flask
  - uuid
  - Adyen v8.0.0 or higher

## Gitpod Usage

RelayedAuth delivers asynchronous notifications during issuing auth events. It is important to test them during the setup of your integration. You can find more information about relayed auth [here](https://docs.adyen.com/issuing/authorisation/relayed-authorisation/).

This sample application provides a simple relayed auth endpoint exposed at `/api/webhooks/relayedAuth`. For it to work, you need to:

1. Be running this repo via Gitpod
2. Setup Adyen's BankBO relayed auth endpoint to point to your Gitpod instance. 

### Making your server reachable
Your endpoint that will consume the incoming relayed auth message must be publicly accessible.

When using Gitpod, the webhook URL will be the host assigned by Gitpod
```
  https://myorg-myrepo-y8ad7pso0w5.ws-eu75.gitpod.io/api/webhooks/notifications
```
**Note:** when starting a new Gitpod workspace the host changes, make sure to **update the Webhook URL** in the Customer Area

### Set up relayed auth
* In Bank BO go to Issuing -> Relayed Auth and create a new 'Standard notification' webhook.
* Enter the URL of your application/endpoint (see options [above](#making-your-server-reachable))
* Define username and password for Basic Authentication
* Generate the HMAC Key
* Optionally, in Additional Settings, add the data you want to receive. A good example is 'Payment Account Reference'.
* Make sure the webhook is **Enabled** (therefore it can receive the notifications)

That's it! Every time you perform a new payment, your application will receive a notification from the Adyen platform.

## Contributing

We commit all our new features directly into our GitHub repository. Feel free to request or suggest new features or code changes yourself as well!!

Find out more in our [Contributing](https://github.com/adyen-examples/.github/blob/main/CONTRIBUTING.md) guidelines.

## License

MIT license. For more information, see the **LICENSE** file in the root directory
