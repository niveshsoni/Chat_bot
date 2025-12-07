# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside container
WORKDIR /app

# Copy only requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .


# Expose the port your Python app runs on (example: Flask default = 5000)
EXPOSE 8000



# Command to run your Python file (replace main.py with your file)
CMD ["python", "api.py"]
