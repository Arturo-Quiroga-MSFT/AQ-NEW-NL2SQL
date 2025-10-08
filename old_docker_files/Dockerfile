# Use the official lightweight Python image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install ODBC runtime and Microsoft ODBC Driver 18 for SQL Server (for pyodbc)
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        apt-transport-https \
        unixodbc \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Copy the entire project into the image
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Set working directory to the Streamlit app folder
WORKDIR /app/ui/streamlit_app

# Set PYTHONPATH so the app can import modules from the project root
ENV PYTHONPATH="/app"

# Expose Streamlit default port
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
