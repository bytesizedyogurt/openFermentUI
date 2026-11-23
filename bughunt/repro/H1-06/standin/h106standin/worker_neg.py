"""The control worker of engine h106neg: one thing whose stated absolute precision is -1, a number
EnginePrecision's Field(ge=0) refuses, so the service sets the engine aside in words."""
from h106standin.worker import main

THINGS = [{"id": "negprec", "title": "a thing whose stated absolute precision is negative", "configurations": [],
           "precision": {"rtol": 0, "atol": -1}}]

if __name__ == "__main__":
    main(THINGS)
