# Use Python runtime as a parent image
FROM python:3

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

# Run CryptoCompareWebSocketOHLCV when the container launches
CMD ["python", "CryptoCompareWebSocketOHLCV.py"]


