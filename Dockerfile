FROM nvidia/cuda:11.2.2-cudnn8-runtime-ubuntu20.04

# Set the working directory
WORKDIR /app

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the source code into the container
COPY src/ ./src
COPY ultralytics/ ./ultralytics
COPY datasets/ ./datasets
COPY weights/ ./weights
COPY tempDir/ ./tempDir
COPY output/ ./output

# Set default environment variables
ENV RUN_MODE=streamlit
ENV OAUTH2_INTROSPECT_URL=https://your-auth-server.com/oauth2/introspect
ENV OAUTH2_TOKEN_URL=https://your-auth-server.com/oauth2/token
ENV CLIENT_ID=your-client-id
ENV CLIENT_SECRET=your-client-secret

# Command to run the application with the arguments
CMD ["sh", "-c", "python3 src/ui.py --run-mode $RUN_MODE --oauth2-introspect-url $OAUTH2_INTROSPECT_URL --oauth2-token-url $OAUTH2_TOKEN_URL --client-id $CLIENT_ID --client-secret $CLIENT_SECRET"]