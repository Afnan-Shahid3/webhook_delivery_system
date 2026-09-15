# Webhook Delivery System

A webhook delivery system built with **Django, Django REST Framework, Celery, Redis, and PostgreSQL**.

The project was built to explore how a backend can deliver events to external HTTP endpoints asynchronously while handling retries, failures, idempotency, request signing, delivery tracking, and repeatedly failing endpoints.

The current implementation uses an **animal-selection event** as the example event, with the webhook system handling the delivery infrastructure around it.

---

## Features

* Asynchronous webhook delivery using **Celery**
* **Redis** as the Celery message broker
* Automatic retries for temporary failures
* **Exponential backoff** between retries
* HTTP failure classification
* Individual delivery tracking
* Individual delivery-attempt tracking
* **Idempotency keys** to prevent duplicate processing
* **HMAC-SHA256** webhook signatures
* Endpoint failure tracking
* **Circuit breaker** for repeatedly failing endpoints
* PostgreSQL persistence
* Web-based delivery dashboard
* Delivery detail and endpoint detail pages

---

## Tech Stack

| Technology            | Purpose                       |
| --------------------- | ----------------------------- |
| Python                | Programming language          |
| Django                | Backend framework             |
| Django REST Framework | API endpoint                  |
| PostgreSQL            | Database                      |
| Celery                | Asynchronous task processing  |
| Redis                 | Celery message broker         |
| Requests              | Sending HTTP webhook requests |
| HMAC-SHA256           | Webhook request signing       |
| HTML/CSS              | Web dashboard                 |

---

## How It Works

The main workflow is:

```text
Create Event
     │
     ▼
Store Event in PostgreSQL
     │
     ▼
Find Active Endpoints
     │
     ▼
Create a Delivery for each Endpoint
     │
     ▼
Queue Celery Task
     │
     ▼
Celery Worker
     │
     ▼
HTTP POST to Endpoint
     │
     ├───────────────┐
     │               │
   Success         Failure
     │               │
     ▼               ▼
 Delivered       Classify Failure
                     │
                     ▼
                Retry if applicable
                     │
                     ▼
                Record Attempts
                     │
                     ▼
              Mark Delivery Failed
```

---

## Event Creation

Events can be created through the web interface at:

```text
/add_event/
```

The current form creates an event with:

```python
event.type = "create"
event.data = {"name": event.name}
```

The system then finds all active endpoints:

```python
Endpoint.objects.filter(is_active=True)
```

For each endpoint, a separate `Delivery` is created and a Celery task is queued.

An endpoint whose circuit breaker is currently open is skipped.

---

## Webhook Request

The Celery worker sends the event data to the endpoint using an HTTP `POST` request.

The request contains:

```text
Content-Type: application/json
Idempotency-Key: <delivery UUID>
X-Webhook-Signature: <HMAC-SHA256 signature>
```

The JSON body contains the event's `data`.

For example:

```json
{
    "name": "cat"
}
```

---

## Asynchronous Processing

Webhook delivery is handled by a Celery task rather than being performed directly during event creation.

The task:

```text
send_animal_name(delivery_id)
```

retrieves the `Delivery` from PostgreSQL and sends the HTTP request.

Redis acts as the Celery broker between Django and the Celery worker.

This allows the event-creation request and webhook delivery process to be separated.

---

## Retry System

The system retries temporary delivery failures.

Retries are performed for:

* HTTP `5xx` responses
* Request timeouts
* Connection errors

The current retry configuration allows **3 retries after the initial attempt**, giving a maximum of **4 total attempts**.

The retry delay is calculated as:

```python
5 * (2 ** self.request.retries)
```

This produces:

```text
Initial attempt
      │
      ▼
   Failure
      │
      ▼
   5 seconds
      │
      ▼
   Retry
      │
      ▼
   Failure
      │
      ▼
  10 seconds
      │
      ▼
   Retry
      │
      ▼
   Failure
      │
      ▼
  20 seconds
      │
      ▼
   Retry
```

If all retries are exhausted, the delivery is marked as failed.

---

## Failure Classification

Each delivery attempt stores an attempt status.

The current statuses are:

