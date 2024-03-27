FROM python:3.9-alpine3.13
LABEL maintainer="muhammadahmed135"

ENV PYTHONUNBUFFERED 1

# Copy the requirements file
COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./app /app

# Create a directory in the container to hold the application code
WORKDIR /app

# Expose port 8000
EXPOSE 8000

# Install dependencies and create non-root user
ARG DEV=false
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    if [ $DEV = "true" ]; then /py/bin/pip install -r /tmp/requirements.dev.txt ; fi && \
    rm -rf /tmp && \
    adduser \
        --disabled-password \
        --no-create-home \
        django-user

# Set the PATH environment variable
ENV PATH="/py/bin:$PATH"

# Switch to the non-root user
USER django-user