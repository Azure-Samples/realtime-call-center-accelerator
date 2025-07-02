# Realtime Call Center Solution Accelerator

One-click deploy Azure Solution Accelerator for Call Center Automation with OpenAI Realtime Models and Azure Communication Services. This Solution Accelerator provides a reference implementation for an AI-assisted call center solution that uses Azure Communication Services to provide a phone-based voice channel for customers to interact with an AI Agent.

![Screenshot](assets/screenshot.png)

#### Features:

- Directly talk to the AI Agent through the web interface
- Request a phone call to talk to the AI Agent via telephone
- Speaks multiple languages
- Ask questions about Azure products
- Interrupt the bot anytime
- Customizable knowledge base and system prompt
- Process sick leave requests via voice

#### What can I ask?

For this demo, the bot is able to answer questions about Microsoft Azure products, like Azure App Service, Azure Container Apps, and Azure Container Registry but its knowledge can be customized. Here is some inspiration for questions you can ask the bot:

> Which pricing tier of Azure App Service supports custom domains?

> What is the difference between scaling up and scaling out in Azure App Services?

## Get it running

### Set up the Azure Environment

To run this application, you can provision the resources to your Azure Subscription using the Azure Developer CLI.

From your command line:

```bash
# Login to the Azure Developer CLI
azd auth login

# Provision all the resources with the azure dev cli
# The following values should work:
# location=northeurope
# aiResourceLocation=swedencentral
azd up
```

#### Azure Communication Services

At the moment, the configuration of Azure Communication Services phone number is not automated. So you will need to follow the following steps manually.

