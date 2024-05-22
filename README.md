# Recipe App API (Backend)

The purpose for this is to learn the advanced concepts of Python Django API with Test Driven Development methodology.

I utilized the following technologies in this project:
- Django
- Docker
- GitHub Actions
- Flake8 (linting)


## Getting Started

To run this project, you will need to have docker setup on your machine.

Make sure to create a `.env` file in your root folder for reference a sample is created for you.

After setting up docker in cli and desktop, run the following commands:

### For building the docker image
```bash
  docker-compose build
```
### For Executing the tests
```bash
    docker-compose run --rm app sh -c "python manage.py test"
```
### For running wait for db command
```bash
    docker-compose run --rm app sh -c "python manage.py wait_for_db"
```
### For checking the linting using flake8
```bash
    docker-compose run --rm app sh -c "flake8"
```
## Features

- Recipe API
- User API
- Tags API
- Ingredients API
- Filtering with tags and ingredients