| Code  | Meaning          |
| ----- | ---------------- |
| `SU`  | Success          |
| `CE`  | Client Error     |
| `SE`  | Server Error     |
| `TO`  | Timeout          |
| `COE` | Connection Error |

HTTP responses are handled as follows:

| Response  | Result                 |
| --------- | ---------------------- |
| `200–299` | Successful delivery    |
| `400–499` | Client error, no retry |
| `500+`    | Server error, retry    |

Timeouts and connection errors are also retried.

Every attempt is stored in the `DeliveryAttempt` model along with information such as:

* Attempt number
* Attempt time
* HTTP response status code
* Response body
* Attempt status

### Attempt Numbers

The current implementation stores Celery's `self.request.retries` value directly.

Therefore, attempts are recorded as:

```text
0 → initial attempt
1 → first retry
2 → second retry
3 → third retry
```

---

## Idempotency

Each `Delivery` receives a unique UUID stored in the `key` field.

That key is sent to the receiving endpoint as:

```text
Idempotency-Key: <delivery key>
```

The example receiver stores processed keys in the `ProcessedIdempotentKeys` model.

When a request arrives, the receiver checks whether the key has already been processed.

If it has already been processed, the receiver returns:

```json
{
    "status": 200,
    "message": "Already Processed"
}
```

This prevents the same delivery key from being processed more than once by the example receiver.

---

## Webhook Signing

Webhook requests are signed using **HMAC-SHA256**.

The sending task creates the signature using the endpoint's configured secret and the JSON payload:

```python
signature = hmac.new(
    delivery.endpoint.secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()
```

The signature is sent through:

```text
X-Webhook-Signature
```

The example `/api/animal/` receiver calculates an expected HMAC signature and compares it using `hmac.compare_digest()`.

Requests with an invalid signature return:

```text
401 Unauthorized
```

### Current Configuration

The sender uses:

```text
Endpoint.secret
```

while the example receiver currently verifies against:

```text
settings.WEBHOOK_SECRET
```

Therefore, the configured values need to correspond for the example sender and receiver to successfully authenticate each other.

---

## Circuit Breaker

The system tracks consecutive failed deliveries for each endpoint using:

```text
consecutive_failures
```

A failure is counted after a delivery has exhausted its configured retries and is finally marked as failed.

When an endpoint reaches **5 consecutive failed deliveries**, the circuit breaker is opened for **10 minutes**:

```python
circuit_broken_until = timezone.now() + timedelta(minutes=10)
```

When new events are created, endpoints whose circuit-breaker timestamp is still in the future are skipped.

```text
Endpoint Active
      │
      ▼
Delivery fails repeatedly
      │
      ▼
5 exhausted deliveries
      │
      ▼
Circuit opened
      │
      ▼
Skip endpoint for 10 minutes
      │
      ▼
Circuit-breaker time expires
      │
      ▼
Endpoint can receive new deliveries
```

A successful delivery resets:

```text
consecutive_failures = 0
```

---

## Data Models

The system currently contains the following models.

### Event

Stores an event that needs to be delivered.

```text
Event
├── name
├── type
├── data
└── created_at
```

The available event type choices are currently:

```text
create
delete
update
```

The current web interface creates events using the `create` type.

---

### Endpoint

Represents an external webhook receiver.

```text
Endpoint
├── client
├── url
├── is_active
├── secret
├── circuit_broken_until
└── consecutive_failures
```

The endpoint URL is unique.

---

### Delivery

Represents one event being delivered to one endpoint.

```text
Delivery
├── event
├── endpoint
├── delivery_status
├── created_at
└── key
```

The available delivery statuses are:

```text
process → IN PROCESS
deliver → DELIVERED
fail    → DELIVERY FAILED
```

A separate `Delivery` is created for every active endpoint receiving an event.

---

### DeliveryAttempt

Stores information about an individual attempt to deliver a webhook.

```text
DeliveryAttempt
├── delivery
├── attempted_at
├── attempt_number
├── response_body
├── response_status_code
└── attempt_status
```

Each retry creates another attempt record for the same delivery.

---

### ProcessedIdempotentKeys

