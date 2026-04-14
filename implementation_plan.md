Part 1: Improved Implementation Plan
Phase 1: Environment Setup

Initialize the project directory.

Run the following command to set up the frontend and backend environments:
npm create vite@latest frontend --template react && cd frontend && npm install axios && cd ../ && python3 -m venv venv && source venv/bin/activate && pip install fastapi uvicorn openai pydantic cachetools

Phase 2: Backend API and State Management

Define a Pydantic model for the 15 required Fabrica configuration fields (e.g., redfish_endpoints (list of strings), polling_interval_seconds (integer), http_success_codes (list of integers)).

Implement an in-memory session store using cachetools.TTLCache configured for a maximum of 1000 items and a TTL of 86400 seconds. Map a UUID string to the Pydantic model state.

Implement the /analyze POST endpoint to accept a text payload up to 50KB and initialize the session.

Implement the /answer POST endpoint to accept a JSON key-value pair, retrieve the session state, update the Pydantic model, and store it back in the cache.

Phase 3: LLM Orchestrator

Configure the OpenAI client using the Structured Outputs API to enforce the Pydantic schema.

In the /analyze and /answer routes, prompt the LLM with the raw text and the current schema state.

Instruct the LLM to return the populated schema, an array of exactly 1 missing field, and 1 specific question for that field. Set a timeout of 45 seconds and a maximum of 3 retries.

Phase 4: Frontend Development

Build a React component mapping a text area input to the /analyze endpoint (port 8000).

Build a dynamic form component that renders the 1 question returned by the backend and submits the answer to the /answer endpoint.

Render an export button when the backend returns 100% completion status.

Phase 5: Export Mechanism

Implement the /export GET endpoint.

Map the completed session state into an apis.yaml file.

Compress the file into a .zip archive and return it as a binary response.

Part 2: Test Verification Plan
Unit Tests

Test Pydantic schema validation to ensure integer and string constraints are enforced.

Send a 51KB payload to /analyze and verify it returns a 413 status code.

Test the TTLCache to verify entries are removed after 86400 seconds.

Integration Tests

Submit a mock response to /answer.

Verify the TTLCache state updates the specific field without overwriting the other 14 fields.

Assert the endpoint returns a 200 OK status and the next missing field in the sequence.

End-to-End Tests

Submit a mock RFD text via the frontend UI.

Intercept the LLM call to mock a sequence of 3 validation loops.

Automate the submission of the 3 corresponding answers.

Verify the UI transitions to the export state.

Trigger /export and assert the .zip file contains the apis.yaml populated with the 15 correct fields.