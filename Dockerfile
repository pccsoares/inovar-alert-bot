# Use Azure Functions Python 3.11 base image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set working directory
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copy requirements first for better caching
COPY requirements.txt /home/site/wwwroot/
WORKDIR /home/site/wwwroot

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY . /home/site/wwwroot

# Ensure proper permissions
RUN chmod -R 755 /home/site/wwwroot