Stores idempotency keys that have already been processed by the example receiver.

```text
ProcessedIdempotentKeys
├── key
└── processed_at
```

---

## Dashboard

The project includes a Django web dashboard at:

```text
/
```

The dashboard displays deliveries ordered by their creation time.

Individual delivery details are available at:

```text
/deliveries/<delivery_id>
```

These pages show the delivery and its associated attempts.

Endpoint details are available at:

```text
/endpoints/<endpoint_id>
```

The endpoint detail page shows the endpoint and its delivery history.

The dashboard makes it possible to inspect delivery results and individual attempts without relying solely on Celery console output.

---

## API

The current project contains an API endpoint for receiving the example animal event:

```text
POST /api/animal/
```

The endpoint expects JSON containing an animal name.

Example:

```json
{
    "name": "cat"
}
```

The currently accepted animals are:

```text
cat
dog
elephant
lion
tiger
monkey
giraffe
```

A valid animal returns:

```text
200 OK
```

An unrecognized animal returns:

```text
404 Not Found
```

An invalid webhook signature returns:

```text
401 Unauthorized
```

The endpoint also checks the `Idempotency-Key` header before processing the request.

---

## Project Structure

The main application structure includes:

```text
project/
│
├── webhook/
│   ├── migrations/
│   ├── models.py
│   ├── views.py
│   ├── tasks.py
│   ├── urls.py
│   ├── forms.py
│   └── ...
│
├── templates/
│   ├── Dashboard.html
│   ├── detail.html
│   ├── endpoint_detail.html
│   └── add_event.html
│
└── manage.py
```

---

## Running the Project

### 1. Install dependencies

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

---

### 2. Configure PostgreSQL

Create a PostgreSQL database and configure the database connection in Django's settings.

Then run:

```bash
python3 manage.py migrate
```

---

### 3. Create a Django superuser

```bash
python3 manage.py createsuperuser
```

---

### 4. Start Redis

Redis must be running because it is used as the Celery broker.

```bash
redis-server
```

---

### 5. Start Django

```bash
python3 manage.py runserver
```

---

### 6. Start the Celery worker

In another terminal:

```bash
celery -A <project_name> worker --loglevel=info
```

The Django development server, Redis, and Celery worker need to be running for the complete webhook delivery workflow.

---

## Example Delivery

### Successful Delivery

```text
Event Created
      ↓
Delivery Created
      ↓
Celery Task
      ↓
HTTP POST
      ↓
2xx Response
      ↓
DeliveryAttempt → SU
      ↓
Delivery → DELIVERED
      ↓
Endpoint consecutive failures → 0
```

### Failed Delivery with Retries

```text
Event Created
      ↓
Delivery Created
      ↓
Initial HTTP Request
      ↓
500 Server Error
      ↓
Retry after 5s
      ↓
500 Server Error
      ↓
Retry after 10s
      ↓
500 Server Error
      ↓
Retry after 20s
      ↓
Final attempt
      ↓
Delivery → DELIVERY FAILED
```

Each attempt is recorded separately.

---

## What I Learned

This project was built to move beyond basic CRUD APIs and explore backend systems that interact with unreliable external services.

The main concepts explored were:

* Celery background tasks
* Redis message brokering
* Asynchronous HTTP requests
* Retry mechanisms
* Exponential backoff
* HTTP failure classification
* Idempotency
* HMAC-SHA256 request signing
* PostgreSQL relationships
* Delivery tracking
* Attempt tracking
* Circuit breakers
* Handling timeouts and connection failures
* Monitoring webhook deliveries
* At-least-once delivery considerations

The main takeaway was understanding how a backend can handle failures and unreliable external endpoints instead of assuming every HTTP request will succeed.

---

## Future Improvements

Possible improvements for a future version include:

* Configurable retry policies
* Scheduled webhook delivery
* Endpoint management through an API
* More detailed delivery metrics
* Rate limiting
* More extensive automated testing
* Production deployment
* More configurable circuit-breaker policies
* Support for additional event types and receivers

---

## License

This project was built as a learning and portfolio project to explore reliable backend systems and asynchronous event delivery.
