# Alert Execution Engine

Dependencies can be installed using `pip3 install requests`. Run the program using `python3 main.py` command. Currently, we exit out of the python interpreter in order to abort the program. A more user friendly way would be to have the main thread print a prompt to the user and listen to specific user input in order to abort the program. The parallelization is also configurable in code - again a better UX would be to make a simple change to take this from command line so that it is configurable across runs.

Start the server using
```
docker run -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:latest
```

# Design decisions

1. We are retrieving all the alerts once when the service starts and storing it in memory.
2. We implement an Alert class which stores the state of a single alert in memory
3. We extend the alert client to support retries with exponential backoffs. This gives better resiliency against failures. At scale, we may want to introduce a circuit breaker between the alert engine and the alert server in order to avoid a cascading/thundering herd problem.
4. The scheduler has been implemented using a threaded timer, with the assumption that the service is I/O bound and not CPU bound. This however puts the Global Interpreter Lock as the bottleneck. If the scraping frequency increases OR if our computations become more complex (for implementing features like, say, warm up or cool down periods) and our functions end up being CPU bound, we may need to revisit this design decision and implement the scheduler using a multi processor. But at that point, sharing variables across processes to update alert state becomes challenging.
5. Failures are handler gracefully so that the workers don't die abruptly. A more scalable solution would involve having a persistent layer to store state and errors and a worker coming up can read from the state or even replay errored transactions.
