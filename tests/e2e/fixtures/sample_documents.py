"""Sample document fixtures for domain classification E2E tests.

This module provides fixtures for testing AI-powered domain classification:
- Legal documents (contracts, case law)
- Medical documents (research papers, clinical notes)
- Technical documents (software documentation, API specs)
- Mixed domain documents for classification testing
"""

from pathlib import Path

import pytest


@pytest.fixture
def sample_legal_contract(tmp_path: Path) -> Path:
    """Create a sample legal contract document.

    This document should be classified as "legal" domain
    by the AI classification system.

    Returns:
        Path to legal contract text file
    """
    content = """SOFTWARE LICENSE AGREEMENT

This Software License Agreement ("Agreement") is entered into as of December 17, 2025,
by and between TechCorp Inc., a Delaware corporation ("Licensor"), and Enterprise Solutions LLC,
a California limited liability company ("Licensee").

RECITALS

WHEREAS, Licensor has developed certain proprietary software products; and
WHEREAS, Licensee desires to obtain a license to use such software products;

NOW, THEREFORE, in consideration of the mutual covenants and agreements herein contained,
the parties agree as follows:

1. DEFINITIONS

1.1 "Software" means the proprietary software application known as "DataPro Analytics Suite",
including all related documentation, updates, and modifications.

1.2 "License Fee" means the annual payment of $50,000 USD payable by Licensee to Licensor.

2. GRANT OF LICENSE

2.1 Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee
a non-exclusive, non-transferable, limited license to use the Software for internal business
purposes only.

2.2 The license granted herein does not permit Licensee to sublicense, distribute, or create
derivative works based on the Software.

3. RESTRICTIONS

3.1 Licensee shall not reverse engineer, decompile, or disassemble the Software.

3.2 Licensee shall not remove or modify any proprietary notices or labels on the Software.

4. INTELLECTUAL PROPERTY RIGHTS

4.1 Licensor retains all right, title, and interest in and to the Software, including all
intellectual property rights therein.

5. CONFIDENTIALITY

5.1 Each party agrees to maintain in confidence all Confidential Information disclosed by
the other party and to use such information solely for the purposes of this Agreement.

6. WARRANTY AND DISCLAIMER

6.1 Licensor warrants that the Software will perform substantially in accordance with the
documentation for a period of ninety (90) days from the date of delivery.

6.2 EXCEPT AS EXPRESSLY PROVIDED HEREIN, THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY
OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

7. LIMITATION OF LIABILITY

7.1 IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR
CONSEQUENTIAL DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGES.

7.2 LICENSOR'S TOTAL LIABILITY SHALL NOT EXCEED THE LICENSE FEES PAID BY LICENSEE.

8. INDEMNIFICATION

8.1 Licensor shall indemnify and hold harmless Licensee from any claims that the Software
infringes any third-party intellectual property rights.

9. TERM AND TERMINATION

9.1 This Agreement shall commence on the Effective Date and continue for a period of one (1)
year, unless earlier terminated as provided herein.

9.2 Either party may terminate this Agreement upon thirty (30) days written notice if the
other party materially breaches any provision of this Agreement.

10. GENERAL PROVISIONS

10.1 This Agreement shall be governed by the laws of the State of Delaware.

10.2 This Agreement constitutes the entire agreement between the parties and supersedes all
prior agreements and understandings.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first above written.

LICENSOR: TechCorp Inc.
By: John Smith, CEO

LICENSEE: Enterprise Solutions LLC
By: Jane Doe, President
"""

    doc_path = tmp_path / "software_license_agreement.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def sample_medical_research_paper(tmp_path: Path) -> Path:
    """Create a sample medical research paper.

    This document should be classified as "medical" domain
    by the AI classification system.

    Returns:
        Path to medical research paper text file
    """
    content = """Efficacy of Novel ACE Inhibitor in Hypertensive Patients: A Randomized Controlled Trial

Abstract

Background: Hypertension remains a leading risk factor for cardiovascular disease worldwide.
This study evaluates the efficacy and safety of a novel angiotensin-converting enzyme (ACE)
inhibitor, designated as ACE-X, in treating essential hypertension.

Methods: We conducted a randomized, double-blind, placebo-controlled trial involving 450
patients with essential hypertension (systolic BP 140-179 mmHg). Patients were randomized
1:1 to receive either ACE-X (10mg daily, n=225) or placebo (n=225) for 12 weeks. The primary
endpoint was change in systolic blood pressure from baseline to week 12.

Results: At 12 weeks, the ACE-X group showed a mean reduction in systolic blood pressure of
15.3 mmHg (95% CI: 13.2-17.4) compared to 2.1 mmHg (95% CI: 0.8-3.4) in the placebo group
(p<0.001). Diastolic blood pressure decreased by 9.8 mmHg in the ACE-X group versus 1.5 mmHg
in placebo (p<0.001).

Safety: Adverse events were mild and comparable between groups. The most common side effect
was dry cough, occurring in 8.9% of ACE-X patients versus 2.2% of placebo patients (p=0.003).
No serious adverse events were attributed to the study drug.

Conclusion: ACE-X demonstrates significant efficacy in reducing blood pressure in patients
with essential hypertension, with a safety profile consistent with other ACE inhibitors.

Introduction

Cardiovascular disease (CVD) remains the leading cause of mortality globally, accounting for
approximately 17.9 million deaths annually. Hypertension, defined as systolic blood pressure
≥140 mmHg or diastolic blood pressure ≥90 mmHg, affects over 1.3 billion people worldwide and
is a major modifiable risk factor for CVD.

Angiotensin-converting enzyme (ACE) inhibitors have been a cornerstone of antihypertensive
therapy for over three decades. These medications work by blocking the conversion of
angiotensin I to angiotensin II, a potent vasoconstrictor, thereby reducing peripheral
vascular resistance and blood pressure.

Despite the availability of multiple ACE inhibitors, there remains a need for medications
with improved efficacy, tolerability, and once-daily dosing convenience. ACE-X is a novel
ACE inhibitor with enhanced tissue penetration and prolonged duration of action.

Methods

Study Design: This was a 12-week, multicenter, randomized, double-blind, placebo-controlled,
parallel-group trial conducted at 25 sites across North America and Europe.

Participants: Eligible patients were adults aged 18-75 years with essential hypertension
(systolic BP 140-179 mmHg and/or diastolic BP 90-109 mmHg) after a 2-week washout period.

Exclusion criteria included secondary hypertension, recent cardiovascular events, significant
renal impairment (eGFR <30 mL/min/1.73m²), or pregnancy.

Randomization: Patients were randomized 1:1 using a computer-generated sequence with
permuted blocks of 4, stratified by site.

Intervention: ACE-X 10mg or matching placebo, administered orally once daily in the morning.

Assessments: Blood pressure was measured at baseline and weeks 2, 4, 8, and 12 using
standardized automated oscillometric devices. Safety assessments included adverse event
monitoring, laboratory tests, and physical examinations.

Statistical Analysis: The primary analysis used intention-to-treat principles with mixed
model repeated measures (MMRM) analysis. A sample size of 450 patients provided 90% power
to detect a 10 mmHg difference in systolic BP with a two-sided alpha of 0.05.

Results

Baseline Characteristics: The mean age was 58.2 years (SD 9.8), 52% were male, and mean
baseline blood pressure was 156.4/96.2 mmHg. Groups were well-balanced for all baseline
characteristics.

Primary Endpoint: At week 12, the ACE-X group achieved a significantly greater reduction in
systolic blood pressure compared to placebo (between-group difference: 13.2 mmHg, 95% CI:
10.8-15.6, p<0.001).

Blood pressure reduction was evident as early as week 2 and maintained throughout the study
period. Response rates (BP <140/90 mmHg) were 68.4% in the ACE-X group versus 22.7% in
placebo (p<0.001).

Safety: Treatment-emergent adverse events occurred in 32.4% of ACE-X patients versus 28.0%
of placebo patients. The most common adverse event was dry cough (8.9% vs 2.2%). Serious
adverse events were rare and not attributed to study medication.

Laboratory abnormalities were uncommon, with no clinically significant changes in renal
function, electrolytes, or hepatic enzymes.

Discussion

This randomized controlled trial demonstrates that ACE-X is effective and well-tolerated
for treating essential hypertension. The magnitude of blood pressure reduction observed
(15.3/9.8 mmHg) is clinically meaningful and consistent with or superior to other
first-line antihypertensive agents.

The safety profile was favorable, with adverse events comparable to placebo except for
dry cough, a known class effect of ACE inhibitors. The 8.9% incidence of cough is within
the expected range for ACE inhibitors (5-20%) and lower than some older agents.

Limitations include the 12-week duration and exclusion of patients with severe hypertension
or significant comorbidities. Long-term studies are needed to assess cardiovascular outcomes
and durability of response.

Conclusion

ACE-X provides effective blood pressure reduction with once-daily dosing and acceptable
tolerability in patients with essential hypertension. These findings support its use as a
first-line antihypertensive agent.

Funding: This study was funded by PharmaCorp Research Foundation.
"""

    doc_path = tmp_path / "ace_inhibitor_clinical_trial.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def sample_technical_documentation(tmp_path: Path) -> Path:
    """Create a sample technical software documentation.

    This document should be classified as "technical" domain
    by the AI classification system.

    Returns:
        Path to technical documentation text file
    """
    content = """REST API Documentation: User Authentication Service

Version: 2.1.0
Last Updated: December 2025

Table of Contents
1. Overview
2. Authentication
3. Endpoints
4. Error Handling
5. Rate Limiting
6. Code Examples

1. OVERVIEW

The User Authentication Service provides secure authentication and authorization capabilities
for client applications. The API follows REST principles and uses JSON for request and
response payloads.

Base URL: https://api.example.com/v2/auth
Protocol: HTTPS only
Content-Type: application/json

2. AUTHENTICATION

All API requests must include a valid API key in the Authorization header:

Authorization: Bearer YOUR_API_KEY

API keys can be obtained from the developer portal at https://developers.example.com

2.1 OAuth 2.0 Support

The service supports OAuth 2.0 authorization code flow for delegated access:

- Authorization endpoint: /oauth/authorize
- Token endpoint: /oauth/token
- Supported grant types: authorization_code, refresh_token, client_credentials

3. ENDPOINTS

3.1 POST /register

Register a new user account.

Request Body:
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd",
  "first_name": "John",
  "last_name": "Doe",
  "organization": "Acme Corp"
}

Response (201 Created):
{
  "user_id": "usr_1a2b3c4d5e",
  "email": "user@example.com",
  "created_at": "2025-12-17T10:30:00Z",
  "email_verified": false
}

Errors:
- 400 Bad Request: Invalid email format or weak password
- 409 Conflict: Email already registered

3.2 POST /login

Authenticate user and obtain access token.

Request Body:
{
  "email": "user@example.com",
  "password": "SecureP@ssw0rd",
  "device_id": "dev_mobile_12345"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "rt_1a2b3c4d5e6f7g8h",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "usr_1a2b3c4d5e",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}

Errors:
- 401 Unauthorized: Invalid credentials
- 423 Locked: Account temporarily locked due to failed login attempts

3.3 POST /refresh

Obtain new access token using refresh token.

Request Body:
{
  "refresh_token": "rt_1a2b3c4d5e6f7g8h"
}

Response (200 OK):
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}

3.4 POST /logout

Invalidate current access and refresh tokens.

Request Headers:
Authorization: Bearer ACCESS_TOKEN

Request Body:
{
  "refresh_token": "rt_1a2b3c4d5e6f7g8h"
}

Response (204 No Content)

3.5 GET /user/profile

Retrieve authenticated user's profile.

Request Headers:
Authorization: Bearer ACCESS_TOKEN

Response (200 OK):
{
  "user_id": "usr_1a2b3c4d5e",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "organization": "Acme Corp",
  "email_verified": true,
  "created_at": "2025-12-17T10:30:00Z",
  "last_login": "2025-12-17T14:22:00Z"
}

3.6 PUT /user/profile

Update user profile information.

Request Headers:
Authorization: Bearer ACCESS_TOKEN

Request Body:
{
  "first_name": "Jonathan",
  "organization": "Acme Corporation"
}

Response (200 OK):
{
  "user_id": "usr_1a2b3c4d5e",
  "email": "user@example.com",
  "first_name": "Jonathan",
  "last_name": "Doe",
  "organization": "Acme Corporation"
}

4. ERROR HANDLING

All errors follow RFC 7807 Problem Details format:

{
  "type": "https://api.example.com/errors/invalid-credentials",
  "title": "Invalid Credentials",
  "status": 401,
  "detail": "The provided email or password is incorrect",
  "instance": "/login",
  "trace_id": "abc123xyz789"
}

Common HTTP Status Codes:
- 200 OK: Request succeeded
- 201 Created: Resource created successfully
- 204 No Content: Request succeeded with no response body
- 400 Bad Request: Invalid request parameters
- 401 Unauthorized: Authentication required or failed
- 403 Forbidden: Authenticated but not authorized
- 404 Not Found: Resource does not exist
- 409 Conflict: Resource conflict (e.g., duplicate email)
- 422 Unprocessable Entity: Validation error
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error
- 503 Service Unavailable: Temporary unavailability

5. RATE LIMITING

API requests are rate limited to prevent abuse:

- Anonymous requests: 100 requests per hour
- Authenticated requests: 1000 requests per hour
- Burst limit: 20 requests per second

Rate limit headers are included in all responses:

X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1702821600

When rate limit is exceeded, a 429 status code is returned with Retry-After header.

6. CODE EXAMPLES

6.1 Python Example

import requests

# Register new user
response = requests.post(
    'https://api.example.com/v2/auth/register',
    json={
        'email': 'user@example.com',
        'password': 'SecureP@ssw0rd',
        'first_name': 'John',
        'last_name': 'Doe'
    }
)
print(response.json())

# Login
response = requests.post(
    'https://api.example.com/v2/auth/login',
    json={
        'email': 'user@example.com',
        'password': 'SecureP@ssw0rd'
    }
)
tokens = response.json()
access_token = tokens['access_token']

# Get user profile
response = requests.get(
    'https://api.example.com/v2/auth/user/profile',
    headers={'Authorization': f'Bearer {access_token}'}
)
print(response.json())

6.2 JavaScript Example

// Register new user
const registerResponse = await fetch(
  'https://api.example.com/v2/auth/register',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'user@example.com',
      password: 'SecureP@ssw0rd',
      first_name: 'John',
      last_name: 'Doe'
    })
  }
);
const user = await registerResponse.json();

// Login
const loginResponse = await fetch(
  'https://api.example.com/v2/auth/login',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'user@example.com',
      password: 'SecureP@ssw0rd'
    })
  }
);
const { access_token } = await loginResponse.json();

// Get user profile
const profileResponse = await fetch(
  'https://api.example.com/v2/auth/user/profile',
  {
    headers: { 'Authorization': `Bearer ${access_token}` }
  }
);
const profile = await profileResponse.json();

For additional support, visit https://developers.example.com or contact support@example.com
"""

    doc_path = tmp_path / "api_authentication_documentation.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def sample_documents_various_domains(
    sample_legal_contract: Path,
    sample_medical_research_paper: Path,
    sample_technical_documentation: Path,
) -> list[Path]:
    """Get all sample documents from various domains.

    Returns:
        List of Paths to sample documents (legal, medical, technical)
    """
    return [
        sample_legal_contract,
        sample_medical_research_paper,
        sample_technical_documentation,
    ]
