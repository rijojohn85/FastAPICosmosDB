# Azure CosmosDB Deployment Microservice

## Problem Statement

Develop a microservice to create Azure CosmosDB

Objective: Create a microservice that deploys Azure CosmosDB using Azure SDK

Requirements:

    1. Write endpoints to create/get/delete Azure CosmosDB
    2. Create a document to describe configuration needed in Azure CosmosDB
    3. Use poetry as the package manager for third party libraries

Assumptions:

    Use AzureCliCredential class to authenticate request for Azure SDK

Tech Stack:

    Framework: FastAPI

## To run the project

1. Clone the repository
```bash
git clone git@github.com:rijojohn85/FastAPICosmosDB.git
```
2. Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 
```
3. Install Dependencies
```bash
poetry install
```
4. Install and sign into Azure CLI
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login
````
5. Set up .env file:
 - Create Azure account
 - Create a new resource group
 - Generate gmail app password [Link](https://support.google.com/mail/answer/185833?hl=en)
```
AZURE_SUBSCRIPTION_ID=<azure subsciption id>
AZURE_RESOURCE_GROUP=<azure resource group name>

# Email Configuration
GMAIL_ADDRESS=<email id to send and recieve email notification>
GMAIL_PASSWORD=<app password for gmail> 
```
6. Run the uvicorn server
```bash
poetry run uvicorn app.main:app --reload
```
7. Open the browser and navigate to http://127.0.0.1:8000/
8. You can see the swagger documentation for the API at http://127.0.0.1:8000/docs

## Current Status:

1. API to create and Delete CosmosDB account is implemented
2. Email notification on creation of CosmosDB account is implemented
3. Get status of provisioning/deletion of CosmosDB account is implemented

## Next steps
1. Add more unit tests
2. Create and delete databases
3. Create and delete collections