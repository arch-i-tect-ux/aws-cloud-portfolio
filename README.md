# AWS Cloud Portfolio Project

> A fully serverless contact management system built on AWS — demonstrating real-world cloud architecture across 10+ AWS services.

---

## What This Project Demonstrates

This project was built to showcase hands-on AWS cloud skills gained through the **ALX Africa Cloud Computing Programme** and extended with prior experience in **Azure** (AZ-900, DP-900), **UI/UX design**, and **web development**.

It is not a tutorial copy. Every architectural decision — service selection, IAM scoping, error handling strategy, free-tier optimisation — was made intentionally and is documented below.

---

## Architecture Overview

```
User / Browser
     │
     ▼
Amazon API Gateway (HTTP API)
     │
     ├──── POST /contact ──────▶ Lambda: contact_form
     │                               │
     │                               ├──▶ DynamoDB  (store submission)
     │                               ├──▶ SES       (send confirmation email)
     │                               └──▶ CloudWatch (auto-logging)
     │
     └──── GET /submissions ───▶ Lambda: get_submissions
                                      │
                                      └──▶ DynamoDB  (read all records)

GitHub (main branch push)
     │
     ▼
GitHub Actions CI/CD
     │
     └──▶ AWS Lambda (auto-deploy both functions)

Static Assets
     └──▶ Amazon S3 bucket (free tier)
```

---

## AWS Services Used

| Service | Role in This Project | Free Tier |
|---|---|---|
| **Lambda** | Serverless compute — two functions | 1M requests/month free |
| **API Gateway** | HTTP API exposing Lambda as REST endpoints | 1M calls/month free |
| **DynamoDB** | NoSQL database storing contact submissions | 25GB + 25 WCU free |
| **SES** | Transactional email confirmation to submitters | 62K emails/month free |
| **IAM** | Least-privilege roles scoped per Lambda function | Always free |
| **CloudWatch** | Automatic Lambda execution logs + retention policy | 5GB logs free |
| **S3** | Static asset storage | 5GB free |
| **Secrets Manager** | Secure storage for any API keys or secrets | 30-day trial |
| **GitHub Actions** | CI/CD — auto-deploys Lambdas on every push | Free for public repos |

> **Total monthly cost: $0** — all services operate within AWS Free Tier limits for this project's scale.

---

## Project Structure

```
aws-cloud-portfolio/
├── lambda/
│   ├── contact_form/
│   │   └── lambda_function.py      # POST /contact handler
│   └── get_submissions/
│       └── lambda_function.py      # GET /submissions handler
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD — auto-deploy on push to main
├── docs/
│   └── case-study.pdf              # Full cloud case study document
├── setup_infrastructure.py         # One-script AWS resource provisioning
└── README.md
```

---

## How to Deploy This Yourself

### Prerequisites
- AWS account (free tier)
- Python 3.10+
- AWS CLI configured (`aws configure`)

### Step 1 — Clone and install
```bash
git clone https://github.com/arch-i-tect-ux/aws-cloud-portfolio.git
cd aws-cloud-portfolio
pip install boto3
```

### Step 2 — Run the infrastructure setup
```bash
python setup_infrastructure.py
```

This single script creates all AWS resources in order:
1. IAM role with least-privilege policies
2. DynamoDB table (`portfolio-contacts`)
3. Both Lambda functions (zipped and deployed)
4. API Gateway with routes and CORS
5. S3 bucket
6. CloudWatch log groups with 30-day retention

### Step 3 — Verify your email in SES
Go to **AWS Console → SES → Verified identities → Create identity**
Add your email address, click the verification link in your inbox.
Then update `FROM_EMAIL` in `lambda/contact_form/lambda_function.py`.

### Step 4 — Set up CI/CD (GitHub Actions)
Add these secrets to your GitHub repo (Settings → Secrets → Actions):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Now every push to `main` auto-deploys both Lambda functions.

### Step 5 — Test the API
```bash
# Submit a contact form
curl -X POST https://l6nc8u8lxh.execute-api.us-east-1.amazonaws.com/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"your@email.com","message":"Hello from the CLI!"}'

# Read all submissions
curl https://l6nc8u8lxh.execute-api.us-east-1.amazonaws.com/submissions
```

---

## Key Design Decisions

**Why serverless (Lambda + API Gateway) instead of EC2?**
For a contact form workload, EC2 would run 24/7 at cost. Lambda runs only when invoked — zero cost at zero traffic, scales automatically at high traffic. This matches the AWS Well-Architected Framework's cost optimisation pillar.

**Why DynamoDB instead of RDS?**
Contact submissions are schema-simple (name, email, message, timestamp). DynamoDB's PAY_PER_REQUEST billing means zero cost for low-volume use, while RDS would incur a minimum monthly charge.

**Why IAM roles instead of hardcoded credentials?**
IAM roles are attached to Lambda execution contexts. No credentials in code, no `.env` files, no secrets to rotate manually. This is the AWS security best practice — credential-free architecture.

**Why GitHub Actions for CI/CD?**
Free for public repositories. Direct AWS CLI integration. Every push to `main` auto-packages and deploys both Lambda functions — no manual uploads via the console.

---

## Background & Context

This project was built as a practical demonstration of skills developed across:

- **ALX Africa AWS Cloud Computing Programme** — Solutions architecture, serverless, storage, databases, security
- **Microsoft Azure** — AZ-900 (Fundamentals), DP-900 (Data Fundamentals) — foundational multi-cloud exposure
- **Dynamic Database** — Professional cloud environment, Azure in production
- **UI/UX Design** — Startup experience (French market), design systems, user-centred thinking
- **Information Systems degree** — Web development, web design, systems thinking

---

## Author

[arch-i-tect-ux](https://github.com/arch-i-tect-ux) — Cloud practitioner from South Africa with a background spanning UI/UX design, web development, and multi-cloud engineering.

📄 [Download Full Case Study PDF](docs/case-study.pdf)

---

*Serverless · Python · AWS Free Tier · CI/CD · Zero infrastructure cost*
