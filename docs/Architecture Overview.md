# ARCHITECTURE 

## Overview 

Scout.io follows a modular, organization-centric, multi-tenant architecture designed around the principles of security, stability, scalability, and maintainability. The architecture intentionally separates responsibilities across independent components to minimize coupling and maximize extensibility. 

The platform adopts a three-tier architectural model consisting of: 

- Presentation Layer 

- Application Layer 

- Data Layer 

All components are designed to remain pluggable and provider-independent. 

## Architectural Goals 

The architecture must satisfy the following requirements: 

- Multi-tenancy support. 

- Multiple chatbot support per organization. 

- Multiple LLM provider support. 

- Multiple knowledge source support. 

- Hybrid deployment capabilities. 

- Graceful degradation mechanisms. 

- Configurable response behaviours. 

- Organization-level isolation. 

- Vendor independence. 

- Horizontal scalability. 

- High availability. 

- Future extensibility without architectural redesign. 

## High-Level Architecture 

Scout.io 

| API Gateway Layer | Authentication Layer 

| Organization Layer | -------------------------------|                              | Dashboard Services              Chat Services |                              | -------------------------------| Application Layer | --------------------------------|               |                | Policy           Analytics         Session Engine            Engine           Manager |               |                | --------------------------------| Knowledge Engine | Synchronization Engine | Retrieval Engine | AI Router | Response Generation | Response Validation | Response Sanitization | Response Dispatcher | Presentation Layer | ----------------------------|                           | Dashboards                  Chat Widgets |                           | Organizations                  Customers 

## Architectural Layers 

### Presentation Layer 

The Presentation Layer is responsible for all user interactions. 

This includes: 

_Organization Interfaces_ 

- Organization Dashboard 

- Chatbot Management 

- Knowledge Source Management 

- Analytics Dashboard 

- Policy Management 

- Session Management 

- Configuration Management 

#### _Customer Interfaces_ 

- Website Chat Widgets 

- Embedded Components 

- Future SDK integrations 

- Future API integrations 

Responsibilities include: 

- Rendering interfaces. 

- Managing user interactions. 

- Performing client-side validations. 

- Handling authenticated sessions. 

### Application Layer 

The Application Layer represents the core intelligence of Scout.io. 

This layer is responsible for: 

- Authentication 

- Authorization 

- Organization management 

- AI orchestration 

- Policy enforcement 

- Analytics processing 

- Synchronization workflows 

- Session management 

- Response generation 

No component within this layer should directly depend upon any provider implementation. 

### Data Layer 

The Data Layer manages: 

- Organizational metadata 

- Session information 

- Analytics 

- Embeddings 

- Knowledge indices 

- Configurations 

- Synchronization metadata 

Scout.io intentionally avoids becoming the owner of organizational knowledge whenever possible. 

Organizations remain the owners of: 

- Documents 

- Databases 

- APIs 

- Knowledge repositories 

Scout.io consumes only authorized information required for chatbot operations. 

## Component Architecture 

### API Gateway 

The API Gateway acts as the entry point for all requests. 

Responsibilities include: 

- Request routing 

- Rate limiting 

- Request validation 

- API versioning 

- Traffic management 

- Request monitoring 

#### All requests must pass through the API Gateway. 

### Authentication Layer 

Responsible for: 

- Organization authentication 

- Dashboard authentication 

- Session validation 

- Access controls 

- Future OAuth integrations 

Future support includes: 

- Single Sign-On 

- Enterprise authentication 

- Multi-factor authentication 

## Organization Manager 

Responsible for: 

- Organization management 

- Chatbot provisioning 

- Configuration management 

- Policy assignment 

- Resource isolation 

Every resource within Scout.io belongs to an organization. 

Examples include: 

- Chatbots 

- Sessions 

- Analytics 

- Policies 

- Knowledge configurations 

- Synchronization settings 

## Knowledge Engine 

The Knowledge Engine serves as the central intelligence layer responsible for managing knowledge workflows. 

Responsibilities include: 

- Knowledge indexing 

- Context management 

- Embedding management 

- Knowledge retrieval 

- Synchronization management 

- Context optimization 

Supported knowledge sources include: 

Knowledge Sources 

| 

-----------------------------------|          |           |            | Documents  Websites   Databases    APIs |              |          |          | PDF            Blogs      SQL        REST DOCX           FAQs       NoSQL      GraphQL Markdown       Docs       Firebase   Future APIs | Future Sources 

The Knowledge Engine remains independent from LLM providers. 