1. Go to the [Azure Portal](https://portal.azure.com) and navigate to the Azure Communication Services resource that has been created
1. In the left menu, select **Phone numbers** and then click the **Get** button
1. Select a Country or region and choose **Toll free** as your number type
1. Follow the instructions to purchase a phone number
1. Add an `ACS_SOURCE_NUMBER=+xxx` environment variable to the `.azure/xxx/.env` file with the phone number

   **Note:** The phone number must be in E.164 format, e.g. `+49123456789`. When copying it from the Azure Portal using the copy button, it will be in the right format.

   <img src="assets/copy-number-hint.png" width="400" />

### Deploy the application

To deploy the application, you can use the script provided in the `azd-hooks` folder. This script will build and deploy the user interface and the backend API. Before running the script, make sure you have the Azure CLI and the Azure Communication Services extension installed.

```bash
az extension add --name communication
```

Run the script with the following commands:

```bash
# Get and set the value for AZURE_ENV_NAME
source <(azd env get-values | grep AZURE_ENV_NAME)

# Building and deploying the user interface and the backend API
bash ./azd-hooks/deploy.sh app $AZURE_ENV_NAME
```

When successful, you will see the following output with the URL of the deployed application:

```
Deployment complete. Application URI: <YOUR_APP>.azurecontainerapps.io
```

### Forward inbound calls to your application

To enable inbound calls, you will also need to add a Web Hook to the Event Grid System Topic resource.

1. Go to the [Azure Portal](https://portal.azure.com) and navigate to the **Event Grid System Topic** resource that has been created
1. In the left menu, select **Event Subscription** and then click the **+ Event Subscription** button
1. Give a name to the event subcription, e.g. `receive-call`
1. In the dropdown list **Filter to Event Types**, select **Incoming Call**
1. Set **Endpoint Type** to **Web Hook**
1. Click **Configure an endpoint**, add `https://<YOUR_APP>.azurecontainerapps.io/acs/incoming`, and click **Create**

## Cloud Infrastructure

![Azure Architecture](assets/architecture.png)

## Local Development

Running this application locally, still requires some Azure Services in the cloud, so make sure to [set up the Azure environment](#set-up-the-azure-environment) first.

### Create a Tunnel

We use [ngrok](https://ngrok.com/) to tunnel `localhost` to a publically available URL while developing. This is needed, as Azure Communication Services need a URL for the callbacks and to send the voice packages to. This can not be `localhost` and must be reachable from Azure Communication Services. For the first time, you might need to install ngrok and create a free account.

Start the ngrok server.

```bash
ngrok http http://localhost:8765
```

This will create a public URL that tunnels to your localhost. You will see an output like this:

```
Forwarding https://1234-567-123-456-789.ngrok-free.app -> http://localhost:8765
```

Note the public domain (in this case `1234-567-123-456-789.ngrok-free.app`), as you will need it later to set the environment variables.

### Setup the local environment

If you are running this application locally, for the first time, we recommend setting up a Python environment. **This only needs to be done once.**

```bash
python -m venv .venv
```

Activate the local Python environment.

```bash
source .venv/bin/activate
```

Install the packages

```bash
pip install -r src/app/requirements.txt
```

Set the environment variables.

```bash
source <(azd env get-values)
azd env get-values > .env
```

### Start the application

Override the callback urls with your ngrok domain (Example: `1234-567-123-456-789.ngrok-free.app`)

For Bash:

```bash
export ACS_CALLBACK_PATH="https://<YOUR_NGROK_DOMAIN>/acs"
export ACS_MEDIA_STREAMING_WEBSOCKET_PATH="wss://<YOUR_NGROK_DOMAIN>/realtime-acs"
```

For PowerShell:

```pwsh
setx ACS_CALLBACK_PATH="https://<YOUR_NGROK_DOMAIN>/acs"
setx ACS_MEDIA_STREAMING_WEBSOCKET_PATH="wss://<YOUR_NGROK_DOMAIN>/realtime-acs"
```

Start the application

```bash
python src/app/app.py
```

To make inbound calls work for local development, you need to [set up another Event Grid System Topic](#forward-inbound-calls-to-your-application) and set the Web Socket endpoint to your ngrok domain (e.g. `https://1234-567-123-456-789/acs/incoming`).

## Customization

You can customize the knowledge base and the system prompt of the bot.

### Knowledge base

The knowledge base is stored in the `data` folder. After running the deployment script, the contents of this folder will be copied to the Azure Storage Account from where it is indexed and vectorized in the Azure AI Search service.

To customize the knowledge base, you can add or remove files from the `data` folder and [re-run the deployment script](#deploy-the-application).

### System prompt

By default, the [hardcoded system prompt](src/app/system_prompt.md) is used. You can customize the system prompt by placing a file named `system_prompt.md` in the `prompt` container of the Azure Storage Account. If this file exists, it will be used instead of the hardcoded system prompt.

---

## Contributors

(alphabetical order)

- [Carlos Raul Garcia](https://www.linkedin.com/in/carlosgarcialalicata/)
- [Sasa Juratovic](https://www.linkedin.com/in/sasajuratovic/)
- [Richard Lagrange](https://www.linkedin.com/in/richard-lagrange/)
- [Thibo Rosemplatt](https://github.com/thiborose)
- [Sanjay Singh](https://www.linkedin.com/in/san360/)
- [Robin-Manuel Thiel](https://www.linkedin.com/in/robinmanuelthiel/)
- [Yimi Wang](https://www.linkedin.com/in/yimiwang/)

## Related content

- This project was based on [Azure-Samples/on-the-road-copilot](https://github.com/Azure-Samples/on-the-road-copilot)
- For a more sophisticated full call center solution on Azure, check out [microsoft/call-center-ai](https://github.com/microsoft/call-center-ai)

### Sick Leave Processing

This solution accelerator includes functionality to handle employee sick leave requests via voice calls. When a caller mentions they need to report sick leave, the AI assistant collects relevant information and submits it to a configured API endpoint.

To enable this feature:

1. Configure the following environment variables with your API endpoints:
   - `SICK_LEAVE_API_URL`: https://pacific-mock.azurewebsites.net/api/sickleave/apply (for submitting sick leave requests)
   - `SICK_LEAVE_BALANCE_API_URL`: https://pacific-mock.azurewebsites.net/api/sickleave/balance (for checking leave balances)
2. Ensure your API can accept the request format documented in `docs/sick_leave_feature.md`

#### Leave Management Server Integration

Your leave management server should expose a RESTful API endpoint for accepting sick leave requests. The accelerator will send POST requests with employee information and leave details to this endpoint.

**Setting up for development:**
```bash
# Create a .env file in src/app directory
echo "SICK_LEAVE_API_URL=https://your-leave-server.example.com/api/sick-leave" > src/app/.env

# For testing with a mock server
npm install -g json-server
json-server --watch src/app/mock-leave-api.json --port 3000
# Then set SICK_LEAVE_API_URL=http://localhost:3000/sick-leave
```

For more details on this feature, see:
- [Sick Leave Feature Documentation](docs/sick_leave_feature.md)
- [Leave API Configuration](docs/leave_api_config.md)

---

**Trademarks:** This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.