## Synchronization Engine 

Responsible for maintaining knowledge consistency. Supported synchronization mechanisms include: 

Manual Synchronization 

Organizations initiate updates manually. 

Scheduled Synchronization 

Examples include: 

 Hourly 

- Daily 

- Weekly 

### Push Synchronization 

Examples include: 

- Webhooks 

- API triggers 

- Event-based updates 

### Pull Synchronization 

Examples include: 

- Website crawling 

- API polling 

- Database synchronization 

Only modified knowledge should be synchronized whenever possible to minimize operational costs. 

## Retrieval Engine 

The Retrieval Engine is responsible for: 

- Context retrieval 

- Context ranking 

- Context compression 

- Knowledge filtering 

- Response optimization 

Responsibilities include: 

- Retrieving relevant information. 

- Eliminating irrelevant contexts. 

- Optimizing token utilization. 

- Preparing context for response generation. 

The Retrieval Engine must remain configurable and extensible for future improvements. 

## Policy Engine 

The Policy Engine validates organizational configurations before responses are generated. 

Examples include: 

##### Policies 

| ----------------------------|             |              | Security      Memory        AI Rules |             |              | Allowed        Session       Strict Sources        Limits        Balanced |             |              | Restricted     Storage       Creative Domains        Duration      Custom ----------------------------- 

Responsibilities include: 

- Security validations. 

- Behaviour management. 

- Organizational constraints. 

- Response restrictions. 

- Context validations. 

No response should bypass policy validation. 

## AI Router 

The AI Router is responsible for intelligent model selection. 

Responsibilities include: 

- Provider selection. 

- Request routing. 

- Fallback mechanisms. 

- Cost optimization. 

- Availability handling. 

- Performance optimization. 

Organizations configure behaviours rather than individual models. Examples include: 

High Accuracy 

| AI Router | --------------|      |       | GPT   Claude  Gemini --------------| Response 

---------------------------- 

Cost Efficient 

| AI Router | ----------------------|          |           | Qwen      Gemma       Phi ----------------------| Response 

The AI Router abstracts all provider implementations from organizations and customers. 

## Response Pipeline Architecture 

Every response follows the same architectural workflow. 

Customer | Question | API Gateway | Policy Validation | 

Security Validation | Knowledge Retrieval | Context Optimization | AI Router | Response Generation | Response Validation | Response Sanitization | Analytics Logging | Session Management | Final Response | Customer 

No component may bypass this pipeline. 

## Response Validation Layer 

Responsible for: 

- Hallucination detection. 

- Policy compliance. 

- Knowledge validations. 

- Output consistency checks. 

- Security validations. 

Examples include: 

- Unsupported responses. 

- Restricted information. 

- Invalid contexts. 

- Policy violations. 

When validations fail: 

Generated Response | Invalid? | YES | Regenerate | Invalid? | YES | Graceful Failure Response | Final Response 

The system should prioritize reliability over response generation. 

## Response Sanitization Layer 

Responsible for: 

- Removing sensitive information. 

- Applying organizational constraints. 

- Formatting responses. 

- Preventing information leakage. 

Examples include: 

- Hidden metadata. 

- Restricted content. 

- Organizational policies. 

- Session constraints. 

Customers should never receive: 

- LLM details. 

- Provider information. 

- Internal source metadata. 

- Organizational configurations. 

## Session Manager 

Responsible for: 

- Session management. 

- Conversation tracking. 

- Storage policies. 

- Session retention. 

Organizations may configure: 

- Session durations. 

- Storage policies. 

- Analytics configurations. 

- Retention periods. 

Examples include: 

Session Storage 

------------- 

No Storage 

7 Days 

30 Days 

90 Days 

##### Custom Policies 

------------- 

## Analytics Engine 

The Analytics Engine remains organization-facing. 

Responsibilities include: 

- Session analytics. 

- Usage statistics. 

- Performance monitoring. 

- Synchronization statistics. 

- Token utilization. 

- Response confidence scores. 

Optional analytics include: 

- Retrieved contexts. 

- Source mappings. 

- Validation reports. 

- Synchronization histories. 

Analytics should remain configurable to minimize unnecessary storage overhead. 

## Multi-Tenant Architecture 

Scout.io follows strict organization-level isolation. 

Scout.io | -------------------------------|               |               | Org-1           Org-2            Org-3 |                |                | Chatbots          Chatbots         Chatbots |                |                | Sources            Sources           Sources |                |                | Policies          Policies         Policies |                |                | Sessions          Sessions         Sessions |                |                | Data               Data             Data 

No organization should have access to: 

- Configurations of other organizations. 

- Sessions of other organizations. 

- Knowledge sources of other organizations. 

- Analytics belonging to other organizations.

## Database-Level Row-Level Security (RLS)

Scout.io implements defense-in-depth organization isolation at the database layer using PostgreSQL Row-Level Security (RLS). This provides an additional security layer beyond application-level query filtering.

### RLS Implementation

**Enabled Tables**: All 13 organization-scoped tables have RLS enabled:
- `users`, `chatbots`, `policies`, `knowledge_sources`, `sessions`
- `messages` (via session join), `api_keys`, `audit_logs`
- `analytics_events`, `daily_analytics`, `llm_usage`, `webhooks`

**Standard Isolation Policy**: Each table has an `org_isolation_policy` restricting all operations (SELECT, INSERT, UPDATE, DELETE) to rows where:
```sql
organization_id = current_setting('app.current_org_id')::uuid
```

**Messages Table**: Special policy joining through `sessions` table since messages don't have direct `organization_id`.

**Platform Admin Bypass**: A separate `platform_admin_bypass` policy allows cross-org access when:
```sql
current_setting('app.is_platform_admin', true) = 'true'
```
This is narrowly scoped to admin endpoints only, not a global superuser bypass.

### Request Lifecycle Integration

1. **Authentication**: JWT access tokens include `org_id` claim (set at login/refresh)
2. **Dependency Injection**: FastAPI dependency `get_db_with_org` extracts `org_id` from authenticated user
3. **Session Variable**: At start of each request, `SET LOCAL app.current_org_id = :org_id` runs on the DB connection
4. **Automatic Enforcement**: All subsequent queries on that connection automatically filtered by RLS
5. **Admin Endpoints**: Use `get_db_admin` which sets `SET LOCAL app.is_platform_admin = 'true'` for cross-org queries

### Security Guarantees

- **Defense in Depth**: Even if application-level WHERE clauses are accidentally omitted, RLS blocks cross-org access
- **Default Deny**: Without `app.current_org_id` set, queries return zero rows (RLS default deny)
- **Write Protection**: `WITH CHECK` prevents INSERT/UPDATE/DELETE with wrong `organization_id`
- **Audit Trail**: All cross-org access requires explicit platform_admin role and admin DB session

## Failure Handling Strategy

Scout.io adopts graceful degradation mechanisms. 

Examples include: 

Primary Provider | Failure | Fallback Provider | Failure | Scout Models | Failure | Graceful Failure Response | Customer Response Similarly, 

Synchronization Failure | Retry | Failure | Maintain Previous Knowledge State | Notify Organization | Continue Operations 

No component failure should terminate unrelated services. 

## Deployment Architecture 

The architecture must support: 

- Cloud deployments. 

- Hybrid deployments. 

- Self-hosted deployments. 

- Enterprise deployments. 

The MVP implementation focuses primarily on website integrations while preserving architectural extensibility. 

Deployment strategies should never require redesigning: 

- Knowledge workflows. 

- AI workflows. 

- Organization management. 

- Response pipelines. 

- Security mechanisms. 

## Architectural Constraints 

The following constraints are mandatory throughout the project: 

- Security takes precedence over feature additions. 

- Organizations remain the owners of their data. 

- Components must remain independently replaceable. 

- Provider implementations must remain abstracted. 

- Multi-tenancy must remain enforced across all layers. 

- No single component should become a point of failure. 

- Responses must pass through all validation layers. 

- Graceful degradation must exist wherever feasible. 

- Architectural changes must preserve backward compatibility whenever possible. 

## Architectural Philosophy 

Scout.io intentionally separates infrastructure concerns from intelligence concerns. The platform leverages existing and battle-tested ecosystems for foundational capabilities while dedicating engineering efforts towards solving organization-centric AI infrastructure challenges. 

Its differentiating architectural components include: 

- Knowledge Engine 

- Policy Engine 

- AI Router 

- Synchronization Engine 

- Response Validation Layer 

- Multi-Tenant Organization Management 

- Analytics Engine 

- Hybrid Deployment Architecture 

- Configurable Behaviour Framework 

- Database-Level Row-Level Security (RLS)

- HashiCorp Vault Secret Management 

This architecture establishes the structural blueprint for Scout.io and defines the responsibilities, boundaries, and interactions of every major component. All subsequent documents must inherit and adhere to the architectural decisions specified herein. 

